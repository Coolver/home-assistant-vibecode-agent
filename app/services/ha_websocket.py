"""Home Assistant WebSocket Client for real-time communication"""
import asyncio
import aiohttp
import json
import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime

logger = logging.getLogger('ha_cursor_agent')


class HAWebSocketClient:
    """
    Persistent WebSocket connection to Home Assistant
    
    Features:
    - Auto-authentication
    - Message routing with request/response matching
    - Auto-reconnect with exponential backoff
    - Thread-safe operation
    - Graceful shutdown
    """
    
    def __init__(self, url: str, token: str):
        """
        Initialize WebSocket client
        
        Args:
            url: Home Assistant URL (http://supervisor/core or http://homeassistant.local:8123)
            token: SUPERVISOR_TOKEN or Long-Lived Access Token
        """
        # Convert HTTP to WebSocket URL
        ws_url = url.replace('http://', 'ws://').replace('https://', 'wss://')
        self.url = f"{ws_url}/api/websocket"
        self.token = token
        
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.message_id = 1
        self.pending_requests: Dict[int, asyncio.Future] = {}
        
        self._running = False
        self._connected = False
        self._task: Optional[asyncio.Task] = None
        self._reconnect_delay = 1  # Start with 1 second
        self._max_reconnect_delay = 60  # Max 60 seconds
        
        # Event callbacks
        self.event_callbacks: Dict[str, Callable] = {}
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self._connected and self.ws is not None and not self.ws.closed
    
    async def start(self):
        """Start WebSocket client in background"""
        if self._running:
            logger.warning("WebSocket client already running")
            return
        
        logger.info(f"Starting WebSocket client: {self.url}")
        self._running = True
        self._task = asyncio.create_task(self._connection_loop())
    
    async def stop(self):
        """Stop WebSocket client gracefully"""
        logger.info("Stopping WebSocket client...")
        self._running = False
        
        # Close WebSocket
        if self.ws and not self.ws.closed:
            await self.ws.close()
        
        # Close session
        if self.session and not self.session.closed:
            await self.session.close()
        
        # Cancel background task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("WebSocket client stopped")
    
    async def _connection_loop(self):
        """Maintain WebSocket connection with auto-reconnect"""
        while self._running:
            try:
                await self._connect_and_listen()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                self._connected = False
                
                if self._running:
                    # Exponential backoff
                    logger.info(f"Reconnecting in {self._reconnect_delay} seconds...")
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)
    
    async def _connect_and_listen(self):
        """Connect to Home Assistant WebSocket and listen for messages"""
        logger.info(f"Connecting to {self.url}...")
        
        # Create session if needed
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        
        async with self.session.ws_connect(self.url) as ws:
            self.ws = ws
            
            # Step 1: Receive auth_required
            msg = await ws.receive_json()
            if msg.get('type') != 'auth_required':
                raise Exception(f"Expected auth_required, got: {msg.get('type')}")
            
            logger.debug("Received auth_required, sending auth...")
            
            # Step 2: Send auth
            await ws.send_json({
                'type': 'auth',
                'access_token': self.token
            })
            
            # Step 3: Receive auth_ok or auth_invalid
            auth_response = await ws.receive_json()
            if auth_response.get('type') == 'auth_invalid':
                raise Exception(f"Authentication failed: {auth_response.get('message')}")
            
            if auth_response.get('type') != 'auth_ok':
                raise Exception(f"Unexpected auth response: {auth_response}")
            
            logger.info("✅ WebSocket connected and authenticated")
            self._connected = True
            self._reconnect_delay = 1  # Reset backoff on successful connect
            
            # Step 4: Listen for messages
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_message(data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse WebSocket message: {e}")
                
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning("WebSocket closed by server")
                    break
                
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    break
            
            self._connected = False
    
    async def _handle_message(self, data: dict):
        """Handle incoming WebSocket message"""
        msg_type = data.get('type')
        msg_id = data.get('id')
        
        # Route response to pending request
        if msg_id is not None and msg_id in self.pending_requests:
            future = self.pending_requests.pop(msg_id)
            if not future.done():
                if msg_type == 'result':
                    future.set_result(data.get('result'))
                else:
                    future.set_result(data)
        
        # Handle events
        elif msg_type == 'event':
            event_type = data.get('event', {}).get('event_type')
            if event_type in self.event_callbacks:
                await self.event_callbacks[event_type](data.get('event'))
        
        # Log other message types for debugging
        elif msg_type not in ('pong', 'result'):
            logger.debug(f"Received WebSocket message: {msg_type}")
    
    async def _send_message(self, message: dict, timeout: float = 30.0) -> Any:
        """
        Send message via WebSocket and wait for response
        
        Args:
            message: Message to send (without 'id' field)
            timeout: Timeout in seconds
            
        Returns:
            Response data
            
        Raises:
            Exception: If not connected or timeout
        """
        if not self.is_connected:
            raise Exception("WebSocket not connected")
        
        # Assign message ID
        msg_id = self.message_id
        self.message_id += 1
        message['id'] = msg_id
        
        # Create future for response
        future: asyncio.Future = asyncio.Future()
        self.pending_requests[msg_id] = future
        
        try:
            # Send message
            await self.ws.send_json(message)
            logger.debug(f"Sent WebSocket message: {message.get('type')} (id={msg_id})")
            
            # Wait for response with timeout
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
            
        except asyncio.TimeoutError:
            # Clean up on timeout
            self.pending_requests.pop(msg_id, None)
            raise Exception(f"WebSocket request timeout after {timeout}s")
        
        except Exception as e:
            # Clean up on error
            self.pending_requests.pop(msg_id, None)
            raise
    
    async def call_service(self, domain: str, service: str, service_data: dict = None, target: dict = None) -> Any:
        """
        Call Home Assistant service via WebSocket
        
        Args:
            domain: Service domain (e.g., 'light', 'hacs')
            service: Service name (e.g., 'turn_on', 'download')
            service_data: Service data
            target: Target entities
            
        Returns:
            Service response
        """
        message = {
            'type': 'call_service',
            'domain': domain,
            'service': service,
        }
        
        if service_data:
            message['service_data'] = service_data
        
        if target:
            message['target'] = target
        
        result = await self._send_message(message)
        logger.info(f"Called service: {domain}.{service}")
        return result
    
    async def get_states(self) -> list:
        """
        Get all entity states
        
        Returns:
            List of entity states
        """
        result = await self._send_message({'type': 'get_states'})
        return result or []
    
    async def get_config(self) -> dict:
        """
        Get Home Assistant configuration
        
        Returns:
            Configuration dict
        """
        result = await self._send_message({'type': 'get_config'})
        return result or {}
    
    async def get_services(self) -> dict:
        """
        Get all available services
        
        Returns:
            Services dict
        """
        result = await self._send_message({'type': 'get_services'})
        return result or {}
    
    async def create_config_entry_helper(self, domain: str, data: dict) -> Any:
        """
        Create helper via config entry flow (UI method)
        
        Args:
            domain: Helper domain (input_boolean, input_text, etc.)
            data: Helper configuration
            
        Returns:
            Config entry result
        """
        # Try config flow init
        result = await self._send_message({
            'type': f'config/{domain}/create',
            'data': data
        })
        logger.info(f"Created config entry for: {domain}")
        return result
    
    async def subscribe_events(self, event_type: str, callback: Callable) -> int:
        """
        Subscribe to Home Assistant events
        
        Args:
            event_type: Event type to subscribe to
            callback: Async function to call when event occurs
            
        Returns:
            Subscription ID
        """
        self.event_callbacks[event_type] = callback
        
        result = await self._send_message({
            'type': 'subscribe_events',
            'event_type': event_type
        })
        
        logger.info(f"Subscribed to events: {event_type}")
        return result
    
    async def unsubscribe_events(self, subscription_id: int):
        """Unsubscribe from events"""
        await self._send_message({
            'type': 'unsubscribe_events',
            'subscription': subscription_id
        })
    
    async def ping(self) -> bool:
        """
        Send ping to keep connection alive
        
        Returns:
            True if pong received
        """
        try:
            await self._send_message({'type': 'ping'}, timeout=5.0)
            return True
        except:
            return False
    
    async def wait_for_connection(self, timeout: float = 30.0):
        """
        Wait until WebSocket is connected

        Args:
            timeout: Maximum time to wait

        Raises:
            TimeoutError: If connection not established
        """
        start = datetime.now()
        while not self.is_connected:
            if (datetime.now() - start).total_seconds() > timeout:
                raise TimeoutError("WebSocket connection timeout")
            await asyncio.sleep(0.1)
    
    # ==================== Entity Registry ====================
    
    async def get_entity_registry_list(self) -> list:
        """
        Get all entities from Entity Registry
        
        Returns:
            List of entity registry entries with metadata (area_id, device_id, name, etc.)
        """
        result = await self._send_message({'type': 'config/entity_registry/list'})
        return result or []
    
    async def get_entity_registry_entry(self, entity_id: str) -> dict:
        """
        Get single entity from Entity Registry
        
        Args:
            entity_id: Entity ID to get
            
        Returns:
            Entity registry entry with metadata
        """
        result = await self._send_message({
            'type': 'config/entity_registry/get',
            'entity_id': entity_id
        })
        # Handle wrapped response format
        if isinstance(result, dict) and 'result' in result:
            return result['result']
        return result or {}
    
    async def update_entity_registry(self, entity_id: str, **kwargs) -> dict:
        """
        Update entity in Entity Registry
        
        Args:
            entity_id: Entity ID to update
            **kwargs: Fields to update (name, area_id, disabled, new_entity_id, etc.)
            
        Returns:
            Update result
        """
        message = {
            'type': 'config/entity_registry/update',
            'entity_id': entity_id,
            **kwargs
        }
        result = await self._send_message(message)
        logger.info(f"Updated entity registry: {entity_id}")
        return result
    
    async def remove_entity_registry_entry(self, entity_id: str) -> dict:
        """
        Remove entity from Entity Registry
        
        Args:
            entity_id: Entity ID to remove
            
        Returns:
            Removal result
        """
        result = await self._send_message({
            'type': 'config/entity_registry/remove',
            'entity_id': entity_id
        })
        logger.debug(f"remove_entity_registry_entry result for {entity_id}: {result}")
        
        # Check for error in result
        if isinstance(result, dict) and result.get('success') is False:
            error = result.get('error', {})
            error_message = error.get('message', str(error)) if isinstance(error, dict) else str(error)
            logger.warning(f"Entity removal failed: {entity_id}, error: {error_message}")
        
        logger.info(f"Removed entity from registry: {entity_id}")
        return result
    
    # ==================== Area Registry ====================
    
    async def get_area_registry_list(self) -> list:
        """
        Get all areas from Area Registry
        
        Returns:
            List of area registry entries
        """
        result = await self._send_message({'type': 'config/area_registry/list'})
        return result or []
    
    async def get_area_registry_entry(self, area_id: str) -> dict:
        """
        Get single area from Area Registry
        
        Args:
            area_id: Area ID to get
            
        Returns:
            Area registry entry
        """
        try:
            result = await self._send_message({
                'type': 'config/area_registry/get',
                'area_id': area_id
            })
            logger.debug(f"get_area_registry_entry result for {area_id}: {result}")
            
            # Handle wrapped response format
            if isinstance(result, dict):
                # Check for error in result
                if result.get('success') is False:
                    error = result.get('error', {})
                    logger.warning(f"Area registry get failed: {error}")
                    return {}
                
                # Handle different response formats
                if 'result' in result:
                    return result['result'] or {}
                # If result is the area entry itself
                if 'area_id' in result:
                    return result
                    
            area_result = result or {}
            
            # If result is empty or doesn't have area_id, use fallback
            if not area_result or not area_result.get('area_id'):
                logger.info(f"WebSocket result empty for area {area_id}, falling back to list method")
                areas = await self.get_area_registry_list()
                for area in areas:
                    if area.get('area_id') == area_id:
                        logger.debug(f"Found area {area_id} via fallback method")
                        return area
                logger.warning(f"Area {area_id} not found in registry list either")
                return {}
            
            return area_result
        except Exception as e:
            logger.error(f"Error getting area registry entry {area_id}: {e}")
            # Fallback: get from list
            logger.info(f"Falling back to list method for area {area_id} due to exception")
            try:
                areas = await self.get_area_registry_list()
                for area in areas:
                    if area.get('area_id') == area_id:
                        logger.debug(f"Found area {area_id} via fallback method after exception")
                        return area
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
            return {}
    
    async def create_area_registry_entry(self, name: str, aliases: list = None) -> dict:
        """
        Create new area in Area Registry
        
        Args:
            name: Area name
            aliases: Optional list of aliases
            
        Returns:
            Created area entry with area_id
        """
        message = {
            'type': 'config/area_registry/create',
            'name': name
        }
        if aliases:
            message['aliases'] = aliases
        
        result = await self._send_message(message)
        logger.info(f"Created area: {name}")
        return result
    
    async def update_area_registry_entry(self, area_id: str, name: str = None, aliases: list = None) -> dict:
        """
        Update area in Area Registry
        
        Args:
            area_id: Area ID to update
            name: Optional new name
            aliases: Optional new aliases list
            
        Returns:
            Update result
        """
        message = {
            'type': 'config/area_registry/update',
            'area_id': area_id
        }
        if name is not None:
            message['name'] = name
        if aliases is not None:
            message['aliases'] = aliases
        
        result = await self._send_message(message)
        logger.info(f"Updated area registry: {area_id}")
        return result
    
    async def delete_area_registry_entry(self, area_id: str) -> dict:
        """
        Delete area from Area Registry
        
        Args:
            area_id: Area ID to delete
            
        Returns:
            Deletion result
        """
        result = await self._send_message({
            'type': 'config/area_registry/delete',
            'area_id': area_id
        })
        logger.info(f"Deleted area from registry: {area_id}")
        return result
    
    # ==================== Device Registry ====================
    
    async def get_device_registry_list(self) -> list:
        """
        Get all devices from Device Registry
        
        Returns:
            List of device registry entries
        """
        result = await self._send_message({'type': 'config/device_registry/list'})
        return result or []
    
    async def get_device_registry_entry(self, device_id: str) -> dict:
        """
        Get single device from Device Registry
        
        Args:
            device_id: Device ID to get
            
        Returns:
            Device registry entry
        """
        try:
            result = await self._send_message({
                'type': 'config/device_registry/get',
                'device_id': device_id
            })
            logger.debug(f"get_device_registry_entry result for {device_id}: {result}")
            
            # Handle wrapped response format
            if isinstance(result, dict):
                # Check for error in result
                if result.get('success') is False:
                    error = result.get('error', {})
                    logger.warning(f"Device registry get failed: {error}")
                    return {}
                
                # Handle different response formats
                if 'result' in result:
                    return result['result'] or {}
                # If result is the device entry itself
                if 'id' in result or 'device_id' in result:
                    return result
                    
            device_result = result or {}
            
            # If result is empty or doesn't have device id, use fallback
            if not device_result or not (device_result.get('id') or device_result.get('device_id')):
                logger.info(f"WebSocket result empty for device {device_id}, falling back to list method")
                devices = await self.get_device_registry_list()
                for device in devices:
                    if device.get('id') == device_id:
                        logger.debug(f"Found device {device_id} via fallback method")
                        return device
                logger.warning(f"Device {device_id} not found in registry list either")
                return {}
            
            return device_result
        except Exception as e:
            logger.error(f"Error getting device registry entry {device_id}: {e}")
            # Fallback: get from list
            logger.info(f"Falling back to list method for device {device_id} due to exception")
            try:
                devices = await self.get_device_registry_list()
                for device in devices:
                    if device.get('id') == device_id:
                        logger.debug(f"Found device {device_id} via fallback method after exception")
                        return device
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
            return {}
    
    async def update_device_registry_entry(self, device_id: str, **kwargs) -> dict:
        """
        Update device in Device Registry
        
        Args:
            device_id: Device ID to update
            **kwargs: Fields to update (area_id, name_by_user, etc.)
            
        Returns:
            Update result
        """
        message = {
            'type': 'config/device_registry/update',
            'device_id': device_id,
            **kwargs
        }
        result = await self._send_message(message)
        logger.info(f"Updated device registry: {device_id}")
        return result
    
    async def remove_device_registry_entry(self, device_id: str) -> dict:
        """
        Remove device from Device Registry
        
        Args:
            device_id: Device ID to remove
            
        Returns:
            Removal result
        """
        result = await self._send_message({
            'type': 'config/device_registry/remove',
            'device_id': device_id
        })
        logger.info(f"Removed device from registry: {device_id}")
        return result


# Global WebSocket client instance
ha_ws_client: Optional[HAWebSocketClient] = None


async def get_ws_client() -> HAWebSocketClient:
    """
    Get WebSocket client instance
    
    Returns:
        HAWebSocketClient instance
        
    Raises:
        Exception: If client not initialized or not connected
    """
    if ha_ws_client is None:
        raise Exception("WebSocket client not initialized")
    
    if not ha_ws_client.is_connected:
        # Try to wait for connection
        try:
            await ha_ws_client.wait_for_connection(timeout=5.0)
        except TimeoutError:
            raise Exception("WebSocket not connected. Agent may still be starting up.")
    
    return ha_ws_client







































