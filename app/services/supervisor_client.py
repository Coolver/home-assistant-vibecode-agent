"""Home Assistant Supervisor API Client for Add-on Management"""
import os
import aiohttp
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger('ha_cursor_agent')

class SupervisorClient:
    """Client for Home Assistant Supervisor API (Add-ons)"""
    
    def __init__(self):
        self.base_url = os.getenv('SUPERVISOR_URL', 'http://supervisor')
        self.token = os.getenv('SUPERVISOR_TOKEN', '')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
        }
        
        if not self.token:
            logger.warning("⚠️ No SUPERVISOR_TOKEN found - Add-on management disabled")
        else:
            token_preview = f"{self.token[:20]}..." if self.token else "EMPTY"
            logger.info(f"SupervisorClient initialized - URL: {self.base_url}, Token: {token_preview}")
    
    def is_available(self) -> bool:
        """Check if Supervisor API is available (running as add-on)"""
        return bool(self.token)
    
    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, timeout: int = 300) -> Dict:
        """Make HTTP request to Supervisor API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., 'addons', 'addons/core_mosquitto/install')
            data: Optional request body
            timeout: Request timeout in seconds (default 300 for install operations)
        """
        url = f"{self.base_url}/{endpoint}"
        
        token_preview = f"{self.token[:20]}..." if self.token else "EMPTY"
        logger.debug(f"Supervisor API Request: {method} {url}, Token: {token_preview}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, 
                    url, 
                    headers=self.headers, 
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status >= 400:
                        text = await response.text()
                        logger.error(f"Supervisor API error: {response.status} - {text}")
                        raise Exception(f"Supervisor API error: {response.status} - {text}")
                    
                    logger.debug(f"Supervisor API success: {method} {url} -> {response.status}")
                    
                    # Some endpoints return no content
                    if response.status == 204:
                        return {"success": True, "message": "Operation completed"}
                    
                    return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Connection error to Supervisor: {e}")
            raise Exception(f"Failed to connect to Supervisor: {e}")
    
    # ==================== Add-on Information ====================
    
    async def list_addons(self) -> Dict:
        """Get list of all available add-ons (installed and available)
        
        Returns:
            {
                "result": "ok",
                "data": {
                    "addons": [
                        {
                            "name": "Mosquitto broker",
                            "slug": "core_mosquitto",
                            "description": "An MQTT broker",
                            "version": "6.4.0",
                            "installed": "6.4.0",
                            "available": true,
                            "repository": "core",
                            "icon": false,
                            "logo": true
                        },
                        ...
                    ]
                }
            }
        """
        return await self._request('GET', 'supervisor/addons')
    
    async def get_addon_info(self, slug: str) -> Dict:
        """Get detailed information about a specific add-on
        
        Args:
            slug: Add-on slug (e.g., 'core_mosquitto', 'a0d7b954_zigbee2mqtt')
        
        Returns:
            Detailed add-on information including config, state, logs, etc.
        """
        return await self._request('GET', f'supervisor/addons/{slug}/info')
    
    async def get_addon_logs(self, slug: str) -> str:
        """Get add-on logs
        
        Args:
            slug: Add-on slug
        
        Returns:
            Plain text logs
        """
        url = f"{self.base_url}/supervisor/addons/{slug}/logs"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise Exception(f"Failed to get logs: {response.status} - {text}")
                    
                    return await response.text()
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to get add-on logs: {e}")
    
    # ==================== Add-on Lifecycle ====================
    
    async def install_addon(self, slug: str) -> Dict:
        """Install an add-on
        
        Args:
            slug: Add-on slug to install
        
        Returns:
            Installation result
        
        Note: This can take several minutes depending on add-on size
        """
        logger.info(f"Installing add-on: {slug}")
        return await self._request('POST', f'supervisor/addons/{slug}/install', timeout=600)
    
    async def uninstall_addon(self, slug: str) -> Dict:
        """Uninstall an add-on
        
        Args:
            slug: Add-on slug to uninstall
        """
        logger.info(f"Uninstalling add-on: {slug}")
        return await self._request('POST', f'supervisor/addons/{slug}/uninstall', timeout=300)
    
    async def start_addon(self, slug: str) -> Dict:
        """Start an add-on
        
        Args:
            slug: Add-on slug to start
        """
        logger.info(f"Starting add-on: {slug}")
        return await self._request('POST', f'supervisor/addons/{slug}/start')
    
    async def stop_addon(self, slug: str) -> Dict:
        """Stop an add-on
        
        Args:
            slug: Add-on slug to stop
        """
        logger.info(f"Stopping add-on: {slug}")
        return await self._request('POST', f'supervisor/addons/{slug}/stop')
    
    async def restart_addon(self, slug: str) -> Dict:
        """Restart an add-on
        
        Args:
            slug: Add-on slug to restart
        """
        logger.info(f"Restarting add-on: {slug}")
        return await self._request('POST', f'supervisor/addons/{slug}/restart')
    
    async def update_addon(self, slug: str) -> Dict:
        """Update an add-on to latest version
        
        Args:
            slug: Add-on slug to update
        """
        logger.info(f"Updating add-on: {slug}")
        return await self._request('POST', f'supervisor/addons/{slug}/update', timeout=600)
    
    # ==================== Add-on Configuration ====================
    
    async def get_addon_options(self, slug: str) -> Dict:
        """Get add-on configuration options
        
        Args:
            slug: Add-on slug
        
        Returns:
            Current add-on options
        """
        info = await self.get_addon_info(slug)
        return info.get('data', {}).get('options', {})
    
    async def set_addon_options(self, slug: str, options: Dict) -> Dict:
        """Set add-on configuration options
        
        Args:
            slug: Add-on slug
            options: Dictionary of configuration options
        
        Returns:
            Update result
        """
        logger.info(f"Configuring add-on {slug}: {options}")
        return await self._request('POST', f'supervisor/addons/{slug}/options', data={'options': options})
    
    # ==================== Store & Repositories ====================
    
    async def list_repositories(self) -> Dict:
        """Get list of add-on repositories"""
        return await self._request('GET', 'supervisor/store/repositories')
    
    async def add_repository(self, repository_url: str) -> Dict:
        """Add a custom add-on repository
        
        Args:
            repository_url: URL of repository to add
        """
        logger.info(f"Adding repository: {repository_url}")
        return await self._request('POST', 'supervisor/store/repositories', data={'repository': repository_url})
    
    async def remove_repository(self, repository_slug: str) -> Dict:
        """Remove an add-on repository
        
        Args:
            repository_slug: Slug of repository to remove
        """
        logger.info(f"Removing repository: {repository_slug}")
        return await self._request('DELETE', f'supervisor/store/repositories/{repository_slug}')

# Global Supervisor client instance
supervisor_client = SupervisorClient()

async def get_supervisor_client() -> SupervisorClient:
    """Get Supervisor client instance
    
    Raises:
        Exception: If Supervisor API is not available (not running as add-on)
    """
    if not supervisor_client.is_available():
        raise Exception("Supervisor API not available - agent must run as Home Assistant add-on for add-on management")
    return supervisor_client



