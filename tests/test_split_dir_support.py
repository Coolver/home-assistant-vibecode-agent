"""Tests for split directory support (automations/ and scripts/ directories).

Validates that the MCP server correctly reads automations and scripts
from split YAML directories using !include_dir_merge_list and
!include_dir_merge_named patterns.
"""
import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import yaml


# ─── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def config_dir(tmp_path):
    """Create a temporary config directory with split automation/script files."""
    # automations.yaml (empty, as in user's real config)
    (tmp_path / "automations.yaml").write_text("[]")

    # automations/ directory with domain-specific files
    automations_dir = tmp_path / "automations"
    automations_dir.mkdir()

    (automations_dir / "security.yaml").write_text(yaml.dump([
        {"id": "alarm_triggered", "alias": "Alarm Triggered", "triggers": [{"trigger": "state"}], "actions": [{"service": "notify.all"}]},
        {"id": "motion_detected", "alias": "Motion Detected", "triggers": [{"trigger": "state"}], "actions": [{"service": "light.turn_on"}]},
    ]))

    (automations_dir / "lighting.yaml").write_text(yaml.dump([
        {"id": "sunset_lights", "alias": "Sunset Lights", "triggers": [{"trigger": "sun"}], "actions": [{"service": "light.turn_on"}]},
    ]))

    # scripts.yaml (empty)
    (tmp_path / "scripts.yaml").write_text("{}")

    # scripts/ directory with named dict files
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()

    (scripts_dir / "notify_engine.yaml").write_text(yaml.dump({
        "notify_engine": {"alias": "Notification Engine", "sequence": [{"service": "notify.mobile"}], "mode": "parallel"},
    }))

    (scripts_dir / "covers.yaml").write_text(yaml.dump({
        "close_covers_safely": {"alias": "Close Covers Safely", "sequence": [{"service": "cover.close_cover"}]},
        "open_covers": {"alias": "Open Covers", "sequence": [{"service": "cover.open_cover"}]},
    }))

    # .storage directory (empty storage files)
    storage_dir = tmp_path / ".storage"
    storage_dir.mkdir()
    (storage_dir / "automation.storage").write_text(json.dumps({"data": {"automations": []}}))
    (storage_dir / "script.storage").write_text(json.dumps({"data": {"scripts": {}}}))

    # packages/ directory (empty, no automations)
    (tmp_path / "packages").mkdir()

    return tmp_path


@pytest.fixture
def mock_ws_client():
    """Mock WebSocket client returning entity registry entries."""
    ws = AsyncMock()
    ws.get_entity_registry_list = AsyncMock(return_value=[
        {"entity_id": "automation.alarm_triggered", "disabled_by": None},
        {"entity_id": "automation.motion_detected", "disabled_by": None},
        {"entity_id": "automation.sunset_lights", "disabled_by": None},
        {"entity_id": "script.notify_engine", "disabled_by": None},
        {"entity_id": "script.close_covers_safely", "disabled_by": None},
        {"entity_id": "script.open_covers", "disabled_by": None},
    ])
    ws.call_service = AsyncMock()
    ws.remove_entity_registry_entry = AsyncMock()
    return ws


@pytest.fixture
def mock_file_manager(config_dir):
    """Mock file_manager with real config_path."""
    fm = MagicMock()
    fm.config_path = config_dir

    async def read_file(path, suppress_not_found_logging=False):
        full_path = config_dir / path
        if not full_path.exists():
            if suppress_not_found_logging:
                raise FileNotFoundError(path)
            raise FileNotFoundError(path)
        return full_path.read_text(encoding="utf-8")

    async def write_file(path, content, create_backup=False):
        full_path = config_dir / path
        full_path.write_text(content, encoding="utf-8")

    fm.read_file = AsyncMock(side_effect=read_file)
    fm.write_file = AsyncMock(side_effect=write_file)
    return fm


# ─── Helpers ────────────────────────────────────────────────────────


