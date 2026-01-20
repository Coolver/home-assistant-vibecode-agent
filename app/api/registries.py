"""Registries API endpoints - Entity, Area, and Device Registry management"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
import logging
import yaml

from app.services.ha_websocket import get_ws_client
from app.services.file_manager import file_manager
from app.models.schemas import Response, EntityRemoveRequest, AreaRemoveRequest, DeviceRemoveRequest

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')

# ==================== Entity Registry ====================

@router.get("/entities/list")
async def list_entity_registry():
    """
    Get all entities from Entity Registry
    
    Returns complete Entity Registry with metadata:
    - entity_id, unique_id, name, area_id, device_id
    - disabled, hidden_by, config_entry_id
    - platform, original_name, etc.
    
    This provides area assignments and other metadata that /api/entities/list (states) doesn't include.
    """
    try:
        ws_client = await get_ws_client()
        entities = await ws_client.get_entity_registry_list()
        
        logger.info(f"Listed {len(entities)} entities from Entity Registry")
        return {
            "success": True,
            "count": len(entities),
            "entities": entities
        }
    except Exception as e:
        logger.error(f"Failed to list Entity Registry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list Entity Registry: {str(e)}")

@router.get("/entities/dead")
async def find_dead_entities():
    """
    Find "dead" entities in Entity Registry
    
    Compares entities in Entity Registry (automation.* and script.*) with
    automations and scripts defined in YAML files to identify entities that
    exist in registry but are missing from YAML configuration.
    
    Returns:
    - dead_automations: List of automation entities not found in automations.yaml
    - dead_scripts: List of script entities not found in scripts.yaml
    - summary: Counts and totals
    """
    try:
        ws_client = await get_ws_client()
        
        # Get all entities from registry
        all_entities = await ws_client.get_entity_registry_list()
        
        # Filter automation and script entities
        registry_automations = []
        registry_scripts = []
        
        for entity in all_entities:
            entity_id = entity.get('entity_id', '')
            platform = entity.get('platform', '')
            unique_id = entity.get('unique_id', '')
            
            if entity_id.startswith('automation.') and platform == 'automation':
                registry_automations.append({
                    'entity_id': entity_id,
                    'unique_id': unique_id,
                    'name': entity.get('name'),
                    'disabled': entity.get('disabled', False)
                })
            elif entity_id.startswith('script.') and platform == 'script':
                registry_scripts.append({
                    'entity_id': entity_id,
                    'unique_id': unique_id,
                    'name': entity.get('name'),
                    'disabled': entity.get('disabled', False)
                })
        
        # Get automations from YAML
        yaml_automation_ids = set()
        try:
            content = await file_manager.read_file('automations.yaml')
            automations = yaml.safe_load(content) or []
            if isinstance(automations, list):
                for automation in automations:
                    automation_id = automation.get('id')
                    if automation_id:
                        yaml_automation_ids.add(automation_id)
        except FileNotFoundError:
            logger.debug("automations.yaml not found, assuming no automations")
        except Exception as e:
            logger.warning(f"Failed to read automations.yaml: {e}")
        
        # Get scripts from YAML
        yaml_script_ids = set()
        try:
            content = await file_manager.read_file('scripts.yaml')
            scripts = yaml.safe_load(content) or {}
            if isinstance(scripts, dict):
                yaml_script_ids = set(scripts.keys())
        except FileNotFoundError:
            logger.debug("scripts.yaml not found, assuming no scripts")
        except Exception as e:
            logger.warning(f"Failed to read scripts.yaml: {e}")
        
        # Find dead entities
        dead_automations = [
            entity for entity in registry_automations
            if entity['unique_id'] not in yaml_automation_ids
        ]
        
        dead_scripts = [
            entity for entity in registry_scripts
            if entity['unique_id'] not in yaml_script_ids
        ]
        
        logger.info(f"Found {len(dead_automations)} dead automations and {len(dead_scripts)} dead scripts")
        
        return {
            "success": True,
            "dead_automations": dead_automations,
            "dead_scripts": dead_scripts,
            "summary": {
                "total_registry_automations": len(registry_automations),
                "total_registry_scripts": len(registry_scripts),
                "total_yaml_automations": len(yaml_automation_ids),
                "total_yaml_scripts": len(yaml_script_ids),
                "dead_automations_count": len(dead_automations),
                "dead_scripts_count": len(dead_scripts),
                "total_dead": len(dead_automations) + len(dead_scripts)
            }
        }
    except Exception as e:
        logger.error(f"Failed to find dead entities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to find dead entities: {str(e)}")

@router.get("/entities/{entity_id}")
async def get_entity_registry_entry(entity_id: str):
    """
    Get single entity from Entity Registry
    
    Returns entity metadata including area_id, device_id, name, disabled status, etc.
    
    Example:
    - `/api/registries/entities/climate.bedroom_trv`
    """
    try:
        ws_client = await get_ws_client()
        entity = await ws_client.get_entity_registry_entry(entity_id)
        
        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity not found in registry: {entity_id}")
        
        return {
            "success": True,
            "entity_id": entity_id,
            "entity": entity
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Entity Registry entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get Entity Registry entry: {str(e)}")

@router.post("/entities/update")
async def update_entity_registry(
    entity_id: str = Body(..., description="Entity ID to update"),
    name: Optional[str] = Body(None, description="New friendly name. Pass empty string '' to reset to original name."),
    area_id: Optional[str] = Body(None, description="Area ID to assign entity to"),
    disabled: Optional[bool] = Body(None, description="Disable/enable entity"),
    new_entity_id: Optional[str] = Body(None, description="New entity_id (rename)"),
    icon: Optional[str] = Body(None, description="Icon for entity"),
    aliases: Optional[List[str]] = Body(None, description="Aliases for entity")
):
    """
    Update entity in Entity Registry
    
    **⚠️ WARNING: This modifies Home Assistant Entity Registry!**
    
    Updates entity metadata such as name, area assignment, disabled status, etc.
    
    Example:
    ```json
    {
      "entity_id": "climate.bedroom_trv",
      "name": "Bedroom Thermostat",
      "area_id": "bedroom_area_id",
      "disabled": false
    }
    ```
    """
    try:
        ws_client = await get_ws_client()
        
        # Build update dict with only provided fields
        update_data = {}
        # Handle name: empty string means remove custom name (reset to original)
        # Pass None to WebSocket to reset to original_name
        if name is not None:
            if name == "":
                # Empty string means remove custom name - pass None to reset
                update_data['name'] = None
            else:
                update_data['name'] = name
        if area_id is not None:
            update_data['area_id'] = area_id
        if disabled is not None:
            update_data['disabled'] = disabled
        if new_entity_id is not None:
            update_data['new_entity_id'] = new_entity_id
        if icon is not None:
            update_data['icon'] = icon
        if aliases is not None:
            update_data['aliases'] = aliases
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided for update")
        
        result = await ws_client.update_entity_registry(entity_id, **update_data)
        
        logger.info(f"Updated Entity Registry: {entity_id} with {update_data}")
        return {
            "success": True,
            "entity_id": entity_id,
            "updated_fields": update_data,
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update Entity Registry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update Entity Registry: {str(e)}")

@router.post("/entities/remove")
async def remove_entity_registry_entry(request: EntityRemoveRequest):
    """
    Remove entity from Entity Registry
    
    **⚠️ WARNING: This removes entity from Entity Registry!**
    
    The entity will be removed from Home Assistant's Entity Registry.
    Note: This doesn't delete the entity itself, just removes it from the registry.
    """
    try:
        ws_client = await get_ws_client()
        result = await ws_client.remove_entity_registry_entry(request.entity_id)
        
        # Check if result indicates an error
        if isinstance(result, dict):
            if result.get('success') is False:
                error = result.get('error', {})
                error_message = error.get('message', str(error)) if isinstance(error, dict) else str(error)
                logger.error(f"Home Assistant rejected entity removal: {request.entity_id}, error: {error_message}")
                raise HTTPException(status_code=400, detail=f"Failed to remove entity: {error_message}")
        
        logger.warning(f"Removed entity from Entity Registry: {request.entity_id}")
        return {
            "success": True,
            "entity_id": request.entity_id,
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove Entity Registry entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove Entity Registry entry: {str(e)}")

# ==================== Area Registry ====================

@router.get("/areas/list")
async def list_area_registry():
    """
    Get all areas from Area Registry
    
    Returns complete Area Registry with area_id, name, aliases, etc.
    """
    try:
        ws_client = await get_ws_client()
        areas = await ws_client.get_area_registry_list()
        
        logger.info(f"Listed {len(areas)} areas from Area Registry")
        return {
            "success": True,
            "count": len(areas),
            "areas": areas
        }
    except Exception as e:
        logger.error(f"Failed to list Area Registry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list Area Registry: {str(e)}")

@router.get("/areas/{area_id}")
async def get_area_registry_entry(area_id: str):
    """
    Get single area from Area Registry
    
    Example:
    - `/api/registries/areas/bedroom_area_id`
    """
    try:
        ws_client = await get_ws_client()
        area = await ws_client.get_area_registry_entry(area_id)
        
        logger.debug(f"get_area_registry_entry returned for {area_id}: {area}")
        
        if not area:
            logger.warning(f"Area {area_id} not found, returning 404")
            raise HTTPException(status_code=404, detail=f"Area not found in registry: {area_id}")
        
        return {
            "success": True,
            "area_id": area_id,
            "area": area
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Area Registry entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get Area Registry entry: {str(e)}")

@router.post("/areas/create")
async def create_area_registry_entry(
    name: str = Body(..., description="Area name"),
    aliases: Optional[List[str]] = Body(None, description="Optional aliases for area")
):
    """
    Create new area in Area Registry
    
    **⚠️ WARNING: This creates a new area in Home Assistant!**
    
    Example:
    ```json
    {
      "name": "Living Room",
      "aliases": ["lounge", "main room"]
    }
    ```
    """
    try:
        ws_client = await get_ws_client()
        result = await ws_client.create_area_registry_entry(name, aliases)
        
        logger.info(f"Created area in Area Registry: {name}")
        return {
            "success": True,
            "name": name,
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to create Area Registry entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create Area Registry entry: {str(e)}")

@router.post("/areas/update")
async def update_area_registry_entry(
    area_id: str = Body(..., description="Area ID to update"),
    name: Optional[str] = Body(None, description="New area name"),
    aliases: Optional[List[str]] = Body(None, description="New aliases list")
):
    """
    Update area in Area Registry
    
    **⚠️ WARNING: This modifies Home Assistant Area Registry!**
    
    Example:
    ```json
    {
      "area_id": "bedroom_area_id",
      "name": "Master Bedroom",
      "aliases": ["bedroom", "main bedroom"]
    }
    ```
    """
    try:
        ws_client = await get_ws_client()
        result = await ws_client.update_area_registry_entry(area_id, name, aliases)
        
        logger.info(f"Updated Area Registry: {area_id}")
        return {
            "success": True,
            "area_id": area_id,
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to update Area Registry entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update Area Registry entry: {str(e)}")

@router.post("/areas/delete")
async def delete_area_registry_entry(request: AreaRemoveRequest):
    """
    Delete area from Area Registry
    
    **⚠️ WARNING: This deletes area from Home Assistant Area Registry!**
    """
    try:
        ws_client = await get_ws_client()
        result = await ws_client.delete_area_registry_entry(request.area_id)
        
        logger.warning(f"Deleted area from Area Registry: {request.area_id}")
        return {
            "success": True,
            "area_id": request.area_id,
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to delete Area Registry entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete Area Registry entry: {str(e)}")

# ==================== Device Registry ====================

@router.get("/devices/list")
async def list_device_registry():
    """
    Get all devices from Device Registry
    
    Returns complete Device Registry with device_id, name, area_id, manufacturer, model, etc.
    """
    try:
        ws_client = await get_ws_client()
        devices = await ws_client.get_device_registry_list()
        
        logger.info(f"Listed {len(devices)} devices from Device Registry")
        return {
            "success": True,
            "count": len(devices),
            "devices": devices
        }
    except Exception as e:
        logger.error(f"Failed to list Device Registry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list Device Registry: {str(e)}")

@router.get("/devices/{device_id}")
async def get_device_registry_entry(
    device_id: str,
    include_entities: bool = Query(
        False,
        description="If true, also return all entities belonging to this device with their descriptions",
    ),
):
    """
    Get single device from Device Registry
    
    **Parameters:**
    - `include_entities` (optional): If `true`, returns device metadata plus all entities belonging to this device with descriptions (entity_id, friendly_name, domain, what it does).
    
    **Example response (include_entities=false):**
    ```json
    {
      "success": true,
      "device_id": "...",
      "device": {
        "name": "Aqara H2 Light Switch",
        "manufacturer": "...",
        "model": "..."
      }
    }
    ```
    
    **Example response (include_entities=true):**
    ```json
    {
      "success": true,
      "device_id": "...",
      "device": {...},
      "entities": [
        {
          "entity_id": "switch.aqara_h2_switch_1",
          "friendly_name": "Aqara H2 Switch",
          "domain": "switch",
          "device_class": "outlet",
          "state": "off"
        },
        {
          "entity_id": "sensor.aqara_h2_energy",
          "friendly_name": "Aqara H2 Energy",
          "domain": "sensor",
          "device_class": "energy",
          "state": "0.0"
        }
      ]
    }
    ```
    
    Example:
    - `/api/registries/devices/device_id_123`
    - `/api/registries/devices/device_id_123?include_entities=true`
    """
    try:
        ws_client = await get_ws_client()
        device = await ws_client.get_device_registry_entry(device_id)
        
        logger.debug(f"get_device_registry_entry returned for {device_id}: {device}")
        
        if not device:
            logger.warning(f"Device {device_id} not found, returning 404")
            raise HTTPException(status_code=404, detail=f"Device not found in registry: {device_id}")
        
        response = {
            "success": True,
            "device_id": device_id,
            "device": device,
        }
        
        # If requested, also fetch and include all entities for this device
        if include_entities:
            try:
                # Get all entities from Entity Registry
                all_entities = await ws_client.get_entity_registry_list()
                
                # Filter entities that belong to this device
                device_entities = [
                    entity
                    for entity in all_entities
                    if entity.get("device_id") == device_id
                ]
                
                # Enrich with current state and additional info
                from app.services.ha_client import ha_client
                
                enriched_entities = []
                for entity in device_entities:
                    entity_id = entity.get("entity_id")
                    if not entity_id:
                        continue
                    
                    # Get current state for this entity
                    try:
                        state_data = await ha_client.get_state(entity_id)
                        current_state = state_data.get("state") if state_data else None
                        attributes = state_data.get("attributes", {}) if state_data else {}
                    except Exception:
                        current_state = None
                        attributes = {}
                    
                    # Build enriched entity info
                    enriched_entity = {
                        "entity_id": entity_id,
                        "friendly_name": entity.get("name") or attributes.get("friendly_name"),
                        "domain": entity_id.split(".", 1)[0] if "." in entity_id else None,
                        "device_class": attributes.get("device_class"),
                        "unit_of_measurement": attributes.get("unit_of_measurement"),
                        "state": current_state,
                        "disabled": entity.get("disabled", False),
                    }
                    
                    enriched_entities.append(enriched_entity)
                
                # Sort by domain, then by entity_id for consistent output
                enriched_entities.sort(key=lambda x: (x.get("domain") or "", x.get("entity_id") or ""))
                
                response["entities"] = enriched_entities
                response["entities_count"] = len(enriched_entities)
                
                logger.info(
                    f"Device {device_id} has {len(enriched_entities)} entities (include_entities=true)"
                )
            except Exception as e:
                logger.warning(f"Failed to fetch entities for device {device_id}: {e}")
                # Don't fail the whole request if entities fetch fails
                response["entities"] = []
                response["entities_count"] = 0
                response["entities_error"] = str(e)
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Device Registry entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get Device Registry entry: {str(e)}")

@router.post("/devices/update")
async def update_device_registry_entry(
    device_id: str = Body(..., description="Device ID to update"),
    area_id: Optional[str] = Body(None, description="Area ID to assign device to"),
    name_by_user: Optional[str] = Body(None, description="Custom name for device"),
    disabled_by: Optional[str] = Body(None, description="Disable device (set to 'user' to disable)")
):
    """
    Update device in Device Registry
    
    **⚠️ WARNING: This modifies Home Assistant Device Registry!**
    
    Example:
    ```json
    {
      "device_id": "device_id_123",
      "area_id": "bedroom_area_id",
      "name_by_user": "Bedroom Thermostat"
    }
    ```
    """
    try:
        ws_client = await get_ws_client()
        
        # Build update dict with only provided fields
        update_data = {}
        if area_id is not None:
            update_data['area_id'] = area_id
        if name_by_user is not None:
            update_data['name_by_user'] = name_by_user
        if disabled_by is not None:
            update_data['disabled_by'] = disabled_by
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided for update")
        
        result = await ws_client.update_device_registry_entry(device_id, **update_data)
        
        logger.info(f"Updated Device Registry: {device_id} with {update_data}")
        return {
            "success": True,
            "device_id": device_id,
            "updated_fields": update_data,
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update Device Registry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update Device Registry: {str(e)}")

@router.post("/devices/remove")
async def remove_device_registry_entry(request: DeviceRemoveRequest):
    """
    Remove device from Device Registry
    
    **⚠️ WARNING: This removes device from Device Registry!**
    """
    try:
        ws_client = await get_ws_client()
        result = await ws_client.remove_device_registry_entry(request.device_id)
        
        logger.warning(f"Removed device from Device Registry: {request.device_id}")
        return {
            "success": True,
            "device_id": request.device_id,
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to remove Device Registry entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove Device Registry entry: {str(e)}")


