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
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        suppress_404_logging: bool = False
    ) -> Dict:
        """Make HTTP request to HA API
        
        Args:
            suppress_404_logging: If True, 404 errors will be logged as DEBUG instead of ERROR
        """
        url = f"{self.url}/api/{endpoint}"
        
        # For POST requests, aiohttp handles query params correctly via params argument
        # No need to manually append to URL - let aiohttp handle it
        
        # Use custom timeout or default 240 seconds (4 minutes)
        # Long operations like backup_full, file operations, and Git cleanup need more time
        timeout_seconds = timeout if timeout is not None else 240
        
        # Debug logging
        token_preview = f"{self.token[:20]}..." if self.token else "EMPTY"
        logger.info(f"HA API Request: {method} {url}, Data: {data}, Params: {params}, Timeout: {timeout_seconds}s")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, 
                    url, 
                    headers=self.headers, 
                    json=data,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=timeout_seconds)
                ) as response:
                    if response.status >= 400:
                        text = await response.text()
                        # 404 is often expected (entity not found), log as DEBUG if suppressed
                        if response.status == 404 and suppress_404_logging:
                            logger.debug(f"HA API 404 (expected): {text} | URL: {url}")
                        else:
                            logger.error(f"HA API error: {response.status} - {text} | URL: {url} | Data: {data} | Params: {params} | Token used: {token_preview}")
                        raise Exception(f"HA API error: {response.status} - {text}")
                    
                    logger.debug(f"HA API success: {method} {url} -> {response.status}")
                    return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Connection error to HA: {e}")
            raise Exception(f"Failed to connect to Home Assistant: {e}")
    
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
    
    # ==================== Automation API ====================
    
    async def list_automations(self) -> List[Dict]:
        """
        List all automations from Home Assistant (via Entity Registry + file system)
        
        Returns all automations that HA has loaded, regardless of source:
        - From automations.yaml
        - From packages/*.yaml
        - Created via UI (stored in .storage)
        
        Note: Home Assistant doesn't provide WebSocket API for listing automations.
        We use Entity Registry to get all automation entities, then collect their
        configurations from files and .storage.
        
        Returns:
            List of automation configurations
        """
        try:
            # Import here to avoid circular dependency
            from app.services.ha_websocket import get_ws_client
            from app.services.file_manager import file_manager
            import json
            import yaml
            from pathlib import Path
            
            # Get all automation entities from Entity Registry
            ws_client = await get_ws_client()
            entity_registry = await ws_client.get_entity_registry_list()
            
            # Filter automation entities
            automation_entities = [
                e for e in entity_registry 
                if e.get('entity_id', '').startswith('automation.')
            ]
            
            automations = []
            automation_ids_seen = set()
            
            # OPTIMIZATION: Read all files ONCE and create a cache
            # This prevents reading automations.yaml multiple times (once per automation from Entity Registry)
            automation_cache = {}  # automation_id -> config dict
            
            # Read automations.yaml ONCE
            try:
                content = await file_manager.read_file('automations.yaml', suppress_not_found_logging=True)
                file_automations = yaml.safe_load(content) or []
                if isinstance(file_automations, list):
                    for auto in file_automations:
                        auto_id = auto.get('id')
                        if auto_id:
                            automation_cache[auto_id] = auto
            except Exception:
                pass
            
            # Read packages/*.yaml files ONCE
            try:
                packages_dir = file_manager.config_path / 'packages'
                if packages_dir.exists():
                    for yaml_file in packages_dir.rglob('*.yaml'):
                        try:
                            content = yaml_file.read_text(encoding='utf-8')
                            data = yaml.safe_load(content)
                            if isinstance(data, dict) and 'automation' in data:
                                pkg_automations = data['automation']
                                if isinstance(pkg_automations, list):
                                    for auto in pkg_automations:
                                        auto_id = auto.get('id')
                                        if auto_id:
                                            automation_cache[auto_id] = auto
                                elif isinstance(pkg_automations, dict):
                                    # Handle dict format: {id: config}
                                    for auto_id, auto_config in pkg_automations.items():
                                        auto = dict(auto_config) if isinstance(auto_config, dict) else auto_config
                                        if isinstance(auto, dict):
                                            auto['id'] = auto_id
                                        automation_cache[auto_id] = auto
                        except Exception:
                            continue
            except Exception:
                pass
            
            # Read .storage (UI-created automations) ONCE
            try:
                storage_file = file_manager.config_path / '.storage' / 'automation.storage'
                if storage_file.exists():
                    content = storage_file.read_text(encoding='utf-8')
                    storage_data = json.loads(content)
                    if 'data' in storage_data and 'automations' in storage_data['data']:
                        for auto in storage_data['data']['automations']:
                            auto_id = auto.get('id')
                            if auto_id:
                                automation_cache[auto_id] = auto
            except Exception:
                pass
            
            # Now process Entity Registry automations using the cache
            for entity in automation_entities:
                entity_id = entity.get('entity_id', '')
                if not entity_id.startswith('automation.'):
                    continue
                
                # Extract automation_id from entity_id (automation.xxx -> xxx)
                automation_id = entity_id.replace('automation.', '', 1)
                
                # Also check capabilities.id (for UI-created automations)
                capabilities = entity.get('capabilities', {})
                if isinstance(capabilities, dict):
                    alt_id = capabilities.get('id')
                    if alt_id and alt_id != automation_id:
                        automation_id = alt_id
                
                if automation_id in automation_ids_seen:
                    continue
                automation_ids_seen.add(automation_id)
                
                # Get config from cache (no file reading!)
                config = automation_cache.get(automation_id)
                if config:
                    automations.append(config)
                else:
                    # If not in cache, at least add the ID
                    automations.append({'id': automation_id})
            
            # Add file-based automations not in Entity Registry
            for auto_id, auto_config in automation_cache.items():
                if auto_id not in automation_ids_seen:
                    automations.append(auto_config)
                    automation_ids_seen.add(auto_id)
            
            return automations
            
        except Exception as e:
            logger.error(f"Failed to list automations: {e}")
            raise
    
    async def get_automation(self, automation_id: str) -> Dict:
        """
        Get single automation configuration by ID (via files + .storage)
        
        Args:
            automation_id: Automation ID
            
        Returns:
            Automation configuration dict
        """
        try:
            from app.services.file_manager import file_manager
            import yaml
            import json
            from pathlib import Path
            
            # Try to find in automations.yaml
            try:
                content = await file_manager.read_file('automations.yaml', suppress_not_found_logging=True)
                automations = yaml.safe_load(content) or []
                if isinstance(automations, list):
                    for auto in automations:
                        if auto.get('id') == automation_id:
                            return auto
            except Exception:
                pass
            
            # Try to find in packages/*.yaml
            try:
                packages_dir = file_manager.config_path / 'packages'
                if packages_dir.exists():
                    for yaml_file in packages_dir.rglob('*.yaml'):
                        try:
                            content = yaml_file.read_text(encoding='utf-8')
                            data = yaml.safe_load(content)
                            if isinstance(data, dict) and 'automation' in data:
                                pkg_automations = data['automation']
                                if isinstance(pkg_automations, list):
                                    for auto in pkg_automations:
                                        if auto.get('id') == automation_id:
                                            return auto
                                elif isinstance(pkg_automations, dict):
                                    if automation_id in pkg_automations:
                                        auto = dict(pkg_automations[automation_id]) if isinstance(pkg_automations[automation_id], dict) else pkg_automations[automation_id]
                                        if isinstance(auto, dict):
                                            auto['id'] = automation_id
                                        return auto
                        except Exception:
                            continue
            except Exception:
                pass
            
            # Try to find in .storage (UI-created automations)
            try:
                storage_file = file_manager.config_path / '.storage' / 'automation.storage'
                if storage_file.exists():
                    content = storage_file.read_text(encoding='utf-8')
                    storage_data = json.loads(content)
                    if 'data' in storage_data and 'automations' in storage_data['data']:
                        for auto in storage_data['data']['automations']:
                            if auto.get('id') == automation_id:
                                return auto
            except Exception:
                pass
            
            raise Exception(f"Automation not found: {automation_id}")
            
        except Exception as e:
            error_msg = str(e)
            if 'not found' in error_msg.lower():
                raise Exception(f"Automation not found: {automation_id}")
            logger.error(f"Failed to get automation {automation_id}: {e}")
            raise
    
    async def create_automation(self, automation_config: Dict) -> Dict:
        """
        Create new automation via Home Assistant REST API
        
        Uses POST /api/config/automation/config/{entity_id} endpoint.
        Home Assistant automatically determines where to store the automation
        (automations.yaml, packages/*, or .storage).
        
        Args:
            automation_config: Automation configuration dict (must include 'id')
            
        Returns:
            Created automation configuration
        """
        automation_id = automation_config.get('id')
        if not automation_id:
            raise ValueError("Automation config must include 'id' field")
        
        try:
            # Use REST API endpoint: POST /api/config/automation/config/{entity_id}
            entity_id = f"automation.{automation_id}"
            endpoint = f"config/automation/config/{entity_id}"
            
            result = await self._request('POST', endpoint, data=automation_config)
            
            logger.info(f"Created automation via REST API: {automation_id}")
            return result
        except Exception as e:
            error_msg = str(e)
            if '409' in error_msg or 'already exists' in error_msg.lower():
                raise ValueError(f"Automation with ID '{automation_id}' already exists")
            logger.error(f"Failed to create automation {automation_id} via REST API: {e}")
            raise
    
    async def update_automation(self, automation_id: str, automation_config: Dict) -> Dict:
        """
        Update existing automation via Home Assistant REST API
        
        Uses POST /api/config/automation/config/{entity_id} endpoint.
        Home Assistant automatically updates the automation in its original location.
        
        Args:
            automation_id: Automation ID
            automation_config: Updated automation configuration
            
        Returns:
            Updated automation configuration
        """
        try:
            # Ensure 'id' matches
            config = dict(automation_config)
            config['id'] = automation_id
            
            # Use REST API endpoint: POST /api/config/automation/config/{entity_id}
            entity_id = f"automation.{automation_id}"
            endpoint = f"config/automation/config/{entity_id}"
            
            result = await self._request('POST', endpoint, data=config)
            
            logger.info(f"Updated automation via REST API: {automation_id}")
            return result
        except Exception as e:
            error_msg = str(e)
            if '404' in error_msg or 'not found' in error_msg.lower():
                raise Exception(f"Automation '{automation_id}' not found")
            logger.error(f"Failed to update automation {automation_id} via REST API: {e}")
            raise
    
    async def _find_automation_location(self, automation_id: str) -> Dict:
        """
        Find where an automation is stored (automations.yaml, packages/*.yaml, or .storage)
        
        Returns:
            Dict with keys: 'location' ('automations.yaml', 'packages', or 'storage'),
                           'file_path' (relative path), 'index' (if applicable)
        """
        from app.services.file_manager import file_manager
        import yaml
        import json
        from pathlib import Path
        
        # Try automations.yaml
        try:
            content = await file_manager.read_file('automations.yaml', suppress_not_found_logging=True)
            automations = yaml.safe_load(content) or []
            if isinstance(automations, list):
                for i, auto in enumerate(automations):
                    if auto.get('id') == automation_id:
                        return {'location': 'automations.yaml', 'file_path': 'automations.yaml', 'index': i}
        except Exception:
            pass
        
        # Try packages/*.yaml
        try:
            packages_dir = file_manager.config_path / 'packages'
            if packages_dir.exists():
                for yaml_file in packages_dir.rglob('*.yaml'):
                    try:
                        content = yaml_file.read_text(encoding='utf-8')
                        data = yaml.safe_load(content)
                        if isinstance(data, dict) and 'automation' in data:
                            pkg_automations = data['automation']
                            rel_path = yaml_file.relative_to(file_manager.config_path)
                            
                            if isinstance(pkg_automations, list):
                                for i, auto in enumerate(pkg_automations):
                                    if auto.get('id') == automation_id:
                                        return {'location': 'packages', 'file_path': str(rel_path), 'index': i, 'format': 'list'}
                            elif isinstance(pkg_automations, dict):
                                if automation_id in pkg_automations:
                                    return {'location': 'packages', 'file_path': str(rel_path), 'key': automation_id, 'format': 'dict'}
                    except Exception:
                        continue
        except Exception:
            pass
        
        # Try .storage (UI-created)
        try:
            storage_file = file_manager.config_path / '.storage' / 'automation.storage'
            if storage_file.exists():
                content = storage_file.read_text(encoding='utf-8')
                storage_data = json.loads(content)
                if 'data' in storage_data and 'automations' in storage_data['data']:
                    for i, auto in enumerate(storage_data['data']['automations']):
                        if auto.get('id') == automation_id:
                            return {'location': 'storage', 'file_path': '.storage/automation.storage', 'index': i}
        except Exception:
            pass
        
        return None
    
    async def delete_automation(self, automation_id: str) -> Dict:
        """
        Delete automation from its original location (file-based approach)
        
        Note: Home Assistant REST API does not support DELETE method for automations.
        We find where the automation is stored and remove it from there, then remove
        from Entity Registry and reload automations.
        
        Args:
            automation_id: Automation ID to delete
            
        Returns:
            Deletion result
        """
        try:
            from app.services.file_manager import file_manager
            import yaml
            import json
            
            # Find where automation is located
            location = await self._find_automation_location(automation_id)
            if not location:
                raise Exception(f"Automation '{automation_id}' not found")
            
            file_path = location['file_path']
            
            if location['location'] == 'automations.yaml':
                # Delete from automations.yaml
                content = await file_manager.read_file(file_path)
                automations = yaml.safe_load(content) or []
                automations = [auto for auto in automations if auto.get('id') != automation_id]
                new_content = yaml.dump(automations, allow_unicode=True, default_flow_style=False, sort_keys=False)
                await file_manager.write_file(file_path, new_content, create_backup=True)
                
            elif location['location'] == 'packages':
                # Delete from packages/*.yaml
                content = await file_manager.read_file(file_path)
                data = yaml.safe_load(content) or {}
                if location['format'] == 'list':
                    data['automation'] = [auto for auto in data['automation'] if auto.get('id') != automation_id]
                else:  # dict format
                    if location['key'] in data['automation']:
                        del data['automation'][location['key']]
                new_content = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
                await file_manager.write_file(file_path, new_content, create_backup=True)
                
            elif location['location'] == 'storage':
                # Delete from .storage/automation.storage (JSON)
                content = await file_manager.read_file(file_path)
                storage_data = json.loads(content)
                storage_data['data']['automations'] = [auto for auto in storage_data['data']['automations'] if auto.get('id') != automation_id]
                new_content = json.dumps(storage_data, indent=2, ensure_ascii=False)
                await file_manager.write_file(file_path, new_content, create_backup=True)
            
            # Remove from Entity Registry
            try:
                from app.services.ha_websocket import get_ws_client
                ws_client = await get_ws_client()
                entity_id = f"automation.{automation_id}"
                await ws_client.remove_entity_registry_entry(entity_id)
                logger.debug(f"Removed automation from Entity Registry: {entity_id}")
            except Exception as reg_error:
                logger.warning(f"Failed to remove automation from Entity Registry: {reg_error}")
            
            # Reload automations in Home Assistant
            try:
                from app.services.ha_websocket import get_ws_client
                ws_client = await get_ws_client()
                await ws_client.call_service('automation', 'reload')
                logger.info(f"Reloaded automations after deleting: {automation_id}")
            except Exception as reload_error:
                logger.warning(f"Failed to reload automations: {reload_error}. Automation deleted but may need manual reload.")
            
            logger.info(f"Deleted automation from {file_path}: {automation_id}")
            return {'success': True, 'automation_id': automation_id}
        except Exception as e:
            error_msg = str(e)
            if 'not found' in error_msg.lower():
                raise Exception(f"Automation not found: {automation_id}")
            logger.error(f"Failed to delete automation {automation_id}: {e}")
            raise
    
    # ==================== Script API ====================
    
    async def list_scripts(self) -> Dict[str, Dict]:
        """
        List all scripts from Home Assistant (via Entity Registry + file system)
        
        Returns all scripts that HA has loaded, regardless of source.
        
        Note: Home Assistant doesn't provide WebSocket API for listing scripts.
        We use Entity Registry to get all script entities, then collect their
        configurations from files and .storage.
        
        Returns:
            Dict where keys are script_ids and values are script configs
        """
        try:
            # Import here to avoid circular dependency
            from app.services.ha_websocket import get_ws_client
            from app.services.file_manager import file_manager
            import json
            import yaml
            from pathlib import Path
            
            # Get all script entities from Entity Registry
            ws_client = await get_ws_client()
            entity_registry = await ws_client.get_entity_registry_list()
            
            # Filter script entities
            script_entities = [
                e for e in entity_registry 
                if e.get('entity_id', '').startswith('script.')
            ]
            
            # Cache for script configurations (read files ONCE at the beginning)
            script_cache = {}
            
            # Read all script files ONCE at the beginning
            try:
                # Read scripts.yaml
                try:
                    content = await file_manager.read_file('scripts.yaml', suppress_not_found_logging=True)
                    file_scripts = yaml.safe_load(content) or {}
                    if isinstance(file_scripts, dict):
                        script_cache.update(file_scripts)
                except Exception:
                    pass
                
                # Read packages/*.yaml files
                try:
                    packages_dir = file_manager.config_path / 'packages'
                    if packages_dir.exists():
                        for yaml_file in packages_dir.rglob('*.yaml'):
                            try:
                                content = yaml_file.read_text(encoding='utf-8')
                                data = yaml.safe_load(content)
                                if isinstance(data, dict) and 'script' in data:
                                    pkg_scripts = data['script']
                                    if isinstance(pkg_scripts, dict):
                                        script_cache.update(pkg_scripts)
                            except Exception:
                                continue
                except Exception:
                    pass
                
                # Read .storage/script.storage (UI-created scripts)
                try:
                    storage_file = file_manager.config_path / '.storage' / 'script.storage'
                    if storage_file.exists():
                        content = storage_file.read_text(encoding='utf-8')
                        storage_data = json.loads(content)
                        if 'data' in storage_data and 'scripts' in storage_data['data']:
                            storage_scripts = storage_data['data']['scripts']
                            if isinstance(storage_scripts, dict):
                                script_cache.update(storage_scripts)
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"Failed to read scripts from files: {e}")
            
            scripts = {}
            script_ids_seen = set()
            
            # Get script IDs from entity registry and use cache (no file reads here)
            for entity in script_entities:
                entity_id = entity.get('entity_id', '')
                if not entity_id.startswith('script.'):
                    continue
                
                # Extract script_id from entity_id (script.xxx -> xxx)
                script_id = entity_id.replace('script.', '', 1)
                
                if script_id in script_ids_seen:
                    continue
                script_ids_seen.add(script_id)
                
                # Use cached config if available, otherwise empty dict
                if script_id in script_cache:
                    scripts[script_id] = script_cache[script_id]
                else:
                    # Script in registry but not in files - might be UI-created
                    scripts[script_id] = {}
            
            # Also add scripts from cache that weren't in entity registry
            for script_id, script_config in script_cache.items():
                if script_id not in script_ids_seen:
                    scripts[script_id] = script_config
                    script_ids_seen.add(script_id)
            
            return scripts
            
        except Exception as e:
            logger.error(f"Failed to list scripts: {e}")
            raise
    
    async def get_script(self, script_id: str) -> Dict:
        """
        Get single script configuration by ID (via files + .storage)
        
        Args:
            script_id: Script ID
            
        Returns:
            Script configuration dict
        """
        try:
            from app.services.file_manager import file_manager
            import yaml
            import json
            from pathlib import Path
            
            # Try to find in scripts.yaml
            try:
                content = await file_manager.read_file('scripts.yaml', suppress_not_found_logging=True)
                scripts = yaml.safe_load(content) or {}
                if isinstance(scripts, dict) and script_id in scripts:
                    return scripts[script_id]
            except Exception:
                pass
            
            # Try to find in packages/*.yaml
            try:
                packages_dir = file_manager.config_path / 'packages'
                if packages_dir.exists():
                    for yaml_file in packages_dir.rglob('*.yaml'):
                        try:
                            content = yaml_file.read_text(encoding='utf-8')
                            data = yaml.safe_load(content)
                            if isinstance(data, dict) and 'script' in data:
                                pkg_scripts = data['script']
                                if isinstance(pkg_scripts, dict) and script_id in pkg_scripts:
                                    return pkg_scripts[script_id]
                        except Exception:
                            continue
            except Exception:
                pass
            
            # Try to find in .storage (UI-created scripts)
            try:
                storage_file = file_manager.config_path / '.storage' / 'script.storage'
                if storage_file.exists():
                    content = storage_file.read_text(encoding='utf-8')
                    storage_data = json.loads(content)
                    if 'data' in storage_data and 'scripts' in storage_data['data']:
                        scripts_dict = storage_data['data']['scripts']
                        if script_id in scripts_dict:
                            return scripts_dict[script_id]
            except Exception:
                pass
            
            raise Exception(f"Script not found: {script_id}")
            
        except Exception as e:
            error_msg = str(e)
            if 'not found' in error_msg.lower():
                raise Exception(f"Script not found: {script_id}")
            logger.error(f"Failed to get script {script_id}: {e}")
            raise
    
    async def create_script(self, script_id: str, script_config: Dict) -> Dict:
        """
        Create new script via Home Assistant REST API
        
        Uses POST /api/config/script/config/{script_id} endpoint.
        Home Assistant automatically determines where to store the script
        (scripts.yaml, packages/*, or .storage).
        
        Args:
            script_id: Script ID
            script_config: Script configuration dict
            
        Returns:
            Created script configuration
        """
        try:
            # Use REST API endpoint: POST /api/config/script/config/{script_id}
            endpoint = f"config/script/config/{script_id}"
            
            result = await self._request('POST', endpoint, data=script_config)
            
            logger.info(f"Created script via REST API: {script_id}")
            return result
        except Exception as e:
            error_msg = str(e)
            if '409' in error_msg or 'already exists' in error_msg.lower():
                raise ValueError(f"Script with ID '{script_id}' already exists")
            logger.error(f"Failed to create script {script_id} via REST API: {e}")
            raise
    
    async def update_script(self, script_id: str, script_config: Dict) -> Dict:
        """
        Update existing script via Home Assistant REST API
        
        Uses POST /api/config/script/config/{script_id} endpoint.
        Home Assistant automatically updates the script in its original location.
        
        Args:
            script_id: Script ID
            script_config: Updated script configuration
            
        Returns:
            Updated script configuration
        """
        try:
            # Use REST API endpoint: POST /api/config/script/config/{script_id}
            endpoint = f"config/script/config/{script_id}"
            
            result = await self._request('POST', endpoint, data=script_config)
            
            logger.info(f"Updated script via REST API: {script_id}")
            return result
        except Exception as e:
            error_msg = str(e)
            if '404' in error_msg or 'not found' in error_msg.lower():
                raise Exception(f"Script '{script_id}' not found")
            logger.error(f"Failed to update script {script_id} via REST API: {e}")
            raise
    
    async def _find_script_location(self, script_id: str) -> Dict:
        """
        Find where a script is stored (scripts.yaml, packages/*.yaml, or .storage)
        
        Returns:
            Dict with keys: 'location' ('scripts.yaml', 'packages', or 'storage'),
                           'file_path' (relative path)
        """
        from app.services.file_manager import file_manager
        import yaml
        import json
        from pathlib import Path
        
        # Try scripts.yaml
        try:
            content = await file_manager.read_file('scripts.yaml', suppress_not_found_logging=True)
            scripts = yaml.safe_load(content) or {}
            if isinstance(scripts, dict) and script_id in scripts:
                return {'location': 'scripts.yaml', 'file_path': 'scripts.yaml'}
        except Exception:
            pass
        
        # Try packages/*.yaml
        try:
            packages_dir = file_manager.config_path / 'packages'
            if packages_dir.exists():
                for yaml_file in packages_dir.rglob('*.yaml'):
                    try:
                        content = yaml_file.read_text(encoding='utf-8')
                        data = yaml.safe_load(content)
                        if isinstance(data, dict) and 'script' in data:
                            pkg_scripts = data['script']
                            rel_path = yaml_file.relative_to(file_manager.config_path)
                            
                            if isinstance(pkg_scripts, dict) and script_id in pkg_scripts:
                                return {'location': 'packages', 'file_path': str(rel_path)}
                    except Exception:
                        continue
        except Exception:
            pass
        
        # Try .storage (UI-created)
        try:
            storage_file = file_manager.config_path / '.storage' / 'script.storage'
            if storage_file.exists():
                content = storage_file.read_text(encoding='utf-8')
                storage_data = json.loads(content)
                if 'data' in storage_data and 'scripts' in storage_data['data']:
                    scripts_dict = storage_data['data']['scripts']
                    if script_id in scripts_dict:
                        return {'location': 'storage', 'file_path': '.storage/script.storage'}
        except Exception:
            pass
        
        return None
    
    async def delete_script(self, script_id: str) -> Dict:
        """
        Delete script from its original location (file-based approach)
        
        Note: Home Assistant REST API does not support DELETE method for scripts
        (only works for UI-created scripts, returns 405 for YAML-defined ones).
        We find where the script is stored and remove it from there, then remove
        from Entity Registry and reload scripts.
        
        Args:
            script_id: Script ID to delete
            
        Returns:
            Deletion result
        """
        try:
            from app.services.file_manager import file_manager
            import yaml
            import json
            
            # Find where script is located
            location = await self._find_script_location(script_id)
            if not location:
                raise Exception(f"Script '{script_id}' not found")
            
            file_path = location['file_path']
            
            if location['location'] == 'scripts.yaml':
                # Delete from scripts.yaml
                content = await file_manager.read_file(file_path)
                scripts = yaml.safe_load(content) or {}
                if script_id in scripts:
                    del scripts[script_id]
                new_content = yaml.dump(scripts, allow_unicode=True, default_flow_style=False, sort_keys=False)
                await file_manager.write_file(file_path, new_content, create_backup=True)
                
            elif location['location'] == 'packages':
                # Delete from packages/*.yaml
                content = await file_manager.read_file(file_path)
                data = yaml.safe_load(content) or {}
                if 'script' in data and script_id in data['script']:
                    del data['script'][script_id]
                new_content = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
                await file_manager.write_file(file_path, new_content, create_backup=True)
                
            elif location['location'] == 'storage':
                # Delete from .storage/script.storage (JSON)
                content = await file_manager.read_file(file_path)
                storage_data = json.loads(content)
                if 'data' in storage_data and 'scripts' in storage_data['data']:
                    if script_id in storage_data['data']['scripts']:
                        del storage_data['data']['scripts'][script_id]
                new_content = json.dumps(storage_data, indent=2, ensure_ascii=False)
                await file_manager.write_file(file_path, new_content, create_backup=True)
            
            # Remove from Entity Registry
            try:
                from app.services.ha_websocket import get_ws_client
                ws_client = await get_ws_client()
                entity_id = f"script.{script_id}"
                await ws_client.remove_entity_registry_entry(entity_id)
                logger.debug(f"Removed script from Entity Registry: {entity_id}")
            except Exception as reg_error:
                logger.warning(f"Failed to remove script from Entity Registry: {reg_error}")
            
            # Reload scripts in Home Assistant
            try:
                from app.services.ha_websocket import get_ws_client
                ws_client = await get_ws_client()
                await ws_client.call_service('script', 'reload')
                logger.info(f"Reloaded scripts after deleting: {script_id}")
            except Exception as reload_error:
                logger.warning(f"Failed to reload scripts: {reload_error}. Script deleted but may need manual reload.")
            
            logger.info(f"Deleted script from {file_path}: {script_id}")
            return {'success': True, 'script_id': script_id}
        except Exception as e:
            error_msg = str(e)
            if 'not found' in error_msg.lower():
                raise Exception(f"Script not found: {script_id}")
            logger.error(f"Failed to delete script {script_id}: {e}")
            raise

# Global client instance
ha_client = HomeAssistantClient()

