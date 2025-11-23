"""Logbook API endpoints"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from collections import Counter
import asyncio
import logging

from app.services.ha_client import ha_client

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')


def _parse_iso_timestamp(value: str) -> datetime:
    """Parse ISO 8601 timestamp strings (supports trailing Z)."""
    try:
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        return datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid ISO timestamp: {value}")


def _normalize_list(values: Optional[List[str]]) -> List[str]:
    """Split comma-separated values and drop empties."""
    normalized: List[str] = []
    if not values:
        return normalized
    
    for value in values:
        if not value:
            continue
        parts = [part.strip() for part in value.split(',')]
        normalized.extend([part for part in parts if part])
    return normalized


def _to_ha_timestamp(dt: datetime) -> str:
    """Convert datetime to HA-friendly ISO string (Z suffix)."""
    iso = dt.astimezone(timezone.utc).isoformat()
    if iso.endswith('+00:00'):
        iso = iso[:-6] + 'Z'
    return iso


def _counter_to_list(counter: Counter, limit: int = 10) -> List[Dict[str, Any]]:
    return [
        {"key": key, "count": count}
        for key, count in counter.most_common(limit)
    ]


def _build_run_overview(entries: List[Dict[str, Any]], domain: str, limit: int = 10) -> List[Dict[str, Any]]:
    counts: Counter = Counter()
    latest: Dict[str, Optional[str]] = {}
    
    for entry in entries:
        if entry.get('domain') != domain:
            continue
        entity = entry.get('entity_id') or 'unknown'
        counts[entity] += 1
        when = entry.get('when')
        if when and (entity not in latest or (latest[entity] and when > latest[entity])):
            latest[entity] = when
        elif when and entity not in latest:
            latest[entity] = when
    
    overview = []
    for entity_id, count in counts.most_common(limit):
        overview.append({
            "entity_id": entity_id,
            "count": count,
            "last_seen": latest.get(entity_id)
        })
    return overview


@router.get("")
async def get_logbook_entries(
    start_time: Optional[str] = Query(None, description="ISO timestamp (UTC) for the beginning of the window"),
    end_time: Optional[str] = Query(None, description="ISO timestamp (UTC) for the end of the window"),
    lookback_minutes: int = Query(120, ge=1, le=1440, description="Used when start_time is not provided"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of entries to return"),
    entity_id: Optional[str] = Query(None, description="Single entity_id to filter (e.g., script.my_script)"),
    entity_ids: Optional[List[str]] = Query(None, description="Additional entity_ids (comma separated or repeated)"),
    domain: Optional[str] = Query(None, description="Filter by a specific domain (automation, script, light, etc.)"),
    domains: Optional[List[str]] = Query(None, description="Filter by multiple domains (comma separated or repeated)"),
    event_type: Optional[str] = Query(None, description="Filter by a specific logbook event type"),
    event_types: Optional[List[str]] = Query(None, description="Filter by multiple event types (comma separated or repeated)"),
    search: Optional[str] = Query(None, description="Case-insensitive search in name/message/entity_id")
):
    """
    Fetch logbook entries from Home Assistant with optional filters.
    
    Useful for analyzing recent automation/script executions or other system events.
    """
    now = datetime.now(timezone.utc)
    
    if end_time:
        end_dt = _parse_iso_timestamp(end_time)
    else:
        end_dt = now
    
    if start_time:
        start_dt = _parse_iso_timestamp(start_time)
    else:
        start_dt = end_dt - timedelta(minutes=lookback_minutes)
    
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="end_time must be greater than start_time")
    
    start_iso = _to_ha_timestamp(start_dt)
    end_iso = _to_ha_timestamp(end_dt)
    
    entity_filters = _normalize_list(entity_ids)
    if entity_id:
        entity_filters.append(entity_id.strip())
    entity_filters = [e for e in entity_filters if e]
    
    # Deduplicate while preserving order
    seen_entities = set()
    deduped_entities = []
    for eid in entity_filters:
        if eid not in seen_entities:
            deduped_entities.append(eid)
            seen_entities.add(eid)
    entity_filters = deduped_entities
    
    domain_filters = _normalize_list(domains)
    if domain:
        domain_filters.append(domain.strip())
    domain_filters = [d.lower() for d in domain_filters]
    
    event_filters = _normalize_list(event_types)
    if event_type:
        event_filters.append(event_type.strip())
    event_filters = [e.lower() for e in event_filters]
    
    search_text = search.lower() if search else None
    
    try:
        if entity_filters:
            tasks = [
                ha_client.get_logbook_entries(start_iso, end_iso, entity)
                for entity in entity_filters
            ]
            results = await asyncio.gather(*tasks)
            raw_entries = [entry for batch in results for entry in batch]
        else:
            raw_entries = await ha_client.get_logbook_entries(start_iso, end_iso, None)
    except Exception as e:
        logger.error(f"Failed to fetch logbook entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    filtered_entries = []
    for entry in raw_entries:
        entry_domain = (entry.get('domain') or '').lower()
        entry_event = (entry.get('event_type') or '').lower()
        
        if domain_filters and entry_domain not in domain_filters:
            continue
        if event_filters and entry_event not in event_filters:
            continue
        if search_text:
            text_fields = [
                entry.get('message', ''),
                entry.get('name', ''),
                entry.get('entity_id', '')
            ]
            if not any(search_text in (field or '').lower() for field in text_fields):
                continue
        
        filtered_entries.append(entry)
    
    # Sort newest first
    filtered_entries.sort(key=lambda e: e.get('when', ''), reverse=True)
    limited_entries = filtered_entries[:limit]
    
    domain_counter = Counter(entry.get('domain', 'unknown') for entry in limited_entries)
    entity_counter = Counter(entry.get('entity_id', 'unknown') for entry in limited_entries)
    event_counter = Counter(entry.get('event_type', 'unknown') for entry in limited_entries)
    
    script_overview = _build_run_overview(limited_entries, 'script')
    automation_overview = _build_run_overview(limited_entries, 'automation')
    
    return {
        "success": True,
        "total_matches": len(filtered_entries),
        "count": len(limited_entries),
        "window": {
            "start": start_iso,
            "end": end_iso,
            "lookback_minutes": lookback_minutes if not start_time else None
        },
        "filters": {
            "entities": entity_filters,
            "domains": domain_filters,
            "event_types": event_filters,
            "search": search_text
        },
        "summary": {
            "domains": _counter_to_list(domain_counter),
            "entities": _counter_to_list(entity_counter),
            "event_types": _counter_to_list(event_counter),
            "scripts": script_overview,
            "automations": automation_overview
        },
        "entries": limited_entries
    }









