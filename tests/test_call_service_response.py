"""Service calls that need Home Assistant to return a response."""
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.auth import verify_token
from app.main import app
from app.services.ha_client import ha_client


def _client():
    app.dependency_overrides[verify_token] = lambda: "test"
    return TestClient(app)


def test_return_response_uses_the_websocket_and_relays_the_payload(monkeypatch):
    ws = AsyncMock()
    ws.call_service = AsyncMock(return_value={
        "context": {"id": "ctx"},
        "response": {"weather.home": {"forecast": [{"temperature": 12}]}},
    })

    async def fake_ws():
        return ws

    monkeypatch.setattr("app.services.ha_websocket.get_ws_client", fake_ws)
    rest = AsyncMock()
    monkeypatch.setattr(ha_client, "call_service", rest)

    with _client() as client:
        response = client.post("/api/entities/call_service", json={
            "domain": "weather",
            "service": "get_forecasts",
            "service_data": {"type": "daily"},
            "target": {"entity_id": "weather.home"},
            "return_response": True,
        })

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["response"]["weather.home"]["forecast"][0]["temperature"] == 12
    rest.assert_not_called()
    ws.call_service.assert_awaited_once_with(
        "weather",
        "get_forecasts",
        service_data={"type": "daily"},
        target={"entity_id": "weather.home"},
        return_response=True,
    )


def test_ordinary_service_call_stays_on_rest(monkeypatch):
    rest = AsyncMock(return_value=[])
    monkeypatch.setattr(ha_client, "call_service", rest)

    with _client() as client:
        response = client.post("/api/entities/call_service", json={
            "domain": "light",
            "service": "turn_on",
            "target": {"entity_id": "light.kitchen"},
        })

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert "response" not in response.json()
    rest.assert_awaited_once_with("light", "turn_on", {"entity_id": "light.kitchen"})