def _patch_deps(mock_ws_client, mock_file_manager):
    """Return a combined patch context for ha_client dependencies."""
    return [
        patch("app.services.ha_websocket.get_ws_client", return_value=mock_ws_client),
        patch("app.services.file_manager.file_manager", mock_file_manager),
    ]


# ─── Automation Tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_automations_finds_split_dir(config_dir, mock_ws_client, mock_file_manager):
    """list_automations() should find automations from automations/ directory."""
    from app.services.ha_client import HomeAssistantClient

    client = HomeAssistantClient(token="test")
    patches = _patch_deps(mock_ws_client, mock_file_manager)

    for p in patches:
        p.start()
    try:
        result = await client.list_automations()
    finally:
        for p in patches:
            p.stop()

    ids = {a.get("id") for a in result if isinstance(a, dict)}
    assert "alarm_triggered" in ids
    assert "motion_detected" in ids
    assert "sunset_lights" in ids
    assert len(result) == 3


@pytest.mark.asyncio
async def test_list_automations_ids_only(config_dir, mock_ws_client, mock_file_manager):
    """list_automations(ids_only=True) should return IDs from automations/ directory."""
    from app.services.ha_client import HomeAssistantClient

    client = HomeAssistantClient(token="test")
    patches = _patch_deps(mock_ws_client, mock_file_manager)

    for p in patches:
        p.start()
    try:
        result = await client.list_automations(ids_only=True)
    finally:
        for p in patches:
            p.stop()

    assert "alarm_triggered" in result
    assert "sunset_lights" in result


@pytest.mark.asyncio
async def test_get_automation_from_split_dir(config_dir, mock_ws_client, mock_file_manager):
    """get_automation() should find an automation in automations/ directory."""
    from app.services.ha_client import HomeAssistantClient

    client = HomeAssistantClient(token="test")
    patches = _patch_deps(mock_ws_client, mock_file_manager)

    for p in patches:
        p.start()
    try:
        result = await client.get_automation("alarm_triggered")
    finally:
        for p in patches:
            p.stop()

    assert result["id"] == "alarm_triggered"
    assert result["alias"] == "Alarm Triggered"


@pytest.mark.asyncio
async def test_find_automation_location_split_dir(config_dir, mock_ws_client, mock_file_manager):
    """_find_automation_location() should return automations_dir location."""
    from app.services.ha_client import HomeAssistantClient

    client = HomeAssistantClient(token="test")
    patches = _patch_deps(mock_ws_client, mock_file_manager)

    for p in patches:
        p.start()
    try:
        result = await client._find_automation_location("sunset_lights")
    finally:
        for p in patches:
            p.stop()

    assert result is not None
    assert result["location"] == "automations_dir"
    assert "lighting.yaml" in result["file_path"]
    assert result["format"] == "list"


@pytest.mark.asyncio
async def test_delete_automation_from_split_dir(config_dir, mock_ws_client, mock_file_manager):
    """delete_automation() should remove automation from automations/ file."""
    from app.services.ha_client import HomeAssistantClient

    client = HomeAssistantClient(token="test")
    patches = _patch_deps(mock_ws_client, mock_file_manager)

    for p in patches:
        p.start()
    try:
        result = await client.delete_automation("sunset_lights")
    finally:
        for p in patches:
            p.stop()

    assert result["success"] is True

    # Verify the file no longer contains the automation
    content = (config_dir / "automations" / "lighting.yaml").read_text()
    data = yaml.safe_load(content)
    ids = [a.get("id") for a in (data or [])]
    assert "sunset_lights" not in ids


# ─── Script Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_scripts_finds_split_dir(config_dir, mock_ws_client, mock_file_manager):
    """list_scripts() should find scripts from scripts/ directory."""
    from app.services.ha_client import HomeAssistantClient

    client = HomeAssistantClient(token="test")
    patches = _patch_deps(mock_ws_client, mock_file_manager)

    for p in patches:
        p.start()
    try:
        result = await client.list_scripts()
    finally:
        for p in patches:
            p.stop()

    assert "notify_engine" in result
    assert "close_covers_safely" in result
    assert "open_covers" in result
    assert result["notify_engine"]["alias"] == "Notification Engine"


