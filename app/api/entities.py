"""Entities API endpoints"""
import asyncio
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
import logging
import math
import json

from rapidfuzz import fuzz, process as fuzz_process
from app.services.ha_client import ha_client

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')

def _parse_dict_like(value: Any) -> Optional[Dict[str, Any]]:
    """Parse dict-like value from object or JSON string."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None
    return None


@router.get("/list")
async def list_entities(
    domain: Optional[str] = Query(None, description="Filter by domain (e.g., 'sensor', 'climate')"),
    search: Optional[str] = Query(None, description="Search in entity_id or friendly_name"),
    fuzzy: bool = Query(
        False,
        description="If true, use fuzzy matching for search (tolerates typos like 'bedrrom' -> 'bedroom'). "
                    "Returns results sorted by relevance score.",
    ),
    fuzzy_threshold: int = Query(
        60,
        ge=0,
        le=100,
        description="Minimum fuzzy match score (0-100). Default 60. Only used when fuzzy=true.",
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(
        250,
        ge=1,
        le=500,
        description="Entities per page (default 250, max 500). Helps avoid overloading LLM context.",
    ),
    ids_only: bool = Query(
        False,
        description="If true, return only list of entity IDs without any other data. Most token-efficient option.",
    ),
    summary_only: bool = Query(
        False,
        description=(
            "If true, return lightweight summary per entity (entity_id, state, domain, friendly_name) "
            "instead of full Home Assistant state objects. Ignored if ids_only=true."
        ),
    ),
):
    """
    Get entities with optional filters, pagination and lightweight modes.

    This endpoint is designed to be LLM-friendly for installations with many entities:
    it supports filtering, pagination and lightweight formats to avoid overloading the model context.
    
    **Parameters:**
    - `ids_only` (optional): If `true`, returns only list of entity IDs. If `false` (default), returns full or summary data.
    - `summary_only` (optional): If `true` and `ids_only=false`, returns lightweight summary per entity. Ignored if `ids_only=true`.
    
    **Examples:**
    - `/api/entities/list` - First page (up to 250 entities, full state objects)
    - `/api/entities/list?domain=climate` - Only climate entities (paginated)
    - `/api/entities/list?search=bedroom` - Search for 'bedroom' in id or friendly_name
    - `/api/entities/list?ids_only=true` - Only entity IDs: `["light.kitchen", "sensor.temp", ...]`
    - `/api/entities/list?summary_only=true&page=1&page_size=250` - Lightweight summaries for first page
    """
    try:
        states = await ha_client.get_states()
        
        # Filter by domain
        if domain:
            states = [s for s in states if s['entity_id'].startswith(f"{domain}.")]
        
        # Search by entity_id or friendly_name
        if search:
            if fuzzy:
                scored = []
                for s in states:
                    entity_id = s['entity_id']
                    friendly_name = s.get('attributes', {}).get('friendly_name', '')
                    score = max(
                        fuzz.partial_ratio(search.lower(), entity_id.lower()),
                        fuzz.partial_ratio(search.lower(), friendly_name.lower()),
                    )
                    if score >= fuzzy_threshold:
                        scored.append((s, score))
                scored.sort(key=lambda x: x[1], reverse=True)
                states = [s for s, _ in scored]
            else:
                search_lower = search.lower()
                states = [
                    s
                    for s in states
                    if search_lower in s['entity_id'].lower()
                    or search_lower in s.get('attributes', {}).get('friendly_name', '').lower()
                ]
        
        total = len(states)
        if total == 0:
            logger.info("Listed 0 entities (no matches for filters)")
            if ids_only:
                return {
                    "success": True,
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0,
                    "entity_ids": [],
                }
            return {
                "success": True,
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "entities": [],
            }
        
        # Pagination
        total_pages = max(1, math.ceil(total / page_size))
        if page > total_pages:
            # Out-of-range page - return empty list but keep metadata
            logger.info(
                f"Requested entities page {page} out of range (total_pages={total_pages}), "
                f"returning empty result"
            )
            if ids_only:
                return {
                    "success": True,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "entity_ids": [],
                }
            return {
                "success": True,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "entities": [],
            }
        
        start = (page - 1) * page_size
        end = start + page_size
        page_states = states[start:end]
        
        # IDs-only mode - most token-efficient, returns just list of entity_id strings
        if ids_only:
            entity_ids = [s.get('entity_id') for s in page_states if s.get('entity_id')]
            logger.info(
                f"Listed {len(entity_ids)} entity IDs (page {page}/{total_pages}, total={total})"
            )
            return {
                "success": True,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "entity_ids": entity_ids,
            }
        
        # Lightweight summary mode to save tokens/context
        if summary_only:
            def _summary(state: Dict[str, Any]) -> Dict[str, Any]:
                attrs = state.get('attributes', {}) or {}
                entity_id = state.get('entity_id')
                domain_part = entity_id.split('.', 1)[0] if entity_id and '.' in entity_id else None
                return {
                    "entity_id": entity_id,
                    "state": state.get('state'),
                    "domain": domain_part,
                    "friendly_name": attrs.get('friendly_name'),
                }
            
            entities = [_summary(s) for s in page_states]
        else:
            entities = page_states
        
        logger.info(
            f"Listed {len(entities)} entities (page {page}/{total_pages}, "
            f"total={total}, summary_only={summary_only})"
        )
        return {
            "success": True,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "entities": entities,
        }
    except Exception as e:
        logger.error(f"Failed to list entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/state/{entity_id}")
async def get_entity_state(entity_id: str):
    """
    Get specific entity state
    
    Example:
    - `/api/entities/state/climate.bedroom_trv_thermostat`
    """
    try:
        state = await ha_client.get_state(entity_id)
        return {
            "success": True,
            "entity_id": entity_id,
            "state": state
        }
    except Exception as e:
        logger.error(f"Failed to get entity state: {e}")
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")

@router.get("/services")
async def list_services():
    """
    Get all available Home Assistant services
    
    Returns complete list of services with descriptions
    """
    try:
        services = await ha_client.get_services()
        return {
            "success": True,
            "count": len(services),
            "services": services
        }
    except Exception as e:
        logger.error(f"Failed to list services: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/call_service")
async def call_service(
    domain: str = Body(..., description="Service domain (e.g., 'number', 'light', 'climate')"),
    service: str = Body(..., description="Service name (e.g., 'set_value', 'turn_on', 'set_temperature')"),
    service_data: Optional[Any] = Body(None, description="Service data (e.g., {'entity_id': 'number.alex_trv_local_temperature_offset', 'value': -2.0})"),
    target: Optional[Any] = Body(None, description="Target entity/entities (e.g., {'entity_id': 'light.living_room'})"),
    data_alias: Optional[Any] = Body(None, alias="data", description="Backward-compatible alias for service_data"),
    wait_for_state: Optional[str] = Body(None, description="If set, poll the target entity until it reaches this state (e.g., 'on', 'off', '21.0')"),
    wait_timeout: float = Body(10.0, description="Max seconds to wait for state change (default 10). Only used with wait_for_state."),
    return_response: bool = Body(False, description="Ask Home Assistant for the service's return value. Needed for weather.get_forecasts, calendar.get_events, todo.get_items, and any service that refuses a caller that does not accept a response."),
):
    """
    Call a Home Assistant service
    
    Examples:
    - Set number value: {"domain": "number", "service": "set_value", "service_data": {"entity_id": "number.alex_trv_local_temperature_offset", "value": -2.0}}
    - Turn on light: {"domain": "light", "service": "turn_on", "target": {"entity_id": "light.living_room"}}
    - Set climate temperature: {"domain": "climate", "service": "set_temperature", "target": {"entity_id": "climate.bedroom_trv_thermostat"}, "service_data": {"temperature": 21.0}}
    - Turn on and wait: {"domain": "light", "service": "turn_on", "target": {"entity_id": "light.living_room"}, "wait_for_state": "on"}
    """
    try:
        service_data = _parse_dict_like(service_data)

        if service_data is None and data_alias is not None:
            service_data = _parse_dict_like(data_alias)

        target = _parse_dict_like(target)

        # Combine service_data and target into data dict
        data = {}
        if service_data:
            data.update(service_data)
        if target:
            if 'entity_id' in target:
                data['entity_id'] = target['entity_id']
            if 'area_id' in target:
                data['area_id'] = target['area_id']
            if 'device_id' in target:
                data['device_id'] = target['device_id']
            if not any(k in data for k in ['entity_id', 'area_id', 'device_id']):
                data['target'] = target
        
        if return_response:
            # The REST service API drops the return value, and Home Assistant
            # refuses services that require a response consumer. The WebSocket
            # command is the one the UI uses for those.
            from app.services.ha_websocket import get_ws_client
            ws_client = await get_ws_client()
            result = await ws_client.call_service(
                domain,
                service,
                service_data=service_data or None,
                target=target or None,
                return_response=True,
            )
        else:
            result = await ha_client.call_service(domain, service, data)
        logger.info(f"Service called: {domain}.{service}")

        response = {
            "success": True,
            "domain": domain,
            "service": service,
            "data": data,
            "result": result
        }
        if return_response:
            response["response"] = result.get("response") if isinstance(result, dict) else None

        # Poll for expected state if requested
        if wait_for_state and data.get('entity_id'):
            entity_id = data['entity_id']
            poll_interval = 0.5
            elapsed = 0.0
            state_reached = False

            while elapsed < wait_timeout:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
                try:
                    state_obj = await ha_client.get_state(entity_id)
                    current_state = state_obj.get('state', '') if isinstance(state_obj, dict) else ''
                    if str(current_state).lower() == str(wait_for_state).lower():
                        state_reached = True
                        break
                except Exception:
                    pass

            response["wait_for_state"] = {
                "expected": wait_for_state,
                "reached": state_reached,
                "elapsed_seconds": round(elapsed, 1),
            }

        return response
    except Exception as e:
        logger.error(f"Failed to call service {domain}.{service}: {e}")
        raise HTTPException(status_code=500, detail=f"Service call failed: {str(e)}")

@router.get("/exposed")
async def list_exposed_entities(
    assistant: str = Query("conversation", description="Assistant name: 'conversation', 'cloud.alexa', or 'cloud.google_assistant'"),
):
    """
    List entities exposed to a voice assistant.

    Uses the HA WebSocket command `homeassistant/expose_entity/list`.

    **Examples:**
    - `/api/entities/exposed` - entities exposed to Assist/Ollama (conversation)
    - `/api/entities/exposed?assistant=cloud.alexa` - entities exposed to Alexa
    """
    try:
        from app.services.ha_websocket import get_ws_client
        ws_client = await get_ws_client()
        all_exposed = await ws_client.list_exposed_entities()

        exposed_ids = [
            eid for eid, assistants in all_exposed.items()
            if assistants.get(assistant) is True
        ]

        logger.info(f"Listed {len(exposed_ids)} entities exposed to {assistant}")
        return {
            "success": True,
            "assistant": assistant,
            "count": len(exposed_ids),
            "entity_ids": sorted(exposed_ids),
        }
    except Exception as e:
        logger.error(f"Failed to list exposed entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/expose")
async def expose_entities(
    entity_ids: List[str] = Body(..., description="List of entity IDs to expose or unexpose"),
    should_expose: bool = Body(True, description="True to expose, False to unexpose"),
    assistant: str = Body("conversation", description="Assistant name: 'conversation', 'cloud.alexa', or 'cloud.google_assistant'"),
):
    """
    Expose or unexpose entities to a voice assistant.

    Uses the HA WebSocket command `homeassistant/expose_entity`.
    Changes take effect immediately (no HA restart needed).

    **Examples:**
    - Expose to Assist: `{"entity_ids": ["light.kitchen", "sensor.temp"], "should_expose": true}`
    - Unexpose from Alexa: `{"entity_ids": ["light.kitchen"], "should_expose": false, "assistant": "cloud.alexa"}`
    """
    try:
        from app.services.ha_websocket import get_ws_client
        ws_client = await get_ws_client()
        result = await ws_client.expose_entities(entity_ids, [assistant], should_expose)

        action = "Exposed" if should_expose else "Unexposed"
        logger.info(f"{action} {len(entity_ids)} entities to {assistant}")
        return {
            "success": True,
            "action": action.lower(),
            "assistant": assistant,
            "count": len(entity_ids),
            "entity_ids": entity_ids,
        }
    except Exception as e:
        logger.error(f"Failed to expose/unexpose entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rename")
async def rename_entity(
    old_entity_id: str = Body(..., description="Current entity_id (e.g., 'climate.sonoff_trvzb_thermostat')"),
    new_entity_id: str = Body(..., description="New entity_id (e.g., 'climate.office_trv_thermostat')"),
    new_name: Optional[str] = Body(None, description="Optional new friendly name")
):
    """
    Rename an entity_id via Entity Registry WebSocket API
    
    This will update the entity_id in Home Assistant's entity registry.
    Note: After renaming, you may need to reload automations/scripts that reference the entity.
    
    Example:
    - {"old_entity_id": "climate.sonoff_trvzb_thermostat", "new_entity_id": "climate.office_trv_thermostat", "new_name": "Office TRV Thermostat"}
    """
    try:
        result = await ha_client.rename_entity(old_entity_id, new_entity_id, new_name)
        logger.info(f"Renamed entity: {old_entity_id} → {new_entity_id}")
        return {
            "success": True,
            "old_entity_id": old_entity_id,
            "new_entity_id": new_entity_id,
            "new_name": new_name,
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to rename entity {old_entity_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to rename entity: {str(e)}")

