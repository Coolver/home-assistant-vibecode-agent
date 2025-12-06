"""Automations API endpoints"""
from fastapi import APIRouter, HTTPException
import yaml
import logging

from app.models.schemas import AutomationData, Response
from app.services.file_manager import file_manager
from app.services.ha_client import ha_client
from app.services.git_manager import git_manager

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')

@router.get("/list")
async def list_automations():
    """
    List all automations
    
    Returns automations from automations.yaml
    """
    try:
        # Read automations.yaml
        content = await file_manager.read_file('automations.yaml')
        automations = yaml.safe_load(content) or []
        
        return {
            "success": True,
            "count": len(automations),
            "automations": automations
        }
    except FileNotFoundError:
        return {"success": True, "count": 0, "automations": []}
    except Exception as e:
        logger.error(f"Failed to list automations: {e}")
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
        
        # Add new automation
        new_automation = automation.model_dump(exclude_none=True)
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
async def delete_automation(automation_id: str):
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
        commit_msg = f"Delete automation: {automation_id}"
        await file_manager.write_file('automations.yaml', new_content, create_backup=True, commit_message=commit_msg)
        
        # Reload
        await ha_client.reload_component('automations')
        
        logger.info(f"Deleted automation: {automation_id}")
        
        return Response(success=True, message=f"Automation deleted and reloaded: {automation_id}")
    except Exception as e:
        logger.error(f"Failed to delete automation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