@pytest.mark.asyncio
async def test_get_script_from_split_dir(config_dir, mock_ws_client, mock_file_manager):
    """get_script() should find a script in scripts/ directory."""
    from app.services.ha_client import HomeAssistantClient

    client = HomeAssistantClient(token="test")
    patches = _patch_deps(mock_ws_client, mock_file_manager)

    for p in patches:
        p.start()
    try:
        result = await client.get_script("notify_engine")
    finally:
        for p in patches:
            p.stop()

    assert result["alias"] == "Notification Engine"
    assert result["mode"] == "parallel"


@pytest.mark.asyncio
async def test_find_script_location_split_dir(config_dir, mock_ws_client, mock_file_manager):
    """_find_script_location() should return scripts_dir location."""
    from app.services.ha_client import HomeAssistantClient

    client = HomeAssistantClient(token="test")
    patches = _patch_deps(mock_ws_client, mock_file_manager)

    for p in patches:
        p.start()
    try:
        result = await client._find_script_location("close_covers_safely")
    finally:
        for p in patches:
            p.stop()

    assert result is not None
    assert result["location"] == "scripts_dir"
    assert "covers.yaml" in result["file_path"]


@pytest.mark.asyncio
async def test_delete_script_from_split_dir(config_dir, mock_ws_client, mock_file_manager):
    """delete_script() should remove script from scripts/ file."""
    from app.services.ha_client import HomeAssistantClient

    client = HomeAssistantClient(token="test")
    patches = _patch_deps(mock_ws_client, mock_file_manager)

    for p in patches:
        p.start()
    try:
        result = await client.delete_script("open_covers")
    finally:
        for p in patches:
            p.stop()

    assert result["success"] is True

    # Verify the file no longer contains the script
    content = (config_dir / "scripts" / "covers.yaml").read_text()
    data = yaml.safe_load(content)
    assert "open_covers" not in data
    assert "close_covers_safely" in data  # other script should remain


# ─── Edge Case Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_automations_dir_graceful(tmp_path, mock_ws_client):
    """If automations/ directory doesn't exist, list_automations should not fail."""
    from app.services.ha_client import HomeAssistantClient

    # Minimal config: only automations.yaml, no automations/ dir
    (tmp_path / "automations.yaml").write_text("[]")
    storage_dir = tmp_path / ".storage"
    storage_dir.mkdir()
    (storage_dir / "automation.storage").write_text(json.dumps({"data": {"automations": []}}))

    fm = MagicMock()
    fm.config_path = tmp_path

    async def read_file(path, suppress_not_found_logging=False):
        full_path = tmp_path / path
        if not full_path.exists():
            raise FileNotFoundError(path)
        return full_path.read_text(encoding="utf-8")

    fm.read_file = AsyncMock(side_effect=read_file)

    # Empty entity registry
    mock_ws_client.get_entity_registry_list = AsyncMock(return_value=[])

    client = HomeAssistantClient(token="test")
    patches = _patch_deps(mock_ws_client, fm)

    for p in patches:
        p.start()
    try:
        result = await client.list_automations()
    finally:
        for p in patches:
            p.stop()

    assert result == []


@pytest.mark.asyncio
async def test_malformed_yaml_in_split_dir_skipped(config_dir, mock_ws_client, mock_file_manager):
    """Malformed YAML files in automations/ should be skipped gracefully."""
    from app.services.ha_client import HomeAssistantClient

    # Add a malformed file
    (config_dir / "automations" / "broken.yaml").write_text("{{{{invalid yaml")

    client = HomeAssistantClient(token="test")
    patches = _patch_deps(mock_ws_client, mock_file_manager)

    for p in patches:
        p.start()
    try:
        result = await client.list_automations()
    finally:
        for p in patches:
            p.stop()

    # Should still return the valid automations
    ids = {a.get("id") for a in result if isinstance(a, dict)}
    assert "alarm_triggered" in ids
    assert "sunset_lights" in ids
