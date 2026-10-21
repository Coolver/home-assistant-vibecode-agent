"""Security tests for the setup panel that embeds the API key (issue #50)."""
import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.main import app

INGRESS_IP = "172.30.32.2"
LAN_IP = "192.168.1.50"


def client_from(host):
    """TestClient whose requests appear to come from `host` (the pinned Starlette has no client= kwarg)."""
    async def asgi(scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            scope = {**scope, "client": (host, 50000)}
        await app(scope, receive, send)
    return TestClient(asgi)


@pytest.fixture
def supervisor_mode(monkeypatch):
    monkeypatch.setattr(main, "RUNTIME_MODE", "supervisor")


@pytest.mark.parametrize("path", ["/", "/old"])
def test_panel_refused_on_published_port_under_supervisor(supervisor_mode, path):
    client = client_from(LAN_IP)
    response = client.get(path)
    assert response.status_code == 403
    assert main.API_KEY not in response.text


@pytest.mark.parametrize("path", ["/", "/old"])
def test_panel_served_through_ingress_under_supervisor(supervisor_mode, path):
    client = client_from(INGRESS_IP)
    response = client.get(path)
    assert response.status_code == 200
    assert main.API_KEY[:8] in response.text


def test_panel_still_served_outside_supervisor():
    # Standalone/dev have no Ingress; behaviour there is unchanged.
    client = client_from(LAN_IP)
    assert client.get("/").status_code == 200


def test_no_cors_grant_for_foreign_origins():
    client = client_from(LAN_IP)
    response = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_no_cors_preflight_for_foreign_origins():
    client = client_from(LAN_IP)
    response = client.options(
        "/api/entities/list",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert "access-control-allow-origin" not in response.headers
