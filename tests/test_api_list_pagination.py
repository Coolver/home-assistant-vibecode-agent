"""Tests for paginated list endpoints in automations/scripts APIs."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_automations_list_pagination_and_search():
    from app.api import automations as automations_api

    data = [
        {"id": f"auto_{idx}", "alias": f"Automation {idx}"}
        for idx in range(300)
    ]
    data.append({"id": "kitchen_evening", "alias": "Kitchen Evening Lights"})

    with patch.object(automations_api.ha_client, "list_automations", AsyncMock(return_value=data)):
        result = await automations_api.list_automations(search="kitchen", page=1, page_size=250, full_list=False)

    assert result["success"] is True
    assert result["total"] == 1
    assert result["count"] == 1
    assert result["automations"][0]["id"] == "kitchen_evening"
    assert result["has_next"] is False


@pytest.mark.asyncio
async def test_automations_list_ids_only_pagination():
    from app.api import automations as automations_api

    ids = [f"auto_{idx}" for idx in range(305)]
    with patch.object(automations_api.ha_client, "list_automations", AsyncMock(return_value=ids)):
        result = await automations_api.list_automations(ids_only=True, page=2, page_size=250, full_list=False)

    assert result["success"] is True
    assert result["total"] == 305
    assert result["count"] == 55
    assert len(result["automation_ids"]) == 55
    assert result["has_next"] is False


@pytest.mark.asyncio
async def test_scripts_list_full_list_mode():
    from app.api import scripts as scripts_api

    scripts = {
        "script_one": {"alias": "Script One"},
        "script_two": {"alias": "Script Two"},
    }
    with patch.object(scripts_api.ha_client, "list_scripts", AsyncMock(return_value=scripts)):
        result = await scripts_api.list_scripts(ids_only=False, full_list=True)

    assert result["success"] is True
    assert result["total"] == 2
    assert result["count"] == 2
    assert sorted(result["scripts"].keys()) == ["script_one", "script_two"]
