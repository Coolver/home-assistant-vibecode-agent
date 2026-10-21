"""Config entries and config/options flows API endpoints

Covers what the Home Assistant UI does through dialogs: adding integrations,
creating UI helpers (e.g. 'Change device type of a switch'), the 'Configure'
dialog of an integration, reloading, and deleting integrations.
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, Dict, Any
import logging

from app.services.ha_client import ha_client

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')


def _summary(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "entry_id": entry.get("entry_id"),
        "domain": entry.get("domain"),
        "title": entry.get("title"),
        "state": entry.get("state"),
        "source": entry.get("source"),
        "disabled_by": entry.get("disabled_by"),
    }


@router.get("/list")
async def list_config_entries(
    domain: Optional[str] = Query(None, description="Only entries of this integration domain (e.g. 'zha', 'switch_as_x')"),
):
    """
    List config entries: integrations and UI-created helpers.

    **Example:** `/api/config_entries/list?domain=switch_as_x`
    """
    try:
        entries = await ha_client.list_config_entries()
        if domain:
            entries = [e for e in entries if e.get("domain") == domain]
        return {"success": True, "count": len(entries), "entries": [_summary(e) for e in entries]}
    except Exception as e:
        logger.error(f"Failed to list config entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flow/start")
async def start_config_flow(
    handler: str = Body(..., embed=True, description="Integration or helper domain, e.g. 'switch_as_x', 'template', 'group'"),
    show_advanced_options: bool = Body(False, embed=True, description="Show advanced options in the flow"),
):
    """
    Start a config flow, like 'Add integration' or 'Create helper' in the UI.

    Returns the first step. A `form` step lists its fields in `data_schema`;
    submit them with `POST /api/config_entries/flow/{flow_id}`. A `menu` step lists
    `menu_options`; submit `{"user_input": {"next_step_id": "<option>"}}`.
    The flow ends with type `create_entry` (done) or `abort` (see `reason`).

    **Example (turn a switch into a light):**
    1. `POST /api/config_entries/flow/start` `{"handler": "switch_as_x"}`
    2. `POST /api/config_entries/flow/<flow_id>` `{"user_input": {"entity_id": "switch.tv", "target_domain": "light"}}`
    """
    try:
        flow = await ha_client.start_config_flow(handler, show_advanced_options)
        return {"success": True, "flow": flow}
    except Exception as e:
        logger.error(f"Failed to start config flow for {handler}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flow/{flow_id}")
async def config_flow_step(
    flow_id: str,
    user_input: Dict[str, Any] = Body(..., embed=True, description="Values for the fields of the current step"),
):
    """Submit the current step of a config flow. Values are not written to the agent log."""
    try:
        flow = await ha_client.config_flow_step(flow_id, user_input)
        return {"success": True, "flow": flow}
    except Exception as e:
        logger.error(f"Config flow step failed for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/flow/{flow_id}")
async def abort_config_flow(flow_id: str):
    """Abort a config flow in progress"""
    try:
        result = await ha_client.abort_config_flow(flow_id)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Failed to abort config flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/options_flow/start")
async def start_options_flow(
    entry_id: str = Body(..., embed=True, description="Config entry to configure (from /api/config_entries/list)"),
):
    """Start the options flow of a config entry, like 'Configure' on an integration in the UI"""
    try:
        flow = await ha_client.start_options_flow(entry_id)
        return {"success": True, "flow": flow}
    except Exception as e:
        logger.error(f"Failed to start options flow for {entry_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/options_flow/{flow_id}")
async def options_flow_step(
    flow_id: str,
    user_input: Dict[str, Any] = Body(..., embed=True, description="Values for the fields of the current step"),
):
    """Submit the current step of an options flow. Values are not written to the agent log."""
    try:
        flow = await ha_client.options_flow_step(flow_id, user_input)
        return {"success": True, "flow": flow}
    except Exception as e:
        logger.error(f"Options flow step failed for {flow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/options_flow/{flow_id}")
async def abort_options_flow(flow_id: str):
    """Abort an options flow in progress"""
    try:
        result = await ha_client.abort_options_flow(flow_id)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Failed to abort options flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{entry_id}/reload")
async def reload_config_entry(entry_id: str):
    """Reload a config entry (restarts that integration without restarting Home Assistant)"""
    try:
        result = await ha_client.reload_config_entry(entry_id)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Failed to reload config entry {entry_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{entry_id}")
async def delete_config_entry(
    entry_id: str,
    confirm: bool = Query(False, description="Must be true: deleting removes the integration and all its entities"),
):
    """
    Delete a config entry, like 'Delete' on an integration or UI helper.

    **⚠️ Removes the integration (or helper) and its devices and entities.**
    Automations that use them stop working. Requires `?confirm=true`.
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="Deleting a config entry removes the integration and its entities; pass confirm=true")
    try:
        result = await ha_client.delete_config_entry(entry_id)
        logger.warning(f"Deleted config entry {entry_id}")
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Failed to delete config entry {entry_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
