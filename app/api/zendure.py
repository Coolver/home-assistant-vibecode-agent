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
async def get_zendure_devices(all_states: Optional[List[Dict]] = None):
    """
    Get all Zendure devices and their aggregated energy data.

    Automatically discovers all Zendure-related entities from Home Assistant
    and groups them by device. Returns per-device and fleet-wide totals.

    **Returns:**
    - List of devices with available_kwh, total_kwh, soc, solar_input_power, etc.
    - Fleet summary: total capacity, available energy, overall SoC, total solar/output power
    """
    if all_states is None:
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
async def get_zendure_status(all_states: Optional[List[Dict]] = None):
    """
    Quick Zendure fleet status snapshot.

    Returns a concise status overview useful for dashboard or quick diagnostics:
    - Fleet SoC, available energy, total capacity
    - Current solar production, house output, battery charging power
    - Manager entity states (Zendure Manager Power, Operation State, etc.)
    - Any entities in unknown/unavailable state (for debugging)
    """
    if all_states is None:
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

    Fetches HA states exactly once and passes them to sub-functions to avoid
    redundant API calls. Combines /zendure/devices + /zendure/status + logs.
    """
    import os

    # --- Single get_states() call shared across all sub-functions ---
    try:
        all_states = await ha_client.get_states()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch HA states: {e}")

    # --- Devices + Fleet (pass shared states to avoid 2nd API call) ---
    devices_result = await get_zendure_devices(all_states=all_states)
    device_summary = [
        {
            "device_id": dev["device_id"],
            "available_kwh": dev.get("available_kwh"),
            "total_kwh": dev.get("total_kwh"),
            "soc_pct": dev.get("soc_pct"),
            "solar_w": dev.get("solar_input_w"),
            "output_w": dev.get("output_home_w"),
            "pack_input_w": dev.get("pack_input_w"),
            "status": dev.get("status"),
        }
        for dev in devices_result.get("devices", [])
    ]
    fleet = devices_result.get("fleet", {})
    fleet_avail = fleet.get("available_kwh", 0.0)
    fleet_total = fleet.get("total_capacity_kwh", 0.0)
    fleet_soc = fleet.get("soc_pct", 0.0)

    # --- Manager entities (pass shared states to avoid 3rd API call) ---
    status_result = await get_zendure_status(all_states=all_states)
    manager_states = {
        e["entity_id"]: e["state"]
        for e in status_result.get("manager_entities", [])
    }

    # --- Log tail (Zendure-filtered) ---
    log_lines = []
    log_source = "unavailable"

    SUPERVISOR_TOKEN = os.environ.get('SUPERVISOR_TOKEN', '')
    if SUPERVISOR_TOKEN:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://supervisor/host/logs/homeassistant/entries",
                    headers={
                        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
                        "Accept": "text/plain",
                        "Range": "entries=:-2000:2000",
                    },
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        log_lines = [l for l in text.splitlines() if "zendure" in l.lower()][-50:]
                        log_source = "supervisor_host_logs"
        except Exception as e:
            logger.debug(f"Supervisor logs unavailable: {e}")

    if not log_lines:
        try:
            from app.services.ha_websocket import get_ws_client
            ws = await get_ws_client()
            entries = await ws._send_message({'type': 'system_log/list'}, timeout=15.0)
            if isinstance(entries, list):
                for e in entries:
                    name = e.get('name', '')
                    messages = e.get('message', [])
                    msg = ' | '.join(messages) if isinstance(messages, list) else str(messages)
                    if 'zendure' in name.lower() or 'zendure' in msg.lower():
                        ts = e.get('timestamp', '')
                        level = e.get('level', 'unknown').upper()
                        count = e.get('count', 1)
                        suffix = f" (x{count})" if count > 1 else ""
                        log_lines.append(f"{ts} {level} {name} {msg}{suffix}")
                if log_lines:
                    log_source = "websocket_system_log"
        except Exception as e:
            logger.warning(f"WebSocket system_log fetch failed in diagnostics: {e}")

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


@router.get("/socfull_alert")
async def get_socfull_alert():
    """
    Detect the 'SoC=100% + Bypass Forbidden + Output cycling to 0W' bug (Issue #1151).

    This is a known bug in Zendure-HA manager.py where once a device reaches 100% SoC
    and bypass is forbidden, the power output cycles between 0 and the setpoint instead
    of holding steady. The root cause is in the discharge_bypass calculation in
    powerChanged(): when state==SOCFULL, pwr_produced is subtracted from setpoint,
    which can flip the sign and incorrectly trigger charge logic.

    **What this endpoint detects:**
    - Devices at or above socSet (100% or configured max SoC)
    - Low/zero output despite active solar input (indicating the cycling bug)
    - Manager in MATCHING mode (smart/auto) where the bug occurs

    **Returns:**
    - alert: bool — True if the issue is likely active
    - affected_devices: list of devices showing the symptom
    - recommendation: string with the suggested action
    - workaround_active: bool — True if a manual power override is currently set

    **Community note (GitHub Issue #1151):**
    Workaround until upstream fix: Switch to MANUAL mode with a fixed output_limit,
    or use 'store_solar' mode. The CT/App workaround (running Zendure CT mode in the
    app alongside the integration) also suppresses the symptom.
    """
    try:
        all_states = await ha_client.get_states()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch HA states: {e}")

    state_map = {s["entity_id"]: s for s in all_states}

    def _get(entity_id: str) -> Optional[float]:
        s = state_map.get(entity_id)
        if s and s["state"] not in ("unknown", "unavailable", None):
            return _safe_float(s["state"])
        return None

    # Get manager operation mode
    manager_op = None
    for s in all_states:
        if "zendure_manager" in s["entity_id"] and "operation" in s["entity_id"] and s["entity_id"].startswith("select."):
            manager_op = s["state"]
            break

    manager_manual_power = _get("number.zendure_manager_manual_power")

    # Find all device prefixes from known sensors
    device_prefixes: set = set()
    for s in all_states:
        prefix = _extract_device_prefix(s["entity_id"])
        if prefix and prefix not in ("gesamt", "zendure_manager"):
            device_prefixes.add(prefix)

    affected_devices = []
    all_full_devices = []

    for prefix in sorted(device_prefixes):
        soc = _get(f"sensor.{prefix}_electric_level")
        soc_set = _get(f"sensor.{prefix}_soc_set") or _get(f"number.{prefix}_soc_set") or 100.0
        solar_w = _get(f"sensor.{prefix}_solar_input_power")
        output_w = _get(f"sensor.{prefix}_output_home_power")
        pack_input_w = _get(f"sensor.{prefix}_pack_input_power")

        if soc is None:
            continue

        is_full = soc >= (soc_set - 2)  # 2% tolerance

        if is_full:
            all_full_devices.append(prefix)

        # Bug symptom: device is full, has solar input, but output is near zero
        # while manager is in smart mode (not manual, not off)
        if (
            is_full
            and solar_w is not None and solar_w > 20
            and output_w is not None and output_w < 30
            and manager_op in ("smart", "smart_charging", "smart_discharging", "store_solar")
        ):
            affected_devices.append({
                "device_id": prefix,
                "soc_pct": soc,
                "soc_set": soc_set,
                "solar_input_w": solar_w,
                "output_home_w": output_w,
                "pack_input_w": pack_input_w,
                "symptom": "SoC=100%, solar active, output near 0W — likely cycling bug",
            })

    alert = len(affected_devices) > 0
    workaround_active = manager_op == "manual" or (manager_manual_power is not None and manager_manual_power != 0)

    if alert:
        recommendation = (
            "Issue #1151 detected. Workarounds (until upstream fix in Zendure-HA):\n"
            "1. Switch manager to 'manual' mode with a fixed output limit (e.g. 300W) — "
            "requires an automation to track home consumption.\n"
            "2. Switch to 'store_solar' mode — reduces output cycling but may not fully eliminate it.\n"
            "3. Enable CT mode on one device via the Zendure app (community workaround).\n"
            "Upstream fix needed in manager.py powerChanged(): discharge_bypass logic "
            "incorrectly flips setpoint sign for SOCFULL devices with no bypass."
        )
    elif all_full_devices:
        recommendation = (
            f"Devices at full SoC: {', '.join(all_full_devices)}. "
            "No active output cycling detected currently, but monitor for Issue #1151 symptoms "
            "if solar input increases and output drops to 0W."
        )
    else:
        recommendation = "No devices at full SoC. Issue #1151 not applicable right now."

    return {
        "success": True,
        "alert": alert,
        "manager_operation": manager_op,
        "workaround_active": workaround_active,
        "devices_at_full_soc": all_full_devices,
        "affected_devices": affected_devices,
        "recommendation": recommendation,
        "issue_reference": "https://github.com/Zendure/Zendure-HA/issues/1151",
        "root_cause": (
            "manager.py powerChanged(): when state==SOCFULL, discharge_bypass subtracts "
            "pwr_produced from setpoint (line ~425). If pwr_produced is small or zero, "
            "this can flip setpoint negative, triggering charge logic instead of discharge, "
            "causing output to cycle to 0W."
        ),
    }
