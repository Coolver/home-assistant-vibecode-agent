"""A checkpoint must not swallow the edits made after it opens."""
import asyncio
import os
from pathlib import Path

import pytest


@pytest.fixture
def git_manager(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_PATH", str(tmp_path))
    monkeypatch.setenv("GIT_VERSIONING_AUTO", "true")
    monkeypatch.setenv("MAX_BACKUPS", "30")
    from app.services.git_manager import GitManager

    manager = GitManager()
    assert manager.repo is not None
    (tmp_path / "configuration.yaml").write_text("homeassistant:\n", encoding="utf-8")
    return manager


def _messages(manager):
    return [commit.message.strip() for commit in manager.repo.iter_commits()]


def test_write_is_committed_while_checkpoint_is_open(git_manager):
    opened = asyncio.run(git_manager.create_checkpoint("rename the hallway light"))
    assert opened["success"] is True
    assert git_manager.processing_request is True

    config = Path(os.environ["CONFIG_PATH"]) / "configuration.yaml"
    config.write_text("homeassistant:\n  name: Home\n", encoding="utf-8")
    commit = asyncio.run(git_manager.commit_changes(
        "Write file: configuration.yaml",
        skip_if_processing=False,
    ))

    assert commit
    assert git_manager.processing_request is True
    assert any(message.startswith("Write file:") for message in _messages(git_manager))


def test_closing_checkpoint_commits_changes_the_write_path_skipped(git_manager):
    asyncio.run(git_manager.create_checkpoint("add a morning automation"))
    config = Path(os.environ["CONFIG_PATH"]) / "automations.yaml"
    config.write_text("- id: morning\n", encoding="utf-8")

    skipped = asyncio.run(git_manager.commit_changes(
        "Backup before writing automations.yaml",
        skip_if_processing=True,
    ))
    assert skipped is None

    commit = asyncio.run(git_manager.end_checkpoint())

    assert commit
    assert git_manager.processing_request is False
    assert git_manager.checkpoint_request is None
    assert any(message == "Changes: add a morning automation" for message in _messages(git_manager))
