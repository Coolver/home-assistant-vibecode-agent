"""Credential files stay out of the file API unless the option is on."""
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.auth import verify_token
from app.main import app
from app.services.file_manager import FileManager, SensitivePathError, file_manager


@pytest.fixture
def manager(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_PATH", str(tmp_path))
    monkeypatch.delenv("ALLOW_SENSITIVE_FILES", raising=False)
    storage = tmp_path / ".storage"
    storage.mkdir()
    (storage / "core.config_entries").write_text('{"data":{"password":"router-secret"}}', encoding="utf-8")
    (storage / "auth").write_text('{"refresh_token":"auth-secret"}', encoding="utf-8")
    (storage / "auth_provider.homeassistant").write_text("users", encoding="utf-8")
    (storage / "lovelace.lovelace").write_text("title: Home\n", encoding="utf-8")
    (storage / "automation.storage").write_text("{}\n", encoding="utf-8")
    (tmp_path / "secrets.yaml").write_text("mqtt_password: mqtt-secret\n", encoding="utf-8")
    (tmp_path / "configuration.yaml").write_text("homeassistant: {}\n", encoding="utf-8")
    (tmp_path / "id_rsa.key").write_text("private-key\n", encoding="utf-8")
    return FileManager()


def test_credential_files_are_blocked(manager):
    blocked = [
        "secrets.yaml",
        ".storage/core.config_entries",
        ".storage/auth",
        ".storage/auth_provider.homeassistant",
        "id_rsa.key",
        "pkg/../secrets.yaml",
    ]
    (manager.config_path / "pkg").mkdir()
    for path in blocked:
        with pytest.raises(SensitivePathError):
            asyncio.run(manager.read_file(path))
        with pytest.raises(SensitivePathError):
            asyncio.run(manager.write_file(path, "overwrite"))


def test_dashboards_and_config_stay_readable(manager):
    assert "homeassistant" in asyncio.run(manager.read_file("configuration.yaml"))
    assert "title: Home" in asyncio.run(manager.read_file(".storage/lovelace.lovelace"))
    assert "{}" in asyncio.run(manager.read_file(".storage/automation.storage"))


def test_listing_storage_omits_credential_files(manager):
    names = {item["name"] for item in asyncio.run(manager.list_files(".storage"))}
    assert "lovelace.lovelace" in names
    assert "automation.storage" in names
    assert "core.config_entries" not in names
    assert "auth" not in names
    assert "auth_provider.homeassistant" not in names


def test_option_allows_secrets(manager, monkeypatch):
    monkeypatch.setenv("ALLOW_SENSITIVE_FILES", "true")
    content = asyncio.run(manager.read_file("secrets.yaml"))
    assert "mqtt-secret" in content


def test_read_api_returns_403_without_the_secret(monkeypatch):
    monkeypatch.delenv("ALLOW_SENSITIVE_FILES", raising=False)
    config = Path(file_manager.config_path)
    config.mkdir(parents=True, exist_ok=True)
    (config / "secrets.yaml").write_text("mqtt_password: do-not-leak\n", encoding="utf-8")
    app.dependency_overrides[verify_token] = lambda: "test"
    try:
        response = TestClient(app).get("/api/files/read", params={"path": "secrets.yaml"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403
    assert "do-not-leak" not in response.text
    assert "allow_sensitive_files" in response.text
