"""Automations API endpoints"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import yaml
import logging
from pathlib import Path
from datetime import datetime

from app.models.schemas import AutomationData, Response
from app.services.file_manager import file_manager
from app.services.ha_client import ha_client
from app.services.git_manager import git_manager
from app.services.ha_websocket import get_ws_client

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')

@router.get("/list")
async def list_automations(ids_only: bool = Query(False, description="If true, return only automation IDs without full configurations")):
    """
    List all automations from Home Assistant (via API)
    
    **Important:** This endpoint now uses Home Assistant's API to return ALL automations
    that HA has loaded, regardless of source:
    - From automations.yaml
    - From packages/*.yaml files
    - Created via UI (stored in .storage)
    
    This ensures you see all 159 automations, not just the 4 in automations.yaml.
    
    **Parameters:**
    - `ids_only` (optional): If `true`, returns only list of automation IDs. If `false` (default), returns full automation configurations.
    
    **Example response (ids_only=false):**
    ```json
    {
      "success": true,
      "count": 159,
      "automations": [
        {"id": "my_automation", "alias": "...", "trigger": [...]},
        {"id": "another", ...}
      ]
    }
    ```
    
    **Example response (ids_only=true):**
    ```json
    {
      "success": true,
      "count": 159,
      "automation_ids": ["my_automation", "another", ...]
    }
    ```
    """
    try:
        # Get all automations from HA API (includes all sources: files, packages, UI)
        automations = await ha_client.list_automations()
        
        if ids_only:
            # Extract IDs from automations list
            automation_ids = [a.get('id') for a in automations if a.get('id')]
            return {
                "success": True,
                "count": len(automation_ids),
                "automation_ids": automation_ids
            }
        
        return {
            "success": True,
            "count": len(automations),
            "automations": automations
        }
    except Exception as e:
        logger.error(f"Failed to list automations via API: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get/{automation_id}")
async def get_automation_config(automation_id: str):
    """
    Get configuration for a single automation from Home Assistant (via API).
    
    **Important:** This endpoint now uses Home Assistant's API, so it works for automations
    from any source (automations.yaml, packages/*.yaml, or UI-created).
    
    **Example response:**
    ```json
    {
      "success": true,
      "automation_id": "my_automation",
      "config": {
        "id": "my_automation",
        "alias": "My Automation",
        "trigger": [...],
        "condition": [...],
        "action": [...],
        "mode": "single"
      }
    }
    ```
    """
    try:
        # Get automation from HA API (works for all sources)
        config = await ha_client.get_automation(automation_id)
        
        return {
            "success": True,
            "automation_id": automation_id,
            "config": config,
        }
    except Exception as e:
        error_msg = str(e)
        if 'not found' in error_msg.lower() or '404' in error_msg:
            raise HTTPException(status_code=404, detail=f"Automation not found: {automation_id}")
        logger.error(f"Failed to get automation {automation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create", response_model=Response)
async def create_automation(automation: AutomationData):
    """
    Create new automation via Home Assistant API
    
    **Important:** This endpoint now uses Home Assistant's API instead of writing to automations.yaml.
    This means automations can be created regardless of your file structure (packages, UI, etc.).
    
    After creation, the automation state is exported to Git for versioning.
    
    **Example request:**
    ```json
    {
      "id": "my_automation",
      "alias": "My Automation",
      "description": "Test automation",
      "trigger": [
        {
          "platform": "state",
          "entity_id": "sensor.temperature",
          "to": "20"
        }
      ],
      "condition": [],
      "action": [
        {
          "service": "light.turn_on",
          "target": {"entity_id": "light.living_room"}
        }
      ],
      "mode": "single"
    }
    ```
    """
    try:
        # Prepare automation config (exclude commit_message as it's not part of automation config)
        automation_config = automation.model_dump(exclude_none=True)
        automation_config.pop('commit_message', None)
        
        if not automation_config.get('id'):
            raise ValueError("Automation must have an 'id' field")
        
        automation_id = automation_config['id']
        
        # Check if automation already exists
        try:
            existing = await ha_client.get_automation(automation_id)
            raise ValueError(f"Automation with ID '{automation_id}' already exists")
        except Exception as check_error:
            # If automation not found, that's fine - we can create it
            if 'not found' not in str(check_error).lower() and '404' not in str(check_error):
                raise
        
        # Create automation via HA API
        created_config = await ha_client.create_automation(automation_config)
        
        # Export current state to Git for versioning
        commit_msg = automation.commit_message or f"Create automation: {automation.alias or automation_id}"
        await _export_automations_to_git(commit_msg)
        
        logger.info(f"Created automation via API: {automation_id}")
        
        return Response(
            success=True,
            message=f"Automation created: {automation.alias or automation_id}",
            data=created_config
        )
    except Exception as e:
        logger.error(f"Failed to create automation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update/{automation_id}", response_model=Response)
async def update_automation(automation_id: str, automation: AutomationData, commit_message: Optional[str] = Query(None, description="Custom commit message for Git backup")):
    """
    Update existing automation via Home Assistant REST API
    
    **Important:** This endpoint uses Home Assistant's REST API (POST /api/config/automation/config/{entity_id}).
    Home Assistant automatically updates the automation in its original location.
    
    After update, the automation state is exported to Git for versioning.
    
    **Example request:**
    ```json
    {
      "id": "my_automation",
      "alias": "Updated Automation",
      "trigger": [...],
      "action": [...]
    }
    ```
    """
    try:
        # Prepare automation config
        automation_config = automation.model_dump(exclude_none=True)
        automation_config.pop('commit_message', None)
        
        # Ensure ID matches
        automation_config['id'] = automation_id
        
        # Update automation via HA REST API
        updated_config = await ha_client.update_automation(automation_id, automation_config)
        
        # Export current state to Git for versioning
        commit_msg = commit_message or automation.commit_message or f"Update automation: {automation.alias or automation_id}"
        await _export_automations_to_git(commit_msg)
        
        logger.info(f"Updated automation via API: {automation_id}")
        
        return Response(
            success=True,
            message=f"Automation updated: {automation.alias or automation_id}",
            data=updated_config
        )
    except Exception as e:
        error_msg = str(e)
        if 'not found' in error_msg.lower() or '404' in error_msg:
            raise HTTPException(status_code=404, detail=f"Automation not found: {automation_id}")
        logger.error(f"Failed to update automation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{automation_id}")
async def delete_automation(automation_id: str, commit_message: Optional[str] = Query(None, description="Custom commit message for Git backup")):
    """
    Delete automation by ID via Home Assistant API
    
    **Important:** This endpoint now uses Home Assistant's API instead of editing automations.yaml.
    This works for automations from any source (files, packages, UI).
    
    After deletion, the automation state is exported to Git for versioning.
    
    Example:
    - `/api/automations/delete/my_automation`
    """
    try:
        # Delete automation via HA API
        await ha_client.delete_automation(automation_id)
        
        # Try to remove entity from Entity Registry (if it exists)
        # This cleans up "orphaned" registry entries that may remain after deletion
        entity_id = f"automation.{automation_id}"
        try:
            ws_client = await get_ws_client()
            await ws_client.remove_entity_registry_entry(entity_id)
            logger.info(f"Removed automation entity from registry: {entity_id}")
        except Exception as e:
            # Entity may already be removed or not exist - this is fine
            logger.debug(f"Could not remove entity from registry (may not exist): {entity_id}, {e}")
        
        # Export current state to Git for versioning
        commit_msg = commit_message or f"Delete automation: {automation_id}"
        await _export_automations_to_git(commit_msg)
        
        logger.info(f"Deleted automation via API: {automation_id}")
        
        return Response(success=True, message=f"Automation deleted: {automation_id}")
    except Exception as e:
        error_msg = str(e)
        if 'not found' in error_msg.lower() or '404' in error_msg:
            raise HTTPException(status_code=404, detail=f"Automation not found: {automation_id}")
        logger.error(f"Failed to delete automation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _export_automations_to_git(commit_message: str):
    """
    Export all automations from HA API to Git shadow repository.
    
    This creates/updates files in export/automations/<id>.yaml in the shadow repo,
    allowing Git to track the actual state of automations in HA, regardless of
    where they're stored (automations.yaml, packages/*, UI, etc.).
    
    Args:
        commit_message: Git commit message for this export
    """
    try:
        if not git_manager.git_versioning_auto or git_manager.processing_request:
            # Git versioning disabled or during request processing, skip export
            return
        
        if not git_manager.repo:
            logger.warning("Git repo not initialized, skipping automation export")
            return
        
        # Get all automations from HA API
        automations = await ha_client.list_automations()
        
        # Shadow repo path
        shadow_root = git_manager.shadow_root
        export_dir = shadow_root / 'export' / 'automations'
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Export each automation to its own file
        # Also try to determine original location for better rollback support
        exported_count = 0
        for automation in automations:
            automation_id = automation.get('id')
            if not automation_id:
                logger.warning(f"Skipping automation without ID: {automation}")
                continue
            
            # Try to find original location (for rollback context)
            # Note: This is informational only - REST API will handle actual storage location
            automation_with_meta = dict(automation)
            try:
                # Try to determine if automation is in packages or storage
                from app.services.file_manager import file_manager
                import json
                from pathlib import Path
                
                # Check packages
                packages_dir = file_manager.config_path / 'packages'
                if packages_dir.exists():
                    for yaml_file in packages_dir.rglob('*.yaml'):
                        try:
                            content = yaml_file.read_text(encoding='utf-8')
                            data = yaml.safe_load(content)
                            if isinstance(data, dict) and 'automation' in data:
                                pkg_automations = data['automation']
                                found = False
                                if isinstance(pkg_automations, list):
                                    found = any(auto.get('id') == automation_id for auto in pkg_automations)
                                elif isinstance(pkg_automations, dict):
                                    found = automation_id in pkg_automations
                                
                                if found:
                                    rel_path = yaml_file.relative_to(file_manager.config_path)
                                    automation_with_meta['_export_metadata'] = {
                                        'original_location': 'packages',
                                        'original_file': str(rel_path)
                                    }
                                    break
                        except Exception:
                            continue
                
                # Check storage if not found in packages
                if '_export_metadata' not in automation_with_meta:
                    storage_file = file_manager.config_path / '.storage' / 'automation.storage'
                    if storage_file.exists():
                        content = storage_file.read_text(encoding='utf-8')
                        storage_data = json.loads(content)
                        if 'data' in storage_data and 'automations' in storage_data['data']:
                            if any(auto.get('id') == automation_id for auto in storage_data['data']['automations']):
                                automation_with_meta['_export_metadata'] = {
                                    'original_location': 'storage',
                                    'original_file': '.storage/automation.storage'
                                }
            except Exception:
                # If we can't determine location, that's fine - REST API will handle it
                pass
            
            # Write automation to export/automations/<id>.yaml
            automation_file = export_dir / f"{automation_id}.yaml"
            automation_yaml = yaml.dump(automation_with_meta, allow_unicode=True, default_flow_style=False, sort_keys=False)
            automation_file.write_text(automation_yaml, encoding='utf-8')
            exported_count += 1
        
        # Also create an index file with all automation IDs for easy reference
        index_file = export_dir / 'index.yaml'
        index_data = {
            'total_count': len(automations),
            'automation_ids': [a.get('id') for a in automations if a.get('id')],
            'exported_at': datetime.now().isoformat()
        }
        index_yaml = yaml.dump(index_data, allow_unicode=True, default_flow_style=False)
        index_file.write_text(index_yaml, encoding='utf-8')
        
        # Add to Git and commit
        try:
            git_manager.repo.git.add(str(export_dir))
            if git_manager.git_versioning_auto and not git_manager.processing_request:
                git_manager.repo.index.commit(commit_message)
                logger.info(f"Exported {exported_count} automations to Git: {commit_message}")
        except Exception as git_error:
            logger.warning(f"Failed to commit automation export to Git: {git_error}")
            
    except Exception as e:
        logger.error(f"Failed to export automations to Git: {e}")
        # Don't fail the main operation if Git export fails


async def _apply_automations_from_git_export(export_dir: Path) -> int:
    """
    Apply automations from Git export directory via HA API.
    
    This function reads all automation YAML files from export/automations/*.yaml
    and applies them to Home Assistant via API. Used for rollback operations.
    
    Args:
        export_dir: Path to export/automations directory in shadow repo
        
    Returns:
        Number of automations successfully applied
    """
    try:
        applied_count = 0
        
        # Get all automation YAML files
        automation_files = list(export_dir.glob('*.yaml'))
        # Exclude index.yaml
        automation_files = [f for f in automation_files if f.name != 'index.yaml']
        
        for automation_file in automation_files:
            try:
                # Read automation config from file
                content = automation_file.read_text(encoding='utf-8')
                automation_config = yaml.safe_load(content)
                
                if not automation_config or not isinstance(automation_config, dict):
                    logger.warning(f"Skipping invalid automation file: {automation_file.name}")
                    continue
                
                automation_id = automation_config.get('id') or automation_file.stem
                
                # Remove export metadata (if present) before applying
                # This metadata is only for informational purposes
                export_metadata = automation_config.pop('_export_metadata', None)
                
                # Check if automation exists
                try:
                    existing = await ha_client.get_automation(automation_id)
                    # Update existing automation via REST API
                    # REST API will preserve original location if automation still exists
                    await ha_client.update_automation(automation_id, automation_config)
                    logger.debug(f"Updated automation from Git export: {automation_id}" + 
                               (f" (was in {export_metadata.get('original_file')})" if export_metadata else ""))
                except Exception:
                    # Automation doesn't exist, create it via REST API
                    # Note: New automations are created in automations.yaml by default
                    # If original location was packages/*, user may need to move it manually
                    await ha_client.create_automation(automation_config)
                    if export_metadata and export_metadata.get('original_location') != 'automations.yaml':
                        logger.info(f"Created automation from Git export: {automation_id} "
                                  f"(original location was {export_metadata.get('original_file')}, "
                                  f"but REST API created it in automations.yaml - may need manual move)")
                    else:
                        logger.debug(f"Created automation from Git export: {automation_id}")
                
                applied_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to apply automation from {automation_file.name}: {e}")
                continue
        
        if applied_count > 0:
            logger.info(f"Applied {applied_count} automations from Git export via API")
        
        return applied_count
        
    except Exception as e:
        logger.error(f"Failed to apply automations from Git export: {e}")
        return 0

