"""WebSocket command results follow Home Assistant's outer response envelope."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.ha_websocket import HAWebSocketClient


def responding_client(response):
    client = HAWebSocketClient("http://localhost:8123", "test-token")
    client._connected = True

    async def send_json(message):
        await client._handle_message({"id": message["id"], "type": "result", **response})

    client.ws = SimpleNamespace(closed=False, send_json=AsyncMock(side_effect=send_json))
    return client


@pytest.mark.parametrize("error, message", [
    ({"code": "not_allowed", "message": "Entity cannot be disabled"}, "not_allowed - Entity cannot be disabled"),
    ("Command rejected", "unknown_error - Command rejected"),
    (None, "unknown_error - None"),
])
def test_command_error_rejects_pending_request(error, message):
    client = responding_client({"success": False, "error": error})

    with pytest.raises(Exception, match=message):
        asyncio.run(client.update_entity_registry("sensor.example", name="Example"))

    assert client.pending_requests == {}


def test_hacs_remove_sends_the_repository_id():
    client = responding_client({"success": True, "result": {}})

    asyncio.run(client.remove_hacs_repository("445678"))

    sent = client.ws.send_json.call_args.args[0]
    assert sent["type"] == "hacs/repository/remove"
    assert sent["repository"] == "445678"


def test_call_service_can_ask_for_the_return_value():
    client = responding_client({"success": True, "result": {
        "context": {"id": "ctx"},
        "response": {"weather.home": {"forecast": [{"temperature": 12}]}},
    }})

    result = asyncio.run(client.call_service(
        "weather",
        "get_forecasts",
        service_data={"type": "daily"},
        target={"entity_id": "weather.home"},
        return_response=True,
    ))

    sent = client.ws.send_json.call_args.args[0]
    assert sent["type"] == "call_service"
    assert sent["return_response"] is True
    assert sent["service_data"] == {"type": "daily"}
    assert sent["target"] == {"entity_id": "weather.home"}
    assert result["response"]["weather.home"]["forecast"][0]["temperature"] == 12


def test_call_service_leaves_ordinary_calls_unchanged():
    client = responding_client({"success": True, "result": {"context": {"id": "ctx"}}})

    asyncio.run(client.call_service("light", "turn_on", {"entity_id": "light.kitchen"}))

    sent = client.ws.send_json.call_args.args[0]
    assert "return_response" not in sent


def test_list_categories_sends_scope_and_filters():
    client = responding_client({"success": True, "result": [
        {"category_id": "a", "scope": "automation", "name": "Lights"},
        {"category_id": "s", "scope": "script", "name": "House"},
    ]})

    listed = asyncio.run(client.list_categories("automation"))

    assert [item["category_id"] for item in listed] == ["a"]
    sent = client.ws.send_json.call_args.args[0]
    assert sent["type"] == "config/category_registry/list"
    assert sent["scope"] == "automation"


@pytest.mark.parametrize("result", [None, [], {}, {"success": False, "error": "Application payload"}])
def test_successful_result_is_returned_unchanged(result):
    client = responding_client({"success": True, "result": result})

    assert asyncio.run(client.update_entity_registry("sensor.example", name="Example")) == result
    assert client.pending_requests == {}
