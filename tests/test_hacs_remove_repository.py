"""Removing one HACS repository, not HACS itself."""
import json
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api import hacs
from app.auth import verify_token
from app.main import app


CATALOG = {
    "445678": {
        "full_name": "author/obsolete-card",
        "category": "plugin",
        "installed": True,
        "version_installed": "1.2.0",
    },
    "99": {
        "full_name": "author/not-installed",
        "category": "integration",
        "installed": False,
        "version_installed": None,
    },
}


def _client():
    app.dependency_overrides[verify_token] = lambda: "test"
    return TestClient(app)


def test_remove_resolves_the_github_name_to_the_hacs_id(tmp_path, monkeypatch):
    hacs_dir = tmp_path / "hacs"
    hacs_dir.mkdir()
    monkeypatch.setattr(hacs, "HACS_INSTALL_PATH", str(hacs_dir))
    monkeypatch.setattr(hacs, "_load_hacs_repository_index", lambda: CATALOG)
    ws = AsyncMock()
    ws.remove_hacs_repository = AsyncMock(return_value={})

    async def fake_ws():
        return ws

    monkeypatch.setattr(hacs, "get_ws_client", fake_ws)

    with _client() as client:
        response = client.post("/api/hacs/remove_repository", json={"repository": "author/obsolete-card"})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["repository_id"] == "445678"
    assert body["data"]["repository"] == "author/obsolete-card"
    ws.remove_hacs_repository.assert_awaited_once_with("445678")


def test_remove_accepts_the_hacs_id_directly(tmp_path, monkeypatch):
    hacs_dir = tmp_path / "hacs"
    hacs_dir.mkdir()
    monkeypatch.setattr(hacs, "HACS_INSTALL_PATH", str(hacs_dir))
    monkeypatch.setattr(hacs, "_load_hacs_repository_index", lambda: CATALOG)
    ws = AsyncMock()
    ws.remove_hacs_repository = AsyncMock(return_value={})

    async def fake_ws():
        return ws

    monkeypatch.setattr(hacs, "get_ws_client", fake_ws)

    with _client() as client:
        response = client.post("/api/hacs/remove_repository", json={"repository": "445678"})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    ws.remove_hacs_repository.assert_awaited_once_with("445678")


def test_unknown_repository_is_not_sent_to_hacs(tmp_path, monkeypatch):
    hacs_dir = tmp_path / "hacs"
    hacs_dir.mkdir()
    monkeypatch.setattr(hacs, "HACS_INSTALL_PATH", str(hacs_dir))
    monkeypatch.setattr(hacs, "_load_hacs_repository_index", lambda: CATALOG)
    called = AsyncMock()
    monkeypatch.setattr(hacs, "get_ws_client", called)

    with _client() as client:
        response = client.post("/api/hacs/remove_repository", json={"repository": "no/such-card"})

    app.dependency_overrides.clear()
    assert response.status_code == 404
    called.assert_not_called()


def test_catalog_entry_that_is_not_installed_is_left_alone(tmp_path, monkeypatch):
    hacs_dir = tmp_path / "hacs"
    hacs_dir.mkdir()
    monkeypatch.setattr(hacs, "HACS_INSTALL_PATH", str(hacs_dir))
    monkeypatch.setattr(hacs, "_load_hacs_repository_index", lambda: CATALOG)
    called = AsyncMock()
    monkeypatch.setattr(hacs, "get_ws_client", called)

    with _client() as client:
        response = client.post("/api/hacs/remove_repository", json={"repository": "author/not-installed"})

    app.dependency_overrides.clear()
    assert response.status_code == 400
    called.assert_not_called()


def test_storage_file_is_indexed_by_repository_id(tmp_path, monkeypatch):
    storage = tmp_path / "hacs.repositories"
    storage.write_text(json.dumps({"data": CATALOG}), encoding="utf-8")
    monkeypatch.setattr(hacs, "HACS_REPOSITORIES_PATH", str(storage))

    repo_id, info = hacs._resolve_hacs_repository("author/obsolete-card")

    assert repo_id == "445678"
    assert info["category"] == "plugin"
