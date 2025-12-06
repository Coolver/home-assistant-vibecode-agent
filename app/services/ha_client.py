"""Home Assistant API Client"""
import os
import aiohttp
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger('ha_cursor_agent')

class HomeAssistantClient:
    """Client for Home Assistant API"""
    
    def __init__(self, token: str = None):
        self.url = os.getenv('HA_URL', 'http://supervisor/core')
        # Use provided token or fall back to environment token
        self.token = token or os.getenv('HA_TOKEN', '') or os.getenv('SUPERVISOR_TOKEN', '')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
        }
        
        # Debug logging
        token_source = "provided" if token else ("HA_TOKEN" if os.getenv('HA_TOKEN') else ("SUPERVISOR_TOKEN" if os.getenv('SUPERVISOR_TOKEN') else "none"))
        token_preview = f"{self.token[:20]}..." if self.token else "EMPTY"
        logger.info(f"HAClient initialized - URL: {self.url}, Token source: {token_source}, Token: {token_preview}")
    
    def set_token(self, token: str):
        """Update token for requests"""
        self.token = token
        self.headers['Authorization'] = f'Bearer {token}'
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """Make HTTP request to HA API"""
        url = f"{self.url}/api/{endpoint}"
        
        # For POST requests, aiohttp may not handle query params correctly
        # Manually append them to URL if needed
        if method == 'POST' and params:
            from urllib.parse import urlencode
            query_string = urlencode(params)
            if query_string:
                url = f"{url}?{query_string}"
                params = None  # Clear params to avoid double encoding
        
        # Debug logging
        token_preview = f"{self.token[:20]}..." if self.token else "EMPTY"
        logger.debug(f"HA API Request: {method} {url}, Token: {token_preview}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=self.headers,
                    json=data,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status >= 400:
                        text = await response.text()
                        logger.error(f"HA API error: {response.status} - {text} | Token used: {token_preview}")
                        raise Exception(f"HA API error: {response.status} - {text}")
                    
                    logger.debug(f"HA API success: {method} {url} -> {response.status}")
                    return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Connection error to HA: {e}")
            raise Exception(f"Failed to connect to Home Assistant: {e}")
    
    async def get_states(self) -> List[Dict]:
        """Get all entity states"""
        return await self._request('GET', 'states')
    
    async def get_state(self, entity_id: str) -> Dict:
        """Get specific entity state"""
        return await self._request('GET', f'states/{entity_id}')
    
    async def get_services(self) -> List[Dict]:
        """Get all available services"""
        return await self._request('GET', 'services')
    
    async def call_service(self, domain: str, service: str, data: Dict) -> Dict:
        """Call a Home Assistant service"""
        endpoint = f"services/{domain}/{service}"
        
        # Some services require return_response as query parameter (e.g., file.read_file)
        # Remove return_response from data if present (it should be a query param, not in body)
        params = None
        if domain == 'file' and service == 'read_file':
            # Remove return_response from data dict if it's there (should be query param)
            if 'return_response' in data:
                data = {k: v for k, v in data.items() if k != 'return_response'}
            # Home Assistant API requires return_response as query parameter for file.read_file
            # Use string 'true' not boolean True to avoid it being sent in body
            params = {'return_response': 'true'}
        
        return await self._request('POST', endpoint, data, params=params)
    
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

# Global client instance
ha_client = HomeAssistantClient()

