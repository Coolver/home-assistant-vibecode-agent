"""Zendure integration API - aggregated device data and diagnostics"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging
import re

from app.services.ha_client import ha_client

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')

# Known Zendure device entity suffixes and what they represent
ZENDURE_SENSOR_MAP = {
    "available_kwh": {"label": "Verfügbare Energie", "unit": "kWh", "role": "energy_available"},
    "total_kwh": {"label": "Gesamtkapazität", "unit": "kWh", "role": "energy_total"},
    "soc": {"label": "SoC", "unit": "%", "role": "soc"},
    "output_home_power": {"label": "Ausgangsleistung Haus", "unit": "W", "role": "power_out"},
    "pack_input_power": {"label": "Eingangsleistung Batterie", "unit": "W", "role": "power_in"},
    "solar_input_power": {"label": "Solarleistung", "unit": "W", "role": "solar"},
    "output_limit": {"label": "Ausgangslimit", "unit": "W", "role": "limit"},
    "input_limit": {"label": "Eingangslimit", "unit": "W", "role": "limit_in"},
    "pack_num": {"label": "Anzahl Akkupacks", "unit": "", "role": "info"},
    "electric_level": {"label": "Ladestand", "unit": "%", "role": "soc"},
}


def _safe_float(val) -> Optional[float]:
    try:
        f = float(val)
        if f != f:  # nan check
            return None
        return f
    except (TypeError, ValueError):
        return None


def _extract_device_prefix(entity_id: str) -> Optional[str]:
    """Extract device prefix from entity like sensor.hyper2000_618_available_kwh -> hyper2000_618"""
    # Remove domain prefix
    name = entity_id.split(".", 1)[-1]
    # Remove known suffixes
    for suffix in ZENDURE_SENSOR_MAP:
        if name.endswith(f"_{suffix}"):
            return name[: -(len(suffix) + 1)]
    return None


@router.get("/devices")
async def get_zendure_devices():
    """
    Get all Zendure devices and their aggregated energy data.

    Automatically discovers all Zendure-related entities from Home Assistant
    and groups them by device. Returns per-device and fleet-wide totals.

    **Returns:**
    - List of devices with available_kwh, total_kwh, soc, solar_input_power, etc.
    - Fleet summary: total capacity, available energy, overall SoC, total solar/output power
    """
    try:
        all_states = await ha_client.get_states()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch HA states: {e}")

    # Find all Zendure-related sensors
    zendure_states = [
        s for s in all_states
        if "zendure" in s.get("attributes", {}).get("friendly_name", "").lower()
        or any(
            s["entity_id"].split(".", 1)[-1].endswith(f"_{sfx}")
            for sfx in ZENDURE_SENSOR_MAP
            if s["entity_id"].startswith("sensor.")
        )
    ]

    # Group by device prefix
    devices: Dict[str, Dict[str, Any]] = {}

    for state in zendure_states:
        entity_id = state["entity_id"]
        prefix = _extract_device_prefix(entity_id)
        if not prefix:
            continue

        if prefix not in devices:
            devices[prefix] = {
                "device_id": prefix,
                "friendly_name": state.get("attributes", {}).get("friendly_name", "").rsplit(" ", 1)[0],
                "sensors": {},
            }

        # Find which sensor this is
        name_part = entity_id.split(".", 1)[-1]
        for suffix, meta in ZENDURE_SENSOR_MAP.items():
            if name_part.endswith(f"_{suffix}"):
                devices[prefix]["sensors"][suffix] = {
                    "entity_id": entity_id,
                    "value": _safe_float(state["state"]) if state["state"] not in ("unknown", "unavailable") else None,
                    "raw_state": state["state"],
                    "unit": meta["unit"],
                    "label": meta["label"],
                    "role": meta["role"],
                }
                break

    # Build clean device list with derived fields
    device_list = []
    fleet_available = 0.0
    fleet_total = 0.0
    fleet_solar = 0.0
    fleet_output = 0.0
    fleet_input = 0.0

    for prefix, dev in devices.items():
        sensors = dev["sensors"]

        avail = (sensors.get("available_kwh") or {}).get("value")
        total = (sensors.get("total_kwh") or {}).get("value")
        soc_raw = (sensors.get("soc") or sensors.get("electric_level") or {}).get("value")
        solar = (sensors.get("solar_input_power") or {}).get("value")
        output = (sensors.get("output_home_power") or {}).get("value")
        pack_in = (sensors.get("pack_input_power") or {}).get("value")
        pack_num = (sensors.get("pack_num") or {}).get("value")

        # Derive SoC from available/total if not directly available
        computed_soc = None
        if avail is not None and total and total > 0:
            computed_soc = round(avail / total * 100, 1)
        elif soc_raw is not None:
            computed_soc = soc_raw

        device_entry = {
            "device_id": prefix,
            "friendly_name": dev["friendly_name"],
            "available_kwh": avail,
            "total_kwh": total,
            "soc_pct": computed_soc,
            "pack_count": int(pack_num) if pack_num is not None else None,
            "solar_input_w": solar,
            "output_home_w": output,
            "pack_input_w": pack_in,
            "status": "ok" if avail is not None else "unavailable",
            "sensors": sensors,
        }
        device_list.append(device_entry)

        if avail is not None:
            fleet_available += avail
        if total is not None:
            fleet_total += total
        if solar is not None:
            fleet_solar += solar
        if output is not None:
            fleet_output += output
        if pack_in is not None:
            fleet_input += pack_in

    fleet_soc = round(fleet_available / fleet_total * 100, 1) if fleet_total > 0 else 0.0

    # Sort devices by device_id
    device_list.sort(key=lambda d: d["device_id"])

    return {
        "success": True,
        "device_count": len(device_list),
        "devices": device_list,
        "fleet": {
            "total_capacity_kwh": round(fleet_total, 2),
            "available_kwh": round(fleet_available, 2),
            "soc_pct": fleet_soc,
            "solar_input_w": round(fleet_solar, 0),
            "output_home_w": round(fleet_output, 0),
            "pack_input_w": round(fleet_input, 0),
        },
    }


@router.get("/status")
async def get_zendure_status():
    """
    Quick Zendure fleet status snapshot.

    Returns a concise status overview useful for dashboard or quick diagnostics:
    - Fleet SoC, available energy, total capacity
    - Current solar production, house output, battery charging power
    - Manager entity states (Zendure Manager Power, Operation State, etc.)
    - Any entities in unknown/unavailable state (for debugging)
    """
    try:
        all_states = await ha_client.get_states()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch HA states: {e}")

    # Collect all zendure entities
    zendure_entities = [
        s for s in all_states
        if s["entity_id"].startswith("sensor.zendure_")
        or s["entity_id"].startswith("select.zendure_")
        or s["entity_id"].startswith("number.zendure_")
        or "zendure_manager" in s["entity_id"]
    ]

    # Manager entities specifically
    manager_entities = [s for s in zendure_entities if "zendure_manager" in s["entity_id"]]

    # Custom template sensors we created
    template_sensor_ids = [
        "sensor.batterie_energieinhalt",
        "sensor.batterie_gesamtkapazitat",
        "sensor.batterie_soc_gesamt",
        "sensor.gesamt_solarleistung",
        "sensor.gesamt_output_home_power",
        "sensor.netz_leistung_gesamt_w",
        "sensor.zendure_log_tail",
    ]

    template_sensors = {}
    for tid in template_sensor_ids:
        for s in all_states:
            if s["entity_id"] == tid:
                template_sensors[tid.split(".", 1)[-1]] = {
                    "state": s["state"],
                    "unit": s.get("attributes", {}).get("unit_of_measurement", ""),
                    "last_updated": s.get("last_updated"),
                }
                break

    # Entities that are unknown/unavailable
    unavailable = [
        {"entity_id": s["entity_id"], "state": s["state"]}
        for s in zendure_entities
        if s["state"] in ("unknown", "unavailable")
    ]

    return {
        "success": True,
        "manager_entities": [
            {
                "entity_id": s["entity_id"],
                "state": s["state"],
                "unit": s.get("attributes", {}).get("unit_of_measurement", ""),
                "friendly_name": s.get("attributes", {}).get("friendly_name", ""),
                "last_updated": s.get("last_updated"),
            }
            for s in manager_entities
        ],
        "template_sensors": template_sensors,
        "unavailable_entities": unavailable,
        "unavailable_count": len(unavailable),
        "total_zendure_entities": len(zendure_entities),
    }


@router.get("/diagnostics")
async def get_zendure_diagnostics():
    """
    Full Zendure diagnostics — device data + log tail + status in one call.

    Combines /zendure/devices + /zendure/status + latest log lines.
    Ideal for the Cursor agent to get a complete picture in a single request.
    """
    import aiohttp
    import os

    HA_URL = ha_client.url
    SUPERVISOR_TOKEN = os.environ.get('SUPERVISOR_TOKEN', '')

    # Get devices and status in parallel
    try:
        all_states = await ha_client.get_states()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch HA states: {e}")

    # --- Devices (reuse logic from /devices) ---
    zendure_states = [
        s for s in all_states
        if any(
            s["entity_id"].split(".", 1)[-1].endswith(f"_{sfx}")
            for sfx in ZENDURE_SENSOR_MAP
            if s["entity_id"].startswith("sensor.")
        )
    ]
    devices: Dict[str, Dict] = {}
    for state in zendure_states:
        entity_id = state["entity_id"]
        prefix = _extract_device_prefix(entity_id)
        if not prefix:
            continue
        if prefix not in devices:
            devices[prefix] = {"device_id": prefix, "sensors": {}}
        name_part = entity_id.split(".", 1)[-1]
        for suffix in ZENDURE_SENSOR_MAP:
            if name_part.endswith(f"_{suffix}"):
                val = _safe_float(state["state"]) if state["state"] not in ("unknown", "unavailable") else None
                devices[prefix]["sensors"][suffix] = val
                break

    device_summary = []
    fleet_avail = 0.0
    fleet_total = 0.0
    for prefix, dev in sorted(devices.items()):
        s = dev["sensors"]
        avail = s.get("available_kwh")
        total = s.get("total_kwh")
        soc = round(avail / total * 100, 1) if avail is not None and total else None
        device_summary.append({
            "device_id": prefix,
            "available_kwh": avail,
            "total_kwh": total,
            "soc_pct": soc,
            "solar_w": s.get("solar_input_power"),
            "output_w": s.get("output_home_power"),
        })
        if avail:
            fleet_avail += avail
        if total:
            fleet_total += total

    fleet_soc = round(fleet_avail / fleet_total * 100, 1) if fleet_total > 0 else 0.0

    # --- Manager entities ---
    manager_states = {
        s["entity_id"]: s["state"]
        for s in all_states
        if "zendure_manager" in s["entity_id"]
    }

    # --- Log tail ---
    log_lines = []
    log_source = "unavailable"
    if SUPERVISOR_TOKEN:
        try:
            headers = {
                "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
                "Accept": "text/plain",
                "Range": "entries=:-2000:2000",
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://supervisor/host/logs/homeassistant/entries",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        all_lines = text.splitlines()
                        log_lines = [l for l in all_lines if "zendure" in l.lower()][-50:]
                        log_source = "supervisor_host_logs"
                    else:
                        logger.warning(f"Supervisor host/logs returned {resp.status}")
        except Exception as e:
            logger.warning(f"Could not fetch logs for diagnostics: {e}")

    errors = [l for l in log_lines if "ERROR" in l]
    warnings = [l for l in log_lines if "WARNING" in l]

    return {
        "success": True,
        "fleet": {
            "available_kwh": round(fleet_avail, 2),
            "total_capacity_kwh": round(fleet_total, 2),
            "soc_pct": fleet_soc,
        },
        "devices": device_summary,
        "manager": manager_states,
        "logs": {
            "source": log_source,
            "total_zendure_lines": len(log_lines),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "recent_errors": errors[-5:],
            "recent_warnings": warnings[-5:],
            "recent_lines": log_lines[-20:],
        },
    }
