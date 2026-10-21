"""Logs API endpoints"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging
import re

from app.services.supervisor_client import supervisor_client
from app.utils.logger import get_logs

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')

# Supervisor's no_colors flag covers current cores. Older gateways still emit
# CSI sequences, so strip whatever remains before the text reaches a client.
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# Home Assistant's own line: "2026-10-21 12:00:00.000 ERROR (MainThread) [logger] ..."
_ENTRY = re.compile(r"\b(DEBUG|INFO|WARNING|ERROR|CRITICAL) \(")
_RANK = {name: index for index, name in enumerate(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])}
_JOURNAL_SOURCES = ("core", "supervisor", "host")


def strip_ansi(text: str) -> str:
    return _ANSI.sub("", text)


def filter_log_level(text: str, level: Optional[str]) -> str:
    """Keep entries at or above `level`, including the traceback that follows them."""
    if not level:
        return text
    minimum = _RANK[level.upper()]
    kept = []
    keeping = False
    for line in text.splitlines():
        match = _ENTRY.search(line)
        if match:
            keeping = _RANK[match.group(1)] >= minimum
        if keeping:
            kept.append(line)
    return "\n".join(kept)

@router.get("")
async def get_agent_logs(
    limit: int = Query(100, description="Number of log entries to return"),
    level: Optional[str] = Query(None, description="Filter by level: DEBUG, INFO, WARNING, ERROR")
):
    """
    Get agent logs
    
    Returns recent log entries from the agent
    
    **Examples:**
    - `/api/logs` - Last 100 log entries
    - `/api/logs?limit=50` - Last 50 entries
    - `/api/logs?level=ERROR` - Only errors
    """
    try:
        logs = get_logs(limit=limit, level=level)
        
        return {
            "success": True,
            "count": len(logs),
            "logs": logs
        }
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        return {
            "success": False,
            "count": 0,
            "logs": [],
            "error": str(e)
        }

@router.get("/journal")
async def get_journal_logs(
    source: str = Query("core", description="Journal to read: core, supervisor, or host"),
    lines: int = Query(100, ge=2, le=500, description="How many recent lines to ask Supervisor for"),
    level: Optional[str] = Query(None, description="Minimum level to keep: DEBUG, INFO, WARNING, ERROR, CRITICAL"),
):
    """
    Read the Supervisor journal that Settings → System → Logs shows.

    `/api/logs` is this add-on's own log. Core stopped writing
    `home-assistant.log`, so the core journal is a separate call.
    `host` is the OS journal and is much noisier.
    """
    if source not in _JOURNAL_SOURCES:
        raise HTTPException(status_code=422, detail="source must be core, supervisor, or host")
    if level is not None and level.upper() not in _RANK:
        raise HTTPException(
            status_code=422,
            detail="level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL",
        )

    if not supervisor_client.is_available():
        raise HTTPException(
            status_code=501,
            detail="Core logs come from the Supervisor journal and are only available when this add-on runs under Home Assistant OS.",
        )

    try:
        raw = await supervisor_client.get_journal_logs(source, lines)
    except Exception as e:
        logger.error(f"Failed to read {source} journal: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to read {source} logs: {e}")

    logs = filter_log_level(strip_ansi(raw), level.upper() if level else None)
    return {
        "success": True,
        "source": source,
        "lines": lines,
        "level": level.upper() if level else None,
        "logs": logs,
    }


@router.delete("/clear")
async def clear_logs():
    """
    Clear agent logs
    
    Clears the in-memory log buffer
    """
    try:
        from app.utils.logger import LOG_BUFFER
        LOG_BUFFER.clear()
        
        logger.info("Logs cleared")
        
        return {
            "success": True,
            "message": "Logs cleared"
        }
    except Exception as e:
        logger.error(f"Failed to clear logs: {e}")
        return {
            "success": False,
            "message": str(e)
        }

