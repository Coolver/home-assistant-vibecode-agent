"""Home Assistant Supervisor API Client for Add-on Management"""
import os
import asyncio
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
            'X-Supervisor-Token': self.token,
            'Content-Type': 'application/json',
        }
        self._session: Optional[aiohttp.ClientSession] = None
        
        if not self.token:
            logger.warning("No SUPERVISOR_TOKEN found - Add-on management disabled")
        else:
            logger.info(f"SupervisorClient initialized - URL: {self.base_url}")
    
    def is_available(self) -> bool:
        """Check if Supervisor API is available (running as add-on)"""
        return bool(self.token)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create a shared aiohttp session for connection pooling."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=300),
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

    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, timeout: int = 300) -> Dict:
        """Make HTTP request to Supervisor API with retry on transient failures.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., 'addons', 'addons/core_mosquitto/install')
            data: Optional request body
            timeout: Request timeout in seconds (default 300 for install operations)
        """
        url = f"{self.base_url}/{endpoint}"
        logger.info(f"Supervisor API Request: {method} {url}")
        
        last_error: Optional[Exception] = None
        for attempt in range(self._MAX_RETRIES):
            try:
                session = await self._get_session()
                async with session.request(
                    method, 
                    url, 
                    headers=self.headers, 
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status in self._RETRYABLE_STATUSES and attempt < self._MAX_RETRIES - 1:
                        text = await response.text()
                        logger.warning(f"Supervisor API transient error {response.status}, retrying ({attempt + 1}/{self._MAX_RETRIES})...")
                        await asyncio.sleep(self._RETRY_BACKOFF[attempt])
                        continue

                    if response.status >= 400:
                        text = await response.text()
                        logger.error(f"Supervisor API error: {response.status} - {text}")
                        raise Exception(f"Supervisor API error: {response.status} - {text}")
                    
                    logger.debug(f"Supervisor API success: {method} {url} -> {response.status}")
                    
                    if response.status == 204:
                        return {"success": True, "message": "Operation completed"}
                    
                    return await response.json()
            except (aiohttp.ClientError, aiohttp.ServerDisconnectedError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < self._MAX_RETRIES - 1:
                    logger.warning(f"Supervisor connection error ({type(e).__name__}), retrying ({attempt + 1}/{self._MAX_RETRIES})...")
                    await asyncio.sleep(self._RETRY_BACKOFF[attempt])
                else:
                    logger.error(f"Connection error to Supervisor after {self._MAX_RETRIES} attempts: {e}")
                    raise Exception(f"Failed to connect to Supervisor: {e}")
        
        raise Exception(f"Failed to connect to Supervisor: {last_error}")
    
    # ==================== Add-on Information ====================
    
    async def list_addons(self) -> Dict:
        """Get list of all available add-ons (installed and available)
        
        NOTE: This endpoint returns limited list (installed + some available).
        For full catalog from all repositories, use list_store_addons().
        
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
        return await self._request('GET', 'addons')
    
    async def list_store_addons(self) -> Dict:
        """Get full catalog of all add-ons from add-on store
        
        Returns complete list of add-ons from all connected repositories,
        not just installed ones. Use this for browsing and recommendations.
        
        Returns:
            List of all add-ons available in connected repositories
        """
        return await self._request('GET', 'store')
    
    async def get_addon_info(self, slug: str) -> Dict:
        """Get detailed information about a specific add-on
        
        Args:
            slug: Add-on slug (e.g., 'core_mosquitto', 'a0d7b954_zigbee2mqtt')
        
        Returns:
            Detailed add-on information including config, state, logs, etc.
        """
        return await self._request('GET', f'addons/{slug}/info')
    
    async def get_addon_logs(self, slug: str) -> str:
        """Get add-on logs
        
        Args:
            slug: Add-on slug
        
        Returns:
            Plain text logs
        """
        url = f"{self.base_url}/addons/{slug}/logs"
        
        last_error: Optional[Exception] = None
        for attempt in range(self._MAX_RETRIES):
            try:
                session = await self._get_session()
                async with session.get(
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status in self._RETRYABLE_STATUSES and attempt < self._MAX_RETRIES - 1:
                        logger.warning(f"Supervisor logs transient error {response.status}, retrying ({attempt + 1}/{self._MAX_RETRIES})...")
                        await asyncio.sleep(self._RETRY_BACKOFF[attempt])
                        continue

                    if response.status >= 400:
                        text = await response.text()
                        raise Exception(f"Failed to get logs: {response.status} - {text}")
                    
                    return await response.text()
            except (aiohttp.ClientError, aiohttp.ServerDisconnectedError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < self._MAX_RETRIES - 1:
                    logger.warning(f"Supervisor logs connection error ({type(e).__name__}), retrying ({attempt + 1}/{self._MAX_RETRIES})...")
                    await asyncio.sleep(self._RETRY_BACKOFF[attempt])
                else:
                    raise Exception(f"Failed to get add-on logs: {e}")
        
        raise Exception(f"Failed to get add-on logs: {last_error}")

    # Journal sources the manager role may read. Kept to a fixed map so a
    # caller cannot turn this into an arbitrary Supervisor path.
    JOURNAL_SOURCES = {
        "core": "core/logs",
        "supervisor": "supervisor/logs",
        "host": "host/logs",
    }

    async def get_journal_logs(self, source: str, lines: int) -> str:
        """Read a Supervisor journal (Core, Supervisor, or the host).

        Uses the lines/no_colors query form. Supervisor ignores Range when
        lines is set, and no_colors asks it to drop ANSI escapes.
        """
        endpoint = self.JOURNAL_SOURCES.get(source)
        if endpoint is None:
            raise ValueError(f"Unknown log source: {source}")

        url = f"{self.base_url}/{endpoint}"
        headers = {**self.headers, "Accept": "text/plain"}
        params = {"lines": str(lines), "no_colors": ""}

        last_error: Optional[Exception] = None
        for attempt in range(self._MAX_RETRIES):
            try:
                session = await self._get_session()
                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status in self._RETRYABLE_STATUSES and attempt < self._MAX_RETRIES - 1:
                        logger.warning(
                            f"Supervisor journal transient error {response.status}, "
                            f"retrying ({attempt + 1}/{self._MAX_RETRIES})..."
                        )
                        await asyncio.sleep(self._RETRY_BACKOFF[attempt])
                        continue

                    if response.status >= 400:
                        text = (await response.text())[:300]
                        raise Exception(f"Failed to get {source} logs: {response.status} - {text}")

                    return await response.text()
            except (aiohttp.ClientError, aiohttp.ServerDisconnectedError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < self._MAX_RETRIES - 1:
                    logger.warning(
                        f"Supervisor journal connection error ({type(e).__name__}), "
                        f"retrying ({attempt + 1}/{self._MAX_RETRIES})..."
                    )
                    await asyncio.sleep(self._RETRY_BACKOFF[attempt])
                else:
                    raise Exception(f"Failed to get {source} logs: {e}")

        raise Exception(f"Failed to get {source} logs: {last_error}")
    
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
        return await self._request('POST', f'addons/{slug}/install', timeout=600)
    
    async def uninstall_addon(self, slug: str) -> Dict:
        """Uninstall an add-on
        
        Args:
            slug: Add-on slug to uninstall
        """
        logger.info(f"Uninstalling add-on: {slug}")
        return await self._request('POST', f'addons/{slug}/uninstall', timeout=300)
    
    async def start_addon(self, slug: str) -> Dict:
        """Start an add-on
        
        Args:
            slug: Add-on slug to start
        """
        logger.info(f"Starting add-on: {slug}")
        return await self._request('POST', f'addons/{slug}/start')
    
    async def stop_addon(self, slug: str) -> Dict:
        """Stop an add-on
        
        Args:
            slug: Add-on slug to stop
        """
        logger.info(f"Stopping add-on: {slug}")
        return await self._request('POST', f'addons/{slug}/stop')
    
    async def restart_addon(self, slug: str) -> Dict:
        """Restart an add-on
        
        Args:
            slug: Add-on slug to restart
        """
        logger.info(f"Restarting add-on: {slug}")
        return await self._request('POST', f'addons/{slug}/restart')
    
    async def update_addon(self, slug: str) -> Dict:
        """Update an add-on to latest version
        
        Args:
            slug: Add-on slug to update
        """
        logger.info(f"Updating add-on: {slug}")
        return await self._request('POST', f'addons/{slug}/update', timeout=600)
    
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
        # Option values often hold passwords; log only which keys are set.
        logger.info(f"Configuring add-on {slug}: options {sorted(options)}")
        return await self._request('POST', f'addons/{slug}/options', data={'options': options})
    
    # ==================== Store & Repositories ====================
    
    async def list_repositories(self) -> Dict:
        """Get list of add-on repositories"""
        return await self._request('GET', 'store/repositories')
    
    async def add_repository(self, repository_url: str) -> Dict:
        """Add a custom add-on repository
        
        Args:
            repository_url: URL of repository to add
        """
        logger.info(f"Adding repository: {repository_url}")
        return await self._request('POST', 'store/repositories', data={'repository': repository_url})
    
    async def remove_repository(self, repository_slug: str) -> Dict:
        """Remove an add-on repository
        
        Args:
            repository_slug: Slug of repository to remove
        """
        logger.info(f"Removing repository: {repository_slug}")
        return await self._request('DELETE', f'store/repositories/{repository_slug}')

# Global Supervisor client instance
supervisor_client = SupervisorClient()

async def get_supervisor_client() -> SupervisorClient:
    """Get Supervisor client instance
    
    Raises:
        HTTPException(501): If Supervisor API is not available (not running as add-on)
    """
    if not supervisor_client.is_available():
        from fastapi import HTTPException
        raise HTTPException(
            status_code=501,
            detail="Add-on management requires Home Assistant Supervisor (HAOS). "
                   "Not available in standalone/Docker mode. "
                   "Install Home Assistant OS or use Supervised installation for add-on support."
        )
    return supervisor_client



