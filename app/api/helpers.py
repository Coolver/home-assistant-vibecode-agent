"""Helpers API endpoints"""
from fastapi import APIRouter, HTTPException, Query
import logging
import os
import yaml
from typing import Dict, Any, Optional

from app.models.schemas import HelperCreate, Response
from app.services.ha_client import ha_client
from app.services.ha_websocket import get_ws_client
from app.services.git_manager import git_manager

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')

CONFIG_FILE = "/config/configuration.yaml"

# Each helper-type domain gets its own YAML file which is referenced from configuration.yaml via:
#   <domain>: !include <file>
# For example:
#   group: !include groups.yaml
#   utility_meter: !include utility_meter.yaml
HELPER_FILES = {
    'input_boolean': '/config/input_boolean.yaml',
    'input_text': '/config/input_text.yaml',
    'input_number': '/config/input_number.yaml',
    'input_datetime': '/config/input_datetime.yaml',
    'input_select': '/config/input_select.yaml',
    # YAML-based helpers that behave similarly to input_* from AI perspective
    # These are not "input helpers" in HA UI, but are commonly used as building blocks
    # and can be safely managed via YAML with the same pattern.
    'group': '/config/groups.yaml',
    'utility_meter': '/config/utility_meter.yaml',
}


def _load_helper_file(domain: str) -> Dict[str, Any]:
    """Load helper file for specific domain"""
    file_path = HELPER_FILES.get(domain)
    if not file_path or not os.path.exists(file_path):
        return {}
    
    with open(file_path, 'r') as f:
        content = yaml.safe_load(f) or {}
    return content


