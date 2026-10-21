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


@pytest.mark.parametrize("result", [None, [], {}, {"success": False, "error": "Application payload"}])
def test_successful_result_is_returned_unchanged(result):
    client = responding_client({"success": True, "result": result})

    assert asyncio.run(client.update_entity_registry("sensor.example", name="Example")) == result
    assert client.pending_requests == {}
