"""Home Assistant System Logs API - reads actual HA log files and error_log endpoint"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging
import os
import aiofiles
from pathlib import Path

from app.services.ha_client import ha_client

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')

LOG_PATHS = [
    '/config/home-assistant.log',
    '/homeassistant/home-assistant.log',
    '/usr/share/hassio/homeassistant/home-assistant.log',
]


def _find_log_file() -> Optional[str]:
    """Find the actual home-assistant.log file path"""
    for p in LOG_PATHS:
        if Path(p).exists():
            return p
    return None


async def _fetch_error_log_api() -> str:
    """Fetch logs from HA /api/error_log via SUPERVISOR_TOKEN"""
    import aiohttp
    import os
    # SUPERVISOR_TOKEN is set by HA Supervisor for add-ons with hassio_api: true
    token = os.environ.get('SUPERVISOR_TOKEN') or os.environ.get('HA_TOKEN') or ha_client.token
    # The error_log endpoint is on the HA Core API, accessible via supervisor proxy
    url = "http://supervisor/core/api/error_log"
    logger.info(f"Fetching error_log, token present: {bool(token)}, token length: {len(token) if token else 0}")
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            logger.info(f"error_log response status: {resp.status}")
            if resp.status >= 400:
                text = await resp.text()
                raise Exception(f"HA error_log returned {resp.status}: {text[:200]}")
            return await resp.text()


@router.get("/ha_system")
async def get_ha_system_logs(
    tail: int = Query(200, description="Number of lines to return from end of log", ge=1, le=5000),
    filter: Optional[str] = Query(None, description="Filter string (case-insensitive). E.g. 'zendure', 'ERROR', 'WARNING'"),
    level: Optional[str] = Query(None, description="Filter by log level: ERROR, WARNING, INFO, DEBUG"),
    use_api: bool = Query(True, description="Try HA /api/error_log first (recommended). Falls back to file read."),
):
    """
    Get actual Home Assistant system logs (home-assistant.log).

    Unlike /api/logs which returns only agent-internal logs, this endpoint reads the
    real HA log file or uses the Supervisor API to fetch system-wide log entries.

    **Parameters:**
    - `tail`: Number of lines to return (default 200, max 5000)
    - `filter`: Optional substring filter (case-insensitive). E.g. 'zendure', 'custom_components'
    - `level`: Filter by log level (ERROR, WARNING, INFO, DEBUG)
    - `use_api`: Use HA /api/error_log endpoint (default true). Falls back to direct file read.

    **Examples:**
    - `/api/ha_logs/ha_system?tail=100&filter=zendure` - Last 100 Zendure log lines
    - `/api/ha_logs/ha_system?level=ERROR` - Only errors
    - `/api/ha_logs/ha_system?filter=custom_components.zendure_ha&tail=50` - Zendure integration logs
    """
    raw_content = None
    source = None

    # Try Supervisor API first
    if use_api and SUPERVISOR_TOKEN:
        try:
            raw_content = await _fetch_error_log_api()
            source = "supervisor_api"
            logger.info(f"Fetched HA system logs via Supervisor API ({len(raw_content)} bytes)")
        except Exception as e:
            logger.warning(f"Supervisor API log fetch failed: {e}, falling back to file")

    # Fallback: read file directly
    if raw_content is None:
        log_path = _find_log_file()
        if log_path:
            try:
                async with aiofiles.open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    raw_content = await f.read()
                source = f"file:{log_path}"
                logger.info(f"Read HA system log from {log_path} ({len(raw_content)} bytes)")
            except Exception as e:
                logger.error(f"Failed to read log file {log_path}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to read log file: {e}")
        else:
            raise HTTPException(
                status_code=404,
                detail="home-assistant.log not found. Checked: " + ", ".join(LOG_PATHS)
            )

    # Split into lines
    lines = raw_content.splitlines()

    # Apply level filter
    if level:
        level_upper = level.upper()
        lines = [l for l in lines if level_upper in l]

    # Apply text filter
    if filter:
        filter_lower = filter.lower()
        lines = [l for l in lines if filter_lower in l.lower()]

    # Apply tail
    lines = lines[-tail:]

    return {
        "success": True,
        "source": source,
        "total_lines": len(lines),
        "filter_applied": filter,
        "level_filter": level,
        "tail": tail,
        "lines": lines,
        "raw": "\n".join(lines),
    }


@router.get("/ha_system/zendure")
async def get_zendure_logs(
    tail: int = Query(100, description="Number of Zendure log lines to return", ge=1, le=2000),
    level: Optional[str] = Query(None, description="Filter by level: ERROR, WARNING, INFO, DEBUG"),
):
    """
    Get Zendure integration logs from home-assistant.log.

    Convenience shortcut that filters for 'zendure' or 'custom_components.zendure_ha'
    entries in the HA system log.

    **Examples:**
    - `/api/ha_logs/ha_system/zendure` - Last 100 Zendure log lines
    - `/api/ha_logs/ha_system/zendure?level=ERROR` - Only Zendure errors
    - `/api/ha_logs/ha_system/zendure?tail=50` - Last 50 Zendure lines
    """
    raw_content = None

    if SUPERVISOR_TOKEN:
        try:
            raw_content = await _fetch_error_log_api()
        except Exception as e:
            logger.warning(f"Supervisor API failed: {e}")

    if raw_content is None:
        log_path = _find_log_file()
        if log_path:
            try:
                async with aiofiles.open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    raw_content = await f.read()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to read log: {e}")
        else:
            raise HTTPException(status_code=404, detail="home-assistant.log not found")

    lines = raw_content.splitlines()

    # Filter for zendure
    zendure_lines = [l for l in lines if 'zendure' in l.lower()]

    # Level filter
    if level:
        level_upper = level.upper()
        zendure_lines = [l for l in zendure_lines if level_upper in l]

    zendure_lines = zendure_lines[-tail:]

    # Parse structured summary
    errors = [l for l in zendure_lines if 'ERROR' in l]
    warnings = [l for l in zendure_lines if 'WARNING' in l]
    p1_events = [l for l in zendure_lines if 'p1' in l.lower() or 'powerchanged' in l.lower() or 'P1 ======>' in l]

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