def _save_helper_file(domain: str, data: Dict[str, Any]) -> None:
    """Save helper file for specific domain"""
    file_path = HELPER_FILES.get(domain)
    if not file_path:
        raise ValueError(f"Unknown domain: {domain}")
    
    with open(file_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    logger.info(f"Saved {file_path}")


def _ensure_domain_in_config(domain: str) -> None:
    """Ensure helper domain is included in configuration.yaml"""
    if not os.path.exists(CONFIG_FILE):
        logger.warning(f"{CONFIG_FILE} not found")
        return
    
    with open(CONFIG_FILE, 'r') as f:
        config_content = f.read()
    
    file_name = HELPER_FILES[domain].split('/')[-1]  # Get filename without path
    include_line = f"{domain}: !include {file_name}"
    
    # Check if already includes this domain
    if include_line in config_content:
        logger.info(f"{domain} already referenced in configuration.yaml")
        return
    
    # Add reference at the end
    with open(CONFIG_FILE, 'a') as f:
        f.write(f'\n{include_line}\n')
    
    logger.info(f"Added {domain} reference to configuration.yaml")


def _generate_entity_id(domain: str, name: str, existing_helpers: Dict) -> str:
    """Generate entity_id from name"""
    # Convert name to entity_id format: lowercase, replace spaces with underscores
    base_id = name.lower().replace(' ', '_').replace('-', '_')
    base_id = ''.join(c for c in base_id if c.isalnum() or c == '_')
    
    # Check if exists in current helpers
    entity_id = base_id
    counter = 1
    
    while entity_id in existing_helpers:
        entity_id = f"{base_id}_{counter}"
        counter += 1
    
    return entity_id


@router.get("/debug/services")
async def debug_services():
    """Debug endpoint to see available services for helpers"""
    try:
        ws_client = await get_ws_client()
        all_services = await ws_client.get_services()
        
        # Extract helper-related services
        helper_services = {}
        for domain in ['input_boolean', 'input_text', 'input_number', 'input_datetime', 'input_select', 'group', 'utility_meter']:
            if domain in all_services:
                helper_services[domain] = all_services[domain]
        
        return {
            "success": True,
            "helper_services": helper_services
        }
    except Exception as e:
        logger.error(f"Failed to get services: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_helpers():
    """
    List all helper-like entities
    
    Returns all entities from helper-related domains:
    - input_boolean
    - input_text
    - input_number
    - input_datetime
    - input_select
    - group
    - utility_meter
    
    Example response:
    ```json
    {
      "success": true,
      "count": 15,
      "helpers": [
        {
          "entity_id": "input_boolean.climate_system_enabled",
          "state": "on",
          "attributes": {...}
        }
      ]
    }
    ```
    """
    try:
        # Get all entities
        all_states = await ha_client.get_states()
        
        # Filter helper-like entities
        helper_domains = ['input_boolean', 'input_text', 'input_number', 'input_datetime', 'input_select', 'group', 'utility_meter']
        helpers = [
            entity for entity in all_states 
            if any(entity['entity_id'].startswith(f"{domain}.") for domain in helper_domains)
        ]
        
        logger.info(f"Listed {len(helpers)} helpers")
        
        return {
            "success": True,
            "count": len(helpers),
            "helpers": helpers
        }
    except Exception as e:
        logger.error(f"Failed to list helpers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create", response_model=Response)
async def create_helper(helper: HelperCreate):
    """
    Create helper via YAML configuration
    
    **Method:** Writes to dedicated YAML file per domain and reloads the integration
    
    **Helper types (YAML-managed):**
    - `input_boolean` - Toggle/switch
    - `input_text` - Text input
    - `input_number` - Number slider
    - `input_datetime` - Date/time picker
    - `input_select` - Dropdown selection
    - `group` - Entity groups (living_room_lights, etc.)
    - `utility_meter` - Utility meter tracking (daily_energy, monthly_gas, etc.)
    
    **Example request (Boolean):**
    ```json
    {
      "type": "input_boolean",
      "config": {
        "name": "My Switch",
        "icon": "mdi:toggle-switch",
        "initial": false
      }
    }
    ```
    
    **Example request (Number):**
    ```json
    {
      "type": "input_number",
      "config": {
        "name": "My Number",
        "min": 0,
        "max": 100,
        "step": 5,
        "unit_of_measurement": "°C",
        "icon": "mdi:thermometer"
      }
    }
    ```
    """
    try:
        # Validate helper type
        valid_types = ['input_boolean', 'input_text', 'input_number', 'input_datetime', 'input_select', 'group', 'utility_meter']
        if helper.type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid helper type. Must be one of: {', '.join(valid_types)}")
        
        # Extract name from config (required for all supported helper-like types)
        if 'name' not in helper.config:
            raise HTTPException(status_code=400, detail="config must include 'name' field")
        
        helper_name = helper.config['name']
        
        # Load existing helpers for this domain
        domain_helpers = _load_helper_file(helper.type)
        
        # Generate entity_id
        entity_id = _generate_entity_id(helper.type, helper_name, domain_helpers)
        
        # Remove 'name' from config as it's used as the key
        config_without_name = {k: v for k, v in helper.config.items() if k != 'name'}
        config_without_name['name'] = helper_name  # Add it back as a value
        
        # Add helper to domain data
        domain_helpers[entity_id] = config_without_name
        
        # Save domain file
        _save_helper_file(helper.type, domain_helpers)
        
        # Ensure domain is included in configuration.yaml
        _ensure_domain_in_config(helper.type)
        
        # Reload the specific helper domain
        ws_client = await get_ws_client()
        await ws_client.call_service(helper.type, 'reload', {})
        logger.info(f"Reloaded {helper.type} integration")
        
        full_entity_id = f"{helper.type}.{entity_id}"
        
        # Commit changes (only if auto mode is enabled)
        if git_manager.git_versioning_auto:
            commit_msg = helper.commit_message or f"Create helper: {full_entity_id} - {helper_name}"
            await git_manager.commit_changes(
                commit_msg,
                skip_if_processing=True
            )
        
        logger.info(f"Created helper: {full_entity_id} - {helper_name}")
        
        return Response(
            success=True,
            message=f"Helper created: {full_entity_id} - {helper_name}",
            data={"entity_id": full_entity_id, "name": helper_name, "config": config_without_name}
        )
    except Exception as e:
        logger.error(f"Failed to create helper: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{entity_id}")
async def delete_helper(entity_id: str, commit_message: Optional[str] = Query(None, description="Custom commit message for Git backup")):
    """
    Delete input helper from YAML configuration or config entry
    
    **Method:** 
    1. First tries to remove from YAML file (if exists)
    2. Then tries to delete via config entry API (if created via UI/API)
    
    Example:
    - `/api/helpers/delete/input_boolean.my_switch`
    """
    try:
        # Parse entity_id
        if '.' not in entity_id:
            raise HTTPException(status_code=400, detail="Invalid entity_id format. Expected: domain.entity_id")
        
        domain, helper_id = entity_id.split('.', 1)
        
        # Validate domain
        valid_types = ['input_boolean', 'input_text', 'input_number', 'input_datetime', 'input_select', 'group', 'utility_meter']
        if domain not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid helper domain. Must be one of: {', '.join(valid_types)}")
        
        deleted_via_yaml = False
        deleted_via_config_entry = False
        
        # Try to delete from YAML first
        try:
            domain_helpers = _load_helper_file(domain)
            if helper_id in domain_helpers:
                # Remove helper from YAML
                del domain_helpers[helper_id]
                _save_helper_file(domain, domain_helpers)
                
                # Reload the specific helper domain
                ws_client = await get_ws_client()
                await ws_client.call_service(domain, 'reload', {})
                logger.info(f"✅ Removed {entity_id} from YAML and reloaded {domain} integration")
                deleted_via_yaml = True
            else:
                logger.debug(f"Helper {entity_id} not found in YAML file (may be storage helper or already removed)")
        except Exception as e:
            logger.debug(f"Could not check/delete from YAML for {entity_id}: {e}")
        
        # Try to delete via config entry API (for helpers created via UI/API)
        # Note: Helpers created via config entry need to be deleted through Home Assistant UI
        # or by finding and deleting the config entry. This is a fallback attempt.
        try:
            # Check if helper exists as entity (means it's a config entry helper)
            try:
                state = await ha_client.get_state(entity_id, suppress_404_logging=True)
                if state:
                    # Helper exists - try to find and delete its config entry
                    ws_client = await get_ws_client()
                    
                    # Get all config entries
                    config_entries_result = await ws_client._send_message({
                        'type': 'config/config_entries/list'
                    })
                    
                    # Parse result
                    if isinstance(config_entries_result, dict):
                        if 'result' in config_entries_result:
                            entries = config_entries_result['result']
                        else:
                            entries = []
                    elif isinstance(config_entries_result, list):
                        entries = config_entries_result
                    else:
                        entries = []
                    
                    # Find matching config entry by checking entity_id in options or title
                    logger.debug(f"Searching for config entry for {entity_id} (domain: {domain}, helper_id: {helper_id})")
                    logger.debug(f"Found {len([e for e in entries if e.get('domain') == domain])} config entries for domain {domain}")
                    
                    for entry in entries:
                        if entry.get('domain') == domain:
                            entry_id = entry.get('entry_id')
                            entry_title = entry.get('title', '')
                            entry_options = entry.get('options', {})
                            
                            # Try multiple matching strategies:
                            # 1. Match by title (common for UI-created helpers)
                            # 2. Match by entity_id in options
                            # 3. Match by name in options
                            # 4. Match by checking if helper_id appears in title (case-insensitive)
                            matches = False
                            
                            # Strategy 1: Exact title match or helper_id in title
                            if entry_title and (helper_id.lower() in entry_title.lower() or entry_title.lower() in helper_id.lower()):
                                matches = True
                                logger.debug(f"Match found by title: '{entry_title}' for {entity_id}")
                            
                            # Strategy 2: Check options for entity_id or name
                            if not matches and entry_options:
                                options_str = str(entry_options).lower()
                                if helper_id.lower() in options_str or entity_id.lower() in options_str:
                                    matches = True
                                    logger.debug(f"Match found by options: {entry_options} for {entity_id}")
                            
                            # Strategy 3: For input_text, try matching by getting the actual entity and comparing
                            if not matches and entry_id:
                                # Try to get config entry details to see if it matches
                                try:
                                    entry_details = await ws_client._send_message({
                                        'type': 'config/config_entries/get',
                                        'entry_id': entry_id
                                    })
                                    if isinstance(entry_details, dict) and 'result' in entry_details:
                                        entry_data = entry_details['result']
                                        # Check if the entry's data matches our helper
                                        entry_data_str = str(entry_data).lower()
                                        if helper_id.lower() in entry_data_str or entity_id.lower() in entry_data_str:
                                            matches = True
                                            logger.debug(f"Match found by entry details for {entity_id}")
                                except Exception as e:
                                    logger.debug(f"Could not get entry details for {entry_id}: {e}")
                            
                            if matches and entry_id:
                                logger.info(f"Attempting to delete config entry {entry_id} (title: '{entry_title}') for helper {entity_id}")
                                # Delete config entry
                                delete_result = await ws_client._send_message({
                                    'type': 'config/config_entries/delete',
                                    'entry_id': entry_id
                                })
                                
                                logger.debug(f"Delete result for {entry_id}: {delete_result}")
                                
                                # Check if deletion was successful
                                if isinstance(delete_result, dict) and delete_result.get('success', False):
                                    deleted_via_config_entry = True
                                    logger.info(f"✅ Deleted config entry {entry_id} for helper {entity_id}")
                                    break
                                elif delete_result is None or (isinstance(delete_result, dict) and 'error' not in delete_result):
                                    # Some APIs return None on success
                                    deleted_via_config_entry = True
                                    logger.info(f"✅ Deleted config entry {entry_id} for helper {entity_id} (result: {delete_result})")
                                    break
                                elif isinstance(delete_result, dict) and 'error' in delete_result:
                                    logger.warning(f"Failed to delete config entry {entry_id}: {delete_result.get('error')}")
            except Exception as e:
                logger.debug(f"Helper {entity_id} does not exist as entity: {e}")
        except Exception as e:
            logger.debug(f"Could not delete via config entry (helper may not exist or already deleted): {e}")
        
        # Try to delete via entity registry (for all helpers that still exist)
        # This works for storage helpers, and may work for restored entities even after YAML deletion
        # Always try this if helper still exists, even if we deleted from YAML
        # (restored entities may persist until restart, but we can try to remove from registry)
        try:
            # Check if entity exists (404 is expected if already deleted from YAML)
            try:
                state = await ha_client.get_state(entity_id, suppress_404_logging=True)
            except Exception as state_error:
                # 404 is expected when entity doesn't exist (already deleted or never existed)
                error_str = str(state_error)
                if "404" in error_str or "Entity not found" in error_str:
                    logger.debug(f"Entity {entity_id} not found (expected if already deleted): {error_str}")
                    state = None
                else:
                    # Re-raise unexpected errors
                    raise
            
            if state:
                ws_client = await get_ws_client()
                
                # Get entity registry entry to check if it's YAML-managed
                registry_result = await ws_client._send_message({
                    'type': 'config/entity_registry/get',
                    'entity_id': entity_id
                })
                
                logger.info(f"Entity registry get result for {entity_id}: {registry_result}")
                
                # Parse registry result - can be wrapped in {'result': ...} or direct dict
                if isinstance(registry_result, dict):
                    if 'result' in registry_result:
                        registry_entry = registry_result['result']
                    else:
                        # Direct result (already the entry data)
                        registry_entry = registry_result
                    
                    logger.info(f"Registry entry for {entity_id}: {registry_entry}")
                    
                    if registry_entry:
                        # Check if helper is YAML-managed
                        # YAML-managed entities have config_entry_id = None
                        config_entry_id = registry_entry.get('config_entry_id')
                        is_yaml_managed = not config_entry_id
                        
                        # Try to delete from entity registry via WebSocket
                        # This works for storage helpers, and may work temporarily for YAML-managed
                        # (but YAML-managed will restore on restart if still in YAML)
                        logger.info(f"Attempting to delete {entity_id} via WebSocket entity registry (YAML-managed: {is_yaml_managed})")
                        
                        delete_registry_result = await ws_client._send_message({
                            'type': 'config/entity_registry/remove',
                            'entity_id': entity_id
                        })
                        
                        logger.info(f"Entity registry remove result for {entity_id}: {delete_registry_result}")
                        
                        if isinstance(delete_registry_result, dict) and delete_registry_result.get('success', False):
                            deleted_via_config_entry = True
                            if is_yaml_managed:
                                logger.warning(f"⚠️ Deleted YAML-managed helper {entity_id} via entity registry. It may restore on restart if still in YAML files.")
                            else:
                                logger.info(f"✅ Deleted storage helper {entity_id} via entity registry")
                        elif delete_registry_result is None:
                            # Some HA versions return None on success
                            deleted_via_config_entry = True
                            if is_yaml_managed:
                                logger.warning(f"⚠️ Deleted YAML-managed helper {entity_id} via entity registry (result: None). It may restore on restart if still in YAML files.")
                            else:
                                logger.info(f"✅ Deleted storage helper {entity_id} via entity registry (result: None)")
                        elif isinstance(delete_registry_result, dict):
                            error_msg = delete_registry_result.get('error', {}).get('message', str(delete_registry_result))
                            logger.warning(f"Entity registry remove returned error: {error_msg}")
                            
                            # If it's YAML-managed and we got an error, provide helpful message
                            if is_yaml_managed and state.get('attributes', {}).get('restored', False):
                                logger.warning(f"Helper {entity_id} is YAML-managed. If deletion failed, remove it from YAML files and restart HA.")
                    else:
                        logger.warning(f"No registry entry found for {entity_id} (result was None or empty)")
                else:
                    logger.warning(f"Unexpected registry result format for {entity_id}: {registry_result}")
        except HTTPException:
            raise
        except Exception as e:
            # Don't log traceback for expected 404 errors
            error_str = str(e)
            if "404" in error_str or "Entity not found" in error_str:
                logger.debug(f"Could not delete via entity registry (entity not found, expected): {error_str}")
            else:
                logger.warning(f"Could not delete via entity registry: {e}", exc_info=True)
        
        # If neither method worked, check if helper actually exists
        if not deleted_via_yaml and not deleted_via_config_entry:
            # Check if helper exists in HA
            helper_exists = False
            try:
                state = await ha_client.get_state(entity_id, suppress_404_logging=True)
                if state:
                    helper_exists = True
            except:
                pass
            
            if helper_exists:
                # Helper exists but we couldn't delete it - provide helpful error message
                logger.warning(f"Helper {entity_id} exists but could not be deleted automatically. Tried YAML and config entry methods.")
                raise HTTPException(
                    status_code=404, 
                    detail=f"Helper {entity_id} exists but could not be deleted automatically. It may have been created via UI with a different configuration. Please delete manually via Settings → Helpers → {entity_id.split('.')[1].replace('_', ' ').title()} or try restarting Home Assistant."
                )
            else:
                # Helper doesn't exist - return 404
                if not deleted_via_yaml:
                    raise HTTPException(status_code=404, detail=f"Helper {entity_id} not found in {HELPER_FILES[domain]} and does not exist as an entity")
        
        # Commit changes if YAML was modified
        if deleted_via_yaml and git_manager.git_versioning_auto:
            commit_msg = commit_message or f"Delete helper: {entity_id}"
            await git_manager.commit_changes(
                commit_msg,
                skip_if_processing=True
            )
        
        method_used = []
        if deleted_via_yaml:
            method_used.append("YAML")
        if deleted_via_config_entry:
            method_used.append("config entry")
        
        logger.info(f"Deleted helper: {entity_id} via {', '.join(method_used)}")
        
        return Response(
            success=True,
            message=f"Helper deleted: {entity_id} (via {', '.join(method_used)})",
            data={"entity_id": entity_id, "deleted_via_yaml": deleted_via_yaml, "deleted_via_config_entry": deleted_via_config_entry}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete helper: {e}")
        raise HTTPException(status_code=500, detail=str(e))

