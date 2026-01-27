"""Scripts API endpoints"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import yaml
import logging
from pathlib import Path
from datetime import datetime

from app.models.schemas import ScriptData, Response
from app.services.file_manager import file_manager
from app.services.ha_client import ha_client
from app.services.git_manager import git_manager
from app.services.ha_websocket import get_ws_client

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')

@router.get("/list")
async def list_scripts(ids_only: bool = Query(False, description="If true, return only script IDs without full configurations")):
    """
    List all scripts from Home Assistant (via API)
    
    **Important:** This endpoint now uses Home Assistant's API to return ALL scripts
    that HA has loaded, regardless of source:
    - From scripts.yaml
    - From packages/*.yaml files
    - Created via UI (stored in .storage)
    
    **Parameters:**
    - `ids_only` (optional): If `true`, returns only list of script IDs. If `false` (default), returns full script configurations.
    
    **Example response (ids_only=false):**
    ```json
    {
      "success": true,
      "count": 3,
      "scripts": {
        "my_script": {"alias": "...", "sequence": [...]},
        "another_script": {...}
      }
    }
    ```
    
    **Example response (ids_only=true):**
    ```json
    {
      "success": true,
      "count": 3,
      "script_ids": ["my_script", "another_script", "third_script"]
    }
    ```
    """
    try:
        # Get all scripts from HA API (includes all sources: files, packages, UI)
        scripts = await ha_client.list_scripts()
        
        if ids_only:
            return {
                "success": True,
                "count": len(scripts),
                "script_ids": list(scripts.keys())
            }
        
        return {
            "success": True,
            "count": len(scripts),
            "scripts": scripts
        }
    except Exception as e:
        logger.error(f"Failed to list scripts via API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get/{script_id}")
async def get_script_config(script_id: str):
    """
    Get configuration for a single script from Home Assistant (via API).
    
    **Important:** This endpoint now uses Home Assistant's API, so it works for scripts
    from any source (scripts.yaml, packages/*.yaml, or UI-created).
    
    **Example response:**
    ```json
    {
      "success": true,
      "script_id": "my_script",
      "config": {
        "alias": "My Script",
        "sequence": [...]
      }
    }
    ```
    """
    try:
        # Get script from HA API (works for all sources)
        config = await ha_client.get_script(script_id)
        
        return {
            "success": True,
            "script_id": script_id,
            "config": config
        }
    except Exception as e:
        error_msg = str(e)
        if 'not found' in error_msg.lower() or '404' in error_msg:
            raise HTTPException(status_code=404, detail=f"Script not found: {script_id}")
        logger.error(f"Failed to get script {script_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create", response_model=Response)
async def create_script(config: dict):
    """
    Create new script via Home Assistant API
    
    **Important:** This endpoint now uses Home Assistant's API instead of writing to scripts.yaml.
    This means scripts can be created regardless of your file structure (packages, UI, etc.).
    
    After creation, the script state is exported to Git for versioning.
    
    **Example:**
    ```json
    {
      "test_script": {
        "alias": "Test Script",
        "sequence": [
          {"service": "light.turn_on", "target": {"entity_id": "light.living_room"}}
        ],
        "mode": "single",
        "icon": "mdi:play"
      }
    }
    ```
    
    Or as single script:
    ```json
    {
      "entity_id": "my_script",
      "alias": "My Script",
      "sequence": [...],
      "mode": "single"
    }
    ```
    """
    try:
        # Extract commit_message if present (may be added by MCP client)
        commit_msg = config.pop('commit_message', None)
        
        # Handle two formats:
        # Format 1: {"script_id": {"alias": ..., "sequence": ...}}
        # Format 2: {"entity_id": "...", "alias": ..., "sequence": ...}
        
        if 'entity_id' in config:
            # Format 2: Single script with entity_id field
            script_id = config.pop('entity_id')
            script_data = config
        else:
            # Format 1: Dictionary with script_id as key
            if len(config) != 1:
                raise ValueError("Config must contain exactly one script")
            script_id = list(config.keys())[0]
            script_data = config[script_id]
        
        # Check if script already exists
        try:
            existing = await ha_client.get_script(script_id)
            raise ValueError(f"Script '{script_id}' already exists")
        except Exception as check_error:
            # If script not found, that's fine - we can create it
            if 'not found' not in str(check_error).lower() and '404' not in str(check_error):
                raise
        
        # Create script via HA API
        await ha_client.create_script(script_id, script_data)
        
        # Export current state to Git for versioning
        script_alias = script_data.get('alias', script_id)
        commit_message = commit_msg or f"Create script: {script_alias}"
        await _export_scripts_to_git(commit_message)
        
        logger.info(f"Created script via API: {script_id}")
        
        return Response(success=True, message=f"Script created: {script_id}")
    except Exception as e:
        logger.error(f"Failed to create script: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update/{script_id}", response_model=Response)
async def update_script(script_id: str, config: dict, commit_message: Optional[str] = Query(None, description="Custom commit message for Git backup")):
    """
    Update existing script via Home Assistant REST API
    
    **Important:** This endpoint uses Home Assistant's REST API (POST /api/config/script/config/{script_id}).
    Home Assistant automatically updates the script in its original location.
    
    After update, the script state is exported to Git for versioning.
    
    **Example request:**
    ```json
    {
      "alias": "Updated Script",
      "sequence": [
        {"service": "light.turn_on", "target": {"entity_id": "light.living_room"}}
      ],
      "mode": "single"
    }
    ```
    """
    try:
        # Extract commit_message if present
        commit_msg = config.pop('commit_message', None) or commit_message
        
        # Update script via HA REST API
        await ha_client.update_script(script_id, config)
        
        # Export current state to Git for versioning
        script_alias = config.get('alias', script_id)
        commit_msg = commit_msg or f"Update script: {script_alias}"
        await _export_scripts_to_git(commit_msg)
        
        logger.info(f"Updated script via API: {script_id}")
        
        return Response(success=True, message=f"Script updated: {script_id}")
    except Exception as e:
        error_msg = str(e)
        if 'not found' in error_msg.lower() or '404' in error_msg:
            raise HTTPException(status_code=404, detail=f"Script not found: {script_id}")
        logger.error(f"Failed to update script: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{script_id}")
async def delete_script(script_id: str, commit_message: Optional[str] = Query(None, description="Custom commit message for Git backup")):
    """
    Delete script by ID via Home Assistant API
    
    **Important:** This endpoint now uses Home Assistant's API instead of editing scripts.yaml.
    This works for scripts from any source (files, packages, UI).
    
    After deletion, the script state is exported to Git for versioning.
    """
    try:
        # Delete script via HA API
        await ha_client.delete_script(script_id)
        
        # Try to remove entity from Entity Registry (if it exists)
        # This cleans up "orphaned" registry entries that may remain after deletion
        entity_id = f"script.{script_id}"
        try:
            ws_client = await get_ws_client()
            await ws_client.remove_entity_registry_entry(entity_id)
            logger.info(f"Removed script entity from registry: {entity_id}")
        except Exception as e:
            # Entity may already be removed or not exist - this is fine
            logger.debug(f"Could not remove entity from registry (may not exist): {entity_id}, {e}")
        
        # Export current state to Git for versioning
        commit_msg = commit_message or f"Delete script: {script_id}"
        await _export_scripts_to_git(commit_msg)
        
        logger.info(f"Deleted script via API: {script_id}")
        
        return Response(success=True, message=f"Script deleted: {script_id}")
    except Exception as e:
        error_msg = str(e)
        if 'not found' in error_msg.lower() or '404' in error_msg:
            raise HTTPException(status_code=404, detail=f"Script not found: {script_id}")
        logger.error(f"Failed to delete script: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _export_scripts_to_git(commit_message: str):
    """
    Export all scripts from HA API to Git shadow repository.
    
    This creates/updates files in export/scripts/<id>.yaml in the shadow repo,
    allowing Git to track the actual state of scripts in HA, regardless of
    where they're stored (scripts.yaml, packages/*, UI, etc.).
    
    Args:
        commit_message: Git commit message for this export
    """
    try:
        if not git_manager.git_versioning_auto or git_manager.processing_request:
            # Git versioning disabled or during request processing, skip export
            return
        
        if not git_manager.repo:
            logger.warning("Git repo not initialized, skipping script export")
            return
        
        # Get all scripts from HA API
        scripts = await ha_client.list_scripts()
        
        # Shadow repo path
        shadow_root = git_manager.shadow_root
        export_dir = shadow_root / 'export' / 'scripts'
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache packages and storage data ONCE to avoid reading files multiple times
        from app.services.file_manager import file_manager
        import json
        from pathlib import Path
        
        # Build cache: script_id -> location info
        location_cache = {}
        
        try:
            # Read all packages files ONCE
            packages_dir = file_manager.config_path / 'packages'
            if packages_dir.exists():
                for yaml_file in packages_dir.rglob('*.yaml'):
                    try:
                        content = yaml_file.read_text(encoding='utf-8')
                        data = yaml.safe_load(content)
                        if isinstance(data, dict) and 'script' in data:
                            pkg_scripts = data['script']
                            rel_path = yaml_file.relative_to(file_manager.config_path)
                            
                            if isinstance(pkg_scripts, dict):
                                for script_id in pkg_scripts.keys():
                                    location_cache[script_id] = {
                                        'original_location': 'packages',
                                        'original_file': str(rel_path)
                                    }
                    except Exception:
                        continue
            
            # Read storage file ONCE
            storage_file = file_manager.config_path / '.storage' / 'script.storage'
            if storage_file.exists():
                try:
                    content = storage_file.read_text(encoding='utf-8')
                    storage_data = json.loads(content)
                    if 'data' in storage_data and 'scripts' in storage_data['data']:
                        for script_id in storage_data['data']['scripts'].keys():
                            if script_id not in location_cache:
                                location_cache[script_id] = {
                                    'original_location': 'storage',
                                    'original_file': '.storage/script.storage'
                                }
                except Exception:
                    pass
        except Exception:
            # If we can't build cache, that's fine - we'll just skip metadata
            pass
        
        # Export each script to its own file (using cached location data)
        exported_count = 0
        for script_id, script_config in scripts.items():
            # Add location metadata from cache if available
            script_with_meta = dict(script_config)
            if script_id in location_cache:
                script_with_meta['_export_metadata'] = location_cache[script_id]
            
            # Write script to export/scripts/<id>.yaml
            script_file = export_dir / f"{script_id}.yaml"
            script_yaml = yaml.dump(script_with_meta, allow_unicode=True, default_flow_style=False, sort_keys=False)
            script_file.write_text(script_yaml, encoding='utf-8')
            exported_count += 1
        
        # Also create an index file with all script IDs for easy reference
        index_file = export_dir / 'index.yaml'
        index_data = {
            'total_count': len(scripts),
            'script_ids': list(scripts.keys()),
            'exported_at': datetime.now().isoformat()
        }
        index_yaml = yaml.dump(index_data, allow_unicode=True, default_flow_style=False)
        index_file.write_text(index_yaml, encoding='utf-8')
        
        # Add to Git and commit
        try:
            git_manager.repo.git.add(str(export_dir))
            if git_manager.git_versioning_auto and not git_manager.processing_request:
                git_manager.repo.index.commit(commit_message)
                logger.info(f"Exported {exported_count} scripts to Git: {commit_message}")
        except Exception as git_error:
            logger.warning(f"Failed to commit script export to Git: {git_error}")
            
    except Exception as e:
        logger.error(f"Failed to export scripts to Git: {e}")
        # Don't fail the main operation if Git export fails


async def _apply_scripts_from_git_export(export_dir: Path) -> int:
    """
    Apply scripts from Git export directory via HA API.
    
    This function reads all script YAML files from export/scripts/*.yaml
    and applies them to Home Assistant via API. Used for rollback operations.
    
    Args:
        export_dir: Path to export/scripts directory in shadow repo
        
    Returns:
        Number of scripts successfully applied
    """
    try:
        applied_count = 0
        
        # Get all script YAML files
        script_files = list(export_dir.glob('*.yaml'))
        # Exclude index.yaml
        script_files = [f for f in script_files if f.name != 'index.yaml']
        
        for script_file in script_files:
            try:
                # Read script config from file
                content = script_file.read_text(encoding='utf-8')
                script_config = yaml.safe_load(content)
                
                if not script_config or not isinstance(script_config, dict):
                    logger.warning(f"Skipping invalid script file: {script_file.name}")
                    continue
                
                script_id = script_file.stem
                
                # Remove export metadata (if present) before applying
                # This metadata is only for informational purposes
                export_metadata = script_config.pop('_export_metadata', None)
                
                # Check if script exists
                try:
                    existing = await ha_client.get_script(script_id)
                    # Update existing script via REST API
                    # REST API will preserve original location if script still exists
                    await ha_client.update_script(script_id, script_config)
                    logger.debug(f"Updated script from Git export: {script_id}" + 
                               (f" (was in {export_metadata.get('original_file')})" if export_metadata else ""))
                except Exception:
                    # Script doesn't exist, create it via REST API
                    # Note: New scripts are created in scripts.yaml by default
                    # If original location was packages/*, user may need to move it manually
                    await ha_client.create_script(script_id, script_config)
                    if export_metadata and export_metadata.get('original_location') != 'scripts.yaml':
                        logger.info(f"Created script from Git export: {script_id} "
                                  f"(original location was {export_metadata.get('original_file')}, "
                                  f"but REST API created it in scripts.yaml - may need manual move)")
                    else:
                        logger.debug(f"Created script from Git export: {script_id}")
                
                applied_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to apply script from {script_file.name}: {e}")
                continue
        
        if applied_count > 0:
            logger.info(f"Applied {applied_count} scripts from Git export via API")
        
        return applied_count
        
    except Exception as e:
        logger.error(f"Failed to apply scripts from Git export: {e}")
        return 0

