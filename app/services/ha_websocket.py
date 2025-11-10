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

























