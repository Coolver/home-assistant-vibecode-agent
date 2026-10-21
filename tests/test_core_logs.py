"""Supervisor journal logs: Core, Supervisor, and the host."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.logs import filter_log_level, strip_ansi
from app.auth import verify_token
from app.main import app
from app.services.supervisor_client import SupervisorClient, supervisor_client


JOURNAL = "\n".join([
    "2026-10-21 12:00:00.000 INFO (MainThread) [homeassistant.core] started",
    "2026-10-21 12:00:01.000 WARNING (MainThread) [homeassistant.components.mqtt] retrying",
    "2026-10-21 12:00:02.000 ERROR (MainThread) [homeassistant.components.mqtt] failed",
    "Traceback (most recent call last):",
    "  File \"/usr/src/homeassistant/components/mqtt/__init__.py\", line 1, in setup",
    "ValueError: boom",
    "2026-10-21 12:00:03.000 INFO (MainThread) [homeassistant.core] recovered",
])


@pytest.fixture
def client():
    app.dependency_overrides[verify_token] = lambda: "test"
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_level_filter_keeps_the_traceback_and_drops_quieter_lines():
    filtered = filter_log_level(JOURNAL, "ERROR")

    assert "failed" in filtered
    assert "Traceback" in filtered
    assert "ValueError: boom" in filtered
    assert "started" not in filtered
    assert "retrying" not in filtered
    assert "recovered" not in filtered


def test_warning_filter_keeps_warnings_and_errors():
    filtered = filter_log_level(JOURNAL, "WARNING")

    assert "retrying" in filtered
    assert "failed" in filtered
    assert "started" not in filtered


def test_ansi_sequences_are_removed():
    assert strip_ansi("\x1b[31mERROR\x1b[0m") == "ERROR"


def test_journal_returns_core_log_without_color(client, monkeypatch):
    monkeypatch.setattr(supervisor_client, "token", "test-token")
    colored = "\x1b[31m" + JOURNAL + "\x1b[0m"

    async def fake_journal(source, lines):
        assert source == "core"
        assert lines == 20
        return colored

    monkeypatch.setattr(supervisor_client, "get_journal_logs", fake_journal)

    response = client.get("/api/logs/journal", params={"lines": 20, "level": "error"})

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "core"
    assert body["level"] == "ERROR"
    assert "\x1b" not in body["logs"]
    assert "failed" in body["logs"]
    assert "started" not in body["logs"]


def test_journal_refuses_an_unknown_source(client, monkeypatch):
    monkeypatch.setattr(supervisor_client, "token", "test-token")
    response = client.get("/api/logs/journal", params={"source": "core/logs/../../host"})
    assert response.status_code == 422


def test_journal_requires_supervisor(client, monkeypatch):
    monkeypatch.setattr(supervisor_client, "token", "")
    response = client.get("/api/logs/journal")
    assert response.status_code == 501


def test_journal_request_asks_supervisor_for_plain_lines():
    class Response:
        status = 200

        async def text(self):
            return "2026-10-21 12:00:00.000 INFO (MainThread) [x] hi"

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    class Session:
        def __init__(self):
            self.url = None
            self.params = None
            self.headers = None

        def get(self, url, headers=None, params=None, timeout=None):
            self.url = url
            self.params = params
            self.headers = headers
            return Response()

    session = Session()
    journal = SupervisorClient()
    journal.base_url = "http://supervisor"
    journal.token = "test-token"

    with patch.object(journal, "_get_session", new=AsyncMock(return_value=session)):
        text = asyncio.run(journal.get_journal_logs("host", 40))

    assert "hi" in text
    assert session.url == "http://supervisor/host/logs"
    assert session.params == {"lines": "40", "no_colors": ""}
    assert session.headers["Accept"] == "text/plain"


def test_journal_rejects_a_source_outside_the_map():
    journal = SupervisorClient()
    with pytest.raises(ValueError):
        asyncio.run(journal.get_journal_logs("addons/core_ssh", 10))
