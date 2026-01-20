"""Automations API endpoints"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import yaml
import logging

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
    List all automations from automations.yaml
    
    **Parameters:**
    - `ids_only` (optional): If `true`, returns only list of automation IDs. If `false` (default), returns full automation configurations.
    
    **Example response (ids_only=false):**
    ```json
    {
      "success": true,
      "count": 2,
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
      "count": 2,
      "automation_ids": ["my_automation", "another"]
    }
    ```
    """
    try:
        # Read automations.yaml
        content = await file_manager.read_file('automations.yaml')
        automations = yaml.safe_load(content) or []
        
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
    except FileNotFoundError:
        if ids_only:
            return {"success": True, "count": 0, "automation_ids": []}
        return {"success": True, "count": 0, "automations": []}
    except Exception as e:
        logger.error(f"Failed to list automations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get/{automation_id}")
async def get_automation_config(automation_id: str):
    """
    Get configuration for a single automation.
    
    Returns the YAML configuration object for a specific automation_id from automations.yaml.
    
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
        # Read automations.yaml
        content = await file_manager.read_file('automations.yaml')
        automations = yaml.safe_load(content) or []
        
        # Find automation by id
        for automation in automations:
            if automation.get('id') == automation_id:
                return {
                    "success": True,
                    "automation_id": automation_id,
                    "config": automation,
                }
        
        raise HTTPException(status_code=404, detail=f"Automation not found: {automation_id}")
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Automation not found: {automation_id}")
    except Exception as e:
        logger.error(f"Failed to get automation {automation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create", response_model=Response)
async def create_automation(automation: AutomationData):
    """
    Create new automation
    
    Adds automation to automations.yaml and reloads
    
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
        # Read existing automations
        try:
            content = await file_manager.read_file('automations.yaml')
            automations = yaml.safe_load(content) or []
        except FileNotFoundError:
            automations = []
        
        # Check if ID already exists
        if automation.id and any(a.get('id') == automation.id for a in automations):
            raise ValueError(f"Automation with ID '{automation.id}' already exists")
        
        # Add new automation (exclude commit_message as it's not part of automation config)
        new_automation = automation.model_dump(exclude_none=True)
        # Remove commit_message if present (it's only for Git, not part of automation config)
        new_automation.pop('commit_message', None)
        automations.append(new_automation)
        
        # Write back
        new_content = yaml.dump(automations, allow_unicode=True, default_flow_style=False, sort_keys=False)
        commit_msg = automation.commit_message or f"Create automation: {automation.alias}"
        await file_manager.write_file('automations.yaml', new_content, create_backup=True, commit_message=commit_msg)
        
        # Reload automations
        await ha_client.reload_component('automations')
        
        logger.info(f"Created automation: {automation.alias}")
        
        return Response(
            success=True,
            message=f"Automation created and reloaded: {automation.alias}",
            data=new_automation
        )
    except Exception as e:
        logger.error(f"Failed to create automation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{automation_id}")
async def delete_automation(automation_id: str, commit_message: Optional[str] = Query(None, description="Custom commit message for Git backup")):
    """
    Delete automation by ID
    
    Example:
    - `/api/automations/delete/my_automation`
    """
    try:
        # Read automations
        content = await file_manager.read_file('automations.yaml')
        automations = yaml.safe_load(content) or []
        
        # Find and remove
        original_count = len(automations)
        automations = [a for a in automations if a.get('id') != automation_id]
        
        if len(automations) == original_count:
            raise HTTPException(status_code=404, detail=f"Automation not found: {automation_id}")
        
        # Write back
        new_content = yaml.dump(automations, allow_unicode=True, default_flow_style=False, sort_keys=False)
        commit_msg = commit_message or f"Delete automation: {automation_id}"
        await file_manager.write_file('automations.yaml', new_content, create_backup=True, commit_message=commit_msg)
        
        # Reload
        await ha_client.reload_component('automations')
        
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
        
        logger.info(f"Deleted automation: {automation_id}")
        
        return Response(success=True, message=f"Automation deleted and reloaded: {automation_id}")
    except Exception as e:
        logger.error(f"Failed to delete automation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

