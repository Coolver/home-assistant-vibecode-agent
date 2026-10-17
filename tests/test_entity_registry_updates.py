"""Exercise the registry HTTP endpoint through the real WebSocket client."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api import registries
from app.services.ha_websocket import HAWebSocketClient


@pytest.fixture
def registry_api(monkeypatch):
    app = FastAPI()
    app.include_router(registries.router, prefix="/api/registries")
    client = HAWebSocketClient("http://localhost:8123", "test-token")
    client._connected = True
    response = {"success": True, "result": {"entity_id": "sensor.example"}}

    async def send_json(message):
        await client._handle_message({"id": message["id"], "type": "result", **response})

    client.ws = SimpleNamespace(closed=False, send_json=AsyncMock(side_effect=send_json))
    monkeypatch.setattr(registries, "get_ws_client", AsyncMock(return_value=client))
    return app, client, response


@pytest.mark.parametrize("disabled, disabled_by", [(True, "user"), (False, None)])
def test_disabled_flag_maps_to_home_assistant_field(registry_api, disabled, disabled_by):
    app, client, _ = registry_api
    with TestClient(app) as http:
        response = http.post("/api/registries/entities/update", json={
            "entity_id": "sensor.example", "disabled": disabled,
        })

    assert response.status_code == 200
    assert response.json()["updated_fields"] == {"disabled": disabled}
    assert client.ws.send_json.call_args.args[0] == {
        "id": 1,
        "type": "config/entity_registry/update",
        "entity_id": "sensor.example",
        "disabled_by": disabled_by,
    }


def test_name_update_leaves_disabled_state_untouched(registry_api):
    app, client, _ = registry_api
    with TestClient(app) as http:
        response = http.post("/api/registries/entities/update", json={
            "entity_id": "sensor.example", "name": "Example",
        })

    assert response.status_code == 200
    message = client.ws.send_json.call_args.args[0]
    assert message["name"] == "Example"
    assert "disabled_by" not in message
    assert "disabled" not in message


def test_home_assistant_rejection_is_not_reported_as_success(registry_api):
    app, client, ws_response = registry_api
    ws_response.clear()
    ws_response.update({"success": False, "error": {"code": "not_allowed", "message": "Entity cannot be disabled"}})
    with TestClient(app) as http:
        response = http.post("/api/registries/entities/update", json={
            "entity_id": "sensor.example", "disabled": True,
        })

    assert response.status_code == 500
    assert "not_allowed - Entity cannot be disabled" in response.json()["detail"]
    assert client.pending_requests == {}
