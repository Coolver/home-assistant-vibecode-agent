"""Config entries, config/options flows, and entity registry hide/disable."""
import asyncio
import logging
import os
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("HA_TOKEN", "test-token")
os.environ.setdefault("HA_URL", "http://localhost:8123")
os.environ.setdefault("CONFIG_PATH", "/tmp/test-config")

from fastapi.testclient import TestClient

from app.auth import verify_token
from app.main import app
from app.services.ha_client import ha_client
from app.services.ha_websocket import HAWebSocketClient


@pytest.fixture
def client():
    app.dependency_overrides[verify_token] = lambda: "test"
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def ha_request():
    with patch.object(ha_client, "_request", new_callable=AsyncMock) as mock:
        yield mock


ENTRIES = [
    {"entry_id": "a1", "domain": "switch_as_x", "title": "TV", "state": "loaded",
     "source": "user", "disabled_by": None},
    {"entry_id": "b2", "domain": "zha", "title": "Yellow", "state": "loaded",
     "source": "hardware", "disabled_by": None},
]


def test_list_entries_filters_by_domain(client, ha_request):
    ha_request.return_value = ENTRIES
    response = client.get("/api/config_entries/list", params={"domain": "zha"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["entries"][0]["entry_id"] == "b2"
    ha_request.assert_awaited_once_with("GET", "config/config_entries/entry")


def test_start_flow_posts_handler(client, ha_request):
    ha_request.return_value = {"flow_id": "f1", "type": "form", "step_id": "user"}
    response = client.post("/api/config_entries/flow/start", json={"handler": "switch_as_x"})
    assert response.status_code == 200
    assert response.json()["flow"]["flow_id"] == "f1"
    ha_request.assert_awaited_once_with(
        "POST", "config/config_entries/flow",
        data={"handler": "switch_as_x", "show_advanced_options": False},
    )


def test_flow_step_sends_user_input_without_logging_values(client, ha_request):
    ha_request.return_value = {"flow_id": "f1", "type": "create_entry", "title": "TV"}
    response = client.post(
        "/api/config_entries/flow/f1",
        json={"user_input": {"entity_id": "switch.tv", "target_domain": "light"}},
    )
    assert response.status_code == 200
    ha_request.assert_awaited_once_with(
        "POST", "config/config_entries/flow/f1",
        data={"entity_id": "switch.tv", "target_domain": "light"}, redact=True,
    )


def test_abort_flow(client, ha_request):
    ha_request.return_value = {"message": "Flow aborted"}
    assert client.delete("/api/config_entries/flow/f1").status_code == 200
    ha_request.assert_awaited_once_with("DELETE", "config/config_entries/flow/f1")


def test_options_flow_start_and_step(client, ha_request):
    ha_request.return_value = {"flow_id": "o1", "type": "form"}
    assert client.post("/api/config_entries/options_flow/start",
                       json={"entry_id": "a1"}).status_code == 200
    ha_request.assert_awaited_with("POST", "config/config_entries/options/flow",
                                   data={"handler": "a1"})
    assert client.post("/api/config_entries/options_flow/o1",
                       json={"user_input": {"invert": True}}).status_code == 200
    ha_request.assert_awaited_with("POST", "config/config_entries/options/flow/o1",
                                   data={"invert": True}, redact=True)


def test_reload_entry(client, ha_request):
    ha_request.return_value = {"require_restart": False}
    assert client.post("/api/config_entries/a1/reload").status_code == 200
    ha_request.assert_awaited_once_with("POST", "config/config_entries/entry/a1/reload")


def test_delete_entry_requires_confirm(client, ha_request):
    response = client.delete("/api/config_entries/a1")
    assert response.status_code == 400
    ha_request.assert_not_awaited()


def test_delete_entry(client, ha_request):
    ha_request.return_value = {"require_restart": False}
    response = client.delete("/api/config_entries/a1", params={"confirm": True})
    assert response.status_code == 200
    ha_request.assert_awaited_once_with("DELETE", "config/config_entries/entry/a1")


def test_redacted_request_does_not_log_values(caplog):
    class FakeResponse:
        status = 200
        async def json(self): return {}
        async def text(self): return "{}"
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False

    class FakeSession:
        closed = False
        def request(self, *a, **k): return FakeResponse()

    with patch.object(ha_client, "_get_session", new=AsyncMock(return_value=FakeSession())):
        with caplog.at_level(logging.INFO, logger="ha_cursor_agent"):
            asyncio.run(ha_client._request("POST", "config/config_entries/flow/f1",
                                           data={"password": "hunter2"}, redact=True))
    assert "hunter2" not in caplog.text
    assert "password" in caplog.text


def test_redacted_error_does_not_echo_the_submitted_secret(caplog):
    class FakeResponse:
        status = 400

        async def text(self):
            return '{"message": "invalid hunter2"}'

        async def json(self):
            return {}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class FakeSession:
        closed = False

        def request(self, *a, **k):
            return FakeResponse()

    with patch.object(ha_client, "_get_session", new=AsyncMock(return_value=FakeSession())):
        with caplog.at_level(logging.INFO, logger="ha_cursor_agent"):
            with pytest.raises(Exception) as caught:
                asyncio.run(ha_client._request(
                    "POST", "config/config_entries/flow/f1",
                    data={"password": "hunter2"}, redact=True,
                ))

    assert "hunter2" not in caplog.text
    assert "hunter2" not in str(caught.value)
    assert "400" in str(caught.value)


@pytest.fixture
def ws_update():
    ws = AsyncMock()
    ws.update_entity_registry.return_value = {}
    with patch("app.api.registries.get_ws_client", new=AsyncMock(return_value=ws)):
        yield ws.update_entity_registry


@pytest.mark.parametrize("field,value", [
    ("disabled", False),
    ("disabled", True),
    ("hidden", True),
    ("hidden", False),
])
def test_entity_update_forwards_disabled_and_hidden(client, ws_update, field, value):
    """Public names stay on the HTTP boundary. The WebSocket client maps them."""
    response = client.post("/api/registries/entities/update",
                           json={"entity_id": "sensor.x", field: value})
    assert response.status_code == 200
    assert response.json()["updated_fields"] == {field: value}
    ws_update.assert_awaited_once_with("sensor.x", **{field: value})


def test_websocket_error_result_raises():
    ws = HAWebSocketClient.__new__(HAWebSocketClient)
    ws.pending_requests = {}
    ws.event_callbacks = {}

    async def run():
        future = asyncio.get_running_loop().create_future()
        ws.pending_requests[7] = future
        await ws._handle_message({"id": 7, "type": "result", "success": False,
                                  "error": {"code": "invalid_format", "message": "bad key"}})
        return future

    future = asyncio.run(run())
    with pytest.raises(Exception, match="invalid_format"):
        future.result()
