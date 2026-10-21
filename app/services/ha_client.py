"""Home Assistant API Client"""
import os
import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional

from app.services.automation_mixin import AutomationMixin
from app.services.script_mixin import ScriptMixin

logger = logging.getLogger('ha_cursor_agent')


def _scrub_submitted_values(text: str, data: Any) -> str:
    """Drop submitted strings from an error body so a failed flow cannot echo a password into the log."""
    if not isinstance(data, dict):
        return text
    scrubbed = text
    for value in data.values():
        if isinstance(value, str) and len(value) >= 4:
            scrubbed = scrubbed.replace(value, "***")
        elif isinstance(value, dict):
            scrubbed = _scrub_submitted_values(scrubbed, value)
    return scrubbed


class HomeAssistantClient(AutomationMixin, ScriptMixin):
    """Client for Home Assistant API"""
    
    def __init__(self, token: str = None):
        self.url = os.getenv('HA_URL', 'http://supervisor/core')
        # Use provided token or fall back to environment token
        self.token = token or os.getenv('HA_TOKEN', '') or os.getenv('SUPERVISOR_TOKEN', '')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
        }
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Debug logging
        token_source = "provided" if token else ("HA_TOKEN" if os.getenv('HA_TOKEN') else ("SUPERVISOR_TOKEN" if os.getenv('SUPERVISOR_TOKEN') else "none"))
        token_preview = f"{self.token[:8]}..." if self.token else "EMPTY"
        logger.info(f"HAClient initialized - URL: {self.url}, Token source: {token_source}, Token: {token_preview}")
    
    def set_token(self, token: str):
        """Update token for requests"""
        self.token = token
        self.headers['Authorization'] = f'Bearer {token}'

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create a shared aiohttp session for connection pooling."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=240),
            )
        return self._session

    async def close(self):
        """Close the shared HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    _RETRYABLE_STATUSES = {502, 503, 504}
    _MAX_RETRIES = 3
    _RETRY_BACKOFF = [1.0, 3.0, 5.0]

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        suppress_404_logging: bool = False,
        redact: bool = False
    ) -> Dict:
        """Make HTTP request to HA API with retry on transient failures.
        
        Args:
            suppress_404_logging: If True, 404 errors will be logged as DEBUG instead of ERROR
            redact: If True, log only the keys of `data` (config flow input can hold passwords)
        """
        url = f"{self.url}/api/{endpoint}"
        timeout_seconds = timeout if timeout is not None else 240
        log_data = sorted(data) if redact and isinstance(data, dict) else data
        
        logger.info(f"HA API Request: {method} {url}, Data: {log_data}, Params: {params}, Timeout: {timeout_seconds}s")
        
        last_error: Optional[Exception] = None
        for attempt in range(self._MAX_RETRIES):
            try:
                session = await self._get_session()
                async with session.request(
                    method, 
                    url, 
                    headers=self.headers, 
                    json=data,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=timeout_seconds)
                ) as response:
                    if response.status in self._RETRYABLE_STATUSES and attempt < self._MAX_RETRIES - 1:
                        text = await response.text()
                        logger.warning(f"HA API transient error {response.status}, retrying ({attempt + 1}/{self._MAX_RETRIES})...")
                        await asyncio.sleep(self._RETRY_BACKOFF[attempt])
                        continue

                    if response.status >= 400:
                        text = await response.text()
                        if redact:
                            text = _scrub_submitted_values(text, data)
                        if response.status == 404 and suppress_404_logging:
                            logger.debug(f"HA API 404 (expected): {text} | URL: {url}")
                        else:
                            logger.error(f"HA API error: {response.status} - {text} | URL: {url} | Data: {log_data} | Params: {params}")
                        raise Exception(f"HA API error: {response.status} - {text}")
                    
                    logger.debug(f"HA API success: {method} {url} -> {response.status}")
                    return await response.json()
            except (aiohttp.ClientError, aiohttp.ServerDisconnectedError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < self._MAX_RETRIES - 1:
                    logger.warning(f"HA connection error ({type(e).__name__}), retrying ({attempt + 1}/{self._MAX_RETRIES})...")
                    await asyncio.sleep(self._RETRY_BACKOFF[attempt])
                else:
                    logger.error(f"Connection error to HA after {self._MAX_RETRIES} attempts: {e}")
                    raise Exception(f"Failed to connect to Home Assistant: {e}")
        
        raise Exception(f"Failed to connect to Home Assistant: {last_error}")

    async def get_states(self) -> List[Dict]:
        """Get all entity states"""
        return await self._request('GET', 'states')
    
    async def get_state(self, entity_id: str, suppress_404_logging: bool = False) -> Dict:
        """Get specific entity state
        
        Args:
            entity_id: Entity ID to get state for
            suppress_404_logging: If True, 404 errors will be logged as DEBUG instead of ERROR
        """
        return await self._request('GET', f'states/{entity_id}', suppress_404_logging=suppress_404_logging)
    
    async def get_services(self) -> List[Dict]:
        """Get all available services"""
        return await self._request('GET', 'services')
    
    async def call_service(self, domain: str, service: str, data: Dict) -> Dict:
        """Call a Home Assistant service"""
        endpoint = f"services/{domain}/{service}"
        
        # Some services need special handling
        params = None
        timeout = None
        
        if domain == 'hassio' and service in ['backup_full', 'backup_partial', 'restore_full', 'restore_partial']:
            # Long-running operations need more time
            timeout = 300  # 5 minutes for backup/restore operations
        
        return await self._request('POST', endpoint, data, params=params, timeout=timeout)
    
    async def get_config(self) -> Dict:
        """Get HA configuration"""
        return await self._request('GET', 'config')
    
    async def check_config(self) -> Dict:
        """Check configuration validity"""
        return await self.call_service('homeassistant', 'check_config', {})
    
    async def reload_component(self, component: str) -> Dict:
        """Reload a specific component"""
        component_map = {
            'automations': ('automation', 'reload'),
            'scripts': ('script', 'reload'),
            'templates': ('template', 'reload'),
            'core': ('homeassistant', 'reload_core_config'),
            'all': ('homeassistant', 'reload_all')
        }
        
        if component not in component_map:
            raise ValueError(f"Unknown component: {component}")
        
        domain, service = component_map[component]
        return await self.call_service(domain, service, {})
    
    async def restart(self) -> Dict:
        """Restart Home Assistant"""
        return await self.call_service('homeassistant', 'restart', {})

    async def get_logbook_entries(
        self,
        start_time: str,
        end_time: Optional[str] = None,
        entity_id: Optional[str] = None
    ) -> List[Dict]:
        """Fetch logbook entries from Home Assistant"""
        if not start_time:
            raise ValueError("start_time is required for logbook queries")
        
        params: Dict[str, Any] = {}
        if end_time:
            params['end_time'] = end_time
        if entity_id:
            params['entity'] = entity_id
        
        return await self._request('GET', f'logbook/{start_time}', params=params)
    
    async def rename_entity(self, old_entity_id: str, new_entity_id: str, new_name: Optional[str] = None) -> Dict:
        """
        Rename an entity_id via Entity Registry WebSocket API
        
        Args:
            old_entity_id: Current entity_id (e.g., 'climate.sonoff_trvzb_thermostat')
            new_entity_id: New entity_id (e.g., 'climate.office_trv_thermostat')
            new_name: Optional new friendly name
            
        Returns:
            Entity registry update result
            
        Raises:
            Exception: If rename fails or WebSocket not available
        """
        # Import here to avoid circular dependency
        from app.services.ha_websocket import get_ws_client
        
        logger.info(f"Renaming entity: {old_entity_id} → {new_entity_id}")
        
        try:
            ws_client = await get_ws_client()
            
            message = {
                'type': 'config/entity_registry/update',
                'entity_id': old_entity_id,
                'new_entity_id': new_entity_id
            }
            
            if new_name:
                message['name'] = new_name
            
            result = await ws_client._send_message(message)
            logger.info(f"✅ Successfully renamed entity: {old_entity_id} → {new_entity_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to rename entity via WebSocket: {e}")
            raise Exception(f"Failed to rename entity {old_entity_id} to {new_entity_id}: {e}")

    # ==================== Config entries and flows ====================

    async def list_config_entries(self) -> List[Dict]:
        """List all config entries (integrations and UI helpers)"""
        return await self._request('GET', 'config/config_entries/entry')

    async def reload_config_entry(self, entry_id: str) -> Dict:
        """Reload one config entry"""
        return await self._request('POST', f'config/config_entries/entry/{entry_id}/reload')

    async def delete_config_entry(self, entry_id: str) -> Dict:
        """Delete a config entry, removing the integration or helper and its entities"""
        return await self._request('DELETE', f'config/config_entries/entry/{entry_id}')

    async def start_config_flow(self, handler: str, show_advanced_options: bool = False) -> Dict:
        """Start a config flow, as 'Add integration' / 'Create helper' does in the UI"""
        return await self._request('POST', 'config/config_entries/flow',
                                   data={'handler': handler, 'show_advanced_options': show_advanced_options})

    async def config_flow_step(self, flow_id: str, user_input: Dict) -> Dict:
        """Submit the current step of a config flow"""
        return await self._request('POST', f'config/config_entries/flow/{flow_id}',
                                   data=user_input, redact=True)

    async def abort_config_flow(self, flow_id: str) -> Dict:
        """Abort a config flow in progress"""
        return await self._request('DELETE', f'config/config_entries/flow/{flow_id}')

    async def start_options_flow(self, entry_id: str) -> Dict:
        """Start the options flow ('Configure') of a config entry"""
        return await self._request('POST', 'config/config_entries/options/flow',
                                   data={'handler': entry_id})

    async def options_flow_step(self, flow_id: str, user_input: Dict) -> Dict:
        """Submit the current step of an options flow"""
        return await self._request('POST', f'config/config_entries/options/flow/{flow_id}',
                                   data=user_input, redact=True)

    async def abort_options_flow(self, flow_id: str) -> Dict:
        """Abort an options flow in progress"""
        return await self._request('DELETE', f'config/config_entries/options/flow/{flow_id}')


# Global client instance
ha_client = HomeAssistantClient()
