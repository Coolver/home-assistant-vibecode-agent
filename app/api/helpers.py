"""Helpers API endpoints"""
from fastapi import APIRouter, HTTPException
import logging

from app.models.schemas import HelperCreate, Response
from app.services.ha_client import ha_client
from app.services.ha_websocket import get_ws_client
from app.services.git_manager import git_manager

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')

@router.get("/list")
async def list_helpers():
    """
    List all input helpers
    
    Returns all entities from helper domains:
    - input_boolean
    - input_text
    - input_number
    - input_datetime
    - input_select
    
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
        
        # Filter helper entities
        helper_domains = ['input_boolean', 'input_text', 'input_number', 'input_datetime', 'input_select']
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
    Create input helper
    
    **Helper types:**
    - `input_boolean` - Toggle/switch
    - `input_text` - Text input
    - `input_number` - Number slider
    - `input_datetime` - Date/time picker
    - `input_select` - Dropdown selection
    
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
        valid_types = ['input_boolean', 'input_text', 'input_number', 'input_datetime', 'input_select']
        if helper.type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid helper type. Must be one of: {', '.join(valid_types)}")
        
        # Extract name from config (required)
        if 'name' not in helper.config:
            raise HTTPException(status_code=400, detail="config must include 'name' field")
        
        # Create helper via WebSocket (works better than REST for helpers)
        ws_client = await get_ws_client()
        result = await ws_client.call_service(
            helper.type,
            'create',
            helper.config
        )
        
        # Get entity_id from result (HA returns it in context)
        entity_id = result.get('context', {}).get('id') if isinstance(result, dict) else None
        helper_name = helper.config.get('name')
        
        # Commit changes
        if git_manager.enabled:
            await git_manager.commit_changes(f"Create helper: {helper.type} - {helper_name}")
        
        logger.info(f"Created helper: {helper.type} - {helper_name}")
        
        return Response(
            success=True,
            message=f"Helper created: {helper.type} - {helper_name}",
            data=result
        )
    except Exception as e:
        logger.error(f"Failed to create helper: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{entity_id}")
async def delete_helper(entity_id: str):
    """
    Delete input helper
    
    Example:
    - `/api/helpers/delete/input_boolean.my_switch`
    """
    try:
        # Get domain from entity_id
        domain = entity_id.split('.')[0]
        
        # Delete via WebSocket
        ws_client = await get_ws_client()
        result = await ws_client.call_service(
            domain,
            'remove',
            {"entity_id": entity_id}
        )
        
        logger.info(f"Deleted helper: {entity_id}")
        
        return Response(
            success=True,
            message=f"Helper deleted: {entity_id}",
            data=result
        )
    except Exception as e:
        logger.error(f"Failed to delete helper: {e}")
        raise HTTPException(status_code=500, detail=str(e))

