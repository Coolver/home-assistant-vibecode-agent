"""Home Assistant System Logs API - uses Supervisor /host/logs/ and system_log integration"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging
import os
import aiohttp
from pathlib import Path

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')


def _get_supervisor_token() -> str:
    """Get SUPERVISOR_TOKEN from environment (set by HA Supervisor for add-ons)"""
    return os.environ.get('SUPERVISOR_TOKEN', '')


async def _fetch_supervisor_logs(identifier: str = "homeassistant", num_entries: int = 500) -> str:
    """
    Fetch logs via Supervisor /host/logs/{identifier}/entries API.
    This replaces the deprecated /api/error_log endpoint.
    Requires hassio_api: true and hassio_role: manager in config.yaml.
    """
    token = _get_supervisor_token()
    if not token:
        raise Exception("SUPERVISOR_TOKEN not available")

    # Use the Supervisor API directly (not via /core proxy)
    # Range header: entries=:skip:num_entries (negative from end)
    url = f"http://supervisor/host/logs/{identifier}/entries"
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'text/plain',
        'Range': f'entries=:-{num_entries}:{num_entries}',
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            logger.info(f"Supervisor logs response: {resp.status} for {identifier}")
            if resp.status == 404:
                raise Exception(f"Log identifier '{identifier}' not found (404)")
            if resp.status >= 400:
                text = await resp.text()
                raise Exception(f"Supervisor logs API returned {resp.status}: {text[:200]}")
            return await resp.text()


async def _fetch_system_log_via_ws() -> list:
    """
    Fetch system_log entries via HA WebSocket API (system_log/list).
    Returns list of log entry dicts.
    """
    try:
        from app.services.websocket_client import ws_client
        result = await ws_client.call_service_and_get_result(
            "system_log", "list_entries", {}
        )
        return result or []
    except Exception as e:
        logger.warning(f"system_log WebSocket fetch failed: {e}")
        return []


@router.get("/ha_system")
async def get_ha_system_logs(
    tail: int = Query(200, description="Number of lines to return", ge=1, le=5000),
    filter: Optional[str] = Query(None, description="Filter string (case-insensitive)"),
    level: Optional[str] = Query(None, description="Filter by level: ERROR, WARNING, INFO, DEBUG"),
    identifier: str = Query("homeassistant", description="Log identifier: homeassistant, supervisor, core, etc."),
):
    """
    Get actual Home Assistant system logs via Supervisor /host/logs/ API.

    Uses the Supervisor API (requires hassio_api: true, hassio_role: manager).
    Falls back to system_log integration entries if Supervisor API fails.

    **Examples:**
    - `/api/ha_logs/ha_system?tail=100&filter=zendure` - Last 100 Zendure log lines
    - `/api/ha_logs/ha_system?level=ERROR` - Only errors
    - `/api/ha_logs/ha_system?identifier=supervisor` - Supervisor logs
    """
    raw_content = None
    source = None

    # Try Supervisor /host/logs/ API first
    token = _get_supervisor_token()
    if token:
        try:
            raw_content = await _fetch_supervisor_logs(identifier=identifier, num_entries=min(tail * 3, 2000))
            source = f"supervisor_host_logs:{identifier}"
            logger.info(f"Fetched logs via Supervisor API ({len(raw_content)} bytes)")
        except Exception as e:
            logger.warning(f"Supervisor logs API failed: {e}")

    if raw_content is None:
        raise HTTPException(
            status_code=503,
            detail=f"Could not fetch logs. Token present: {bool(token)}. "
                   f"Requires hassio_api: true and hassio_role: manager in config.yaml."
        )

    lines = raw_content.splitlines()

    if level:
        lines = [l for l in lines if level.upper() in l.upper()]

    if filter:
        lines = [l for l in lines if filter.lower() in l.lower()]

    lines = lines[-tail:]

    return {
        "success": True,
        "source": source,
        "total_lines": len(lines),
        "filter_applied": filter,
        "level_filter": level,
        "tail": tail,
        "identifier": identifier,
        "lines": lines,
        "raw": "\n".join(lines),
    }


@router.get("/ha_system/zendure")
async def get_zendure_logs(
    tail: int = Query(100, description="Number of Zendure log lines to return", ge=1, le=2000),
    level: Optional[str] = Query(None, description="Filter by level: ERROR, WARNING, INFO, DEBUG"),
):
    """
    Get Zendure integration logs from Home Assistant system logs.

    Fetches HA logs via Supervisor API and filters for Zendure-related entries.

    **Examples:**
    - `/api/ha_logs/ha_system/zendure` - Last 100 Zendure lines
    - `/api/ha_logs/ha_system/zendure?level=ERROR` - Only Zendure errors
    """
    token = _get_supervisor_token()
    raw_content = None

    if token:
        try:
            raw_content = await _fetch_supervisor_logs(identifier="homeassistant", num_entries=2000)
        except Exception as e:
            logger.warning(f"Supervisor logs failed for zendure endpoint: {e}")

    if raw_content is None:
        raise HTTPException(
            status_code=503,
            detail=f"home-assistant.log not found. Token present: {bool(token)}. "
                   f"Requires hassio_api: true and hassio_role: manager in config.yaml."
        )

    lines = raw_content.splitlines()
    zendure_lines = [l for l in lines if 'zendure' in l.lower()]

    if level:
        zendure_lines = [l for l in zendure_lines if level.upper() in l.upper()]

    zendure_lines = zendure_lines[-tail:]

    errors = [l for l in zendure_lines if 'ERROR' in l]
    warnings = [l for l in zendure_lines if 'WARNING' in l]
    p1_events = [l for l in zendure_lines if 'p1' in l.lower() or 'powerchanged' in l.lower()]

    return {
        "success": True,
        "total_zendure_lines": len(zendure_lines),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "p1_event_count": len(p1_events),
        "recent_errors": errors[-10:],
        "recent_warnings": warnings[-10:],
        "recent_p1_events": p1_events[-5:],
        "all_lines": zendure_lines,
    }
