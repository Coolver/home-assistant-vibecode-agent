"""ignore_dirs is a list of directory prefixes relative to /config."""


def _manager(tmp_path, monkeypatch, ignore=""):
    monkeypatch.setenv("CONFIG_PATH", str(tmp_path))
    monkeypatch.setenv("GIT_VERSIONING_AUTO", "false")
    monkeypatch.setenv("IGNORE_DIRS", ignore)
    monkeypatch.setenv("MAX_BACKUPS", "30")
    from app.services.git_manager import GitManager

    return GitManager()


def test_empty_option_uses_builtin_exclusions_only(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch, " , ")
    assert manager.ignore_dirs == ()
    assert manager._should_include_path("custom_components/foo/__init__.py", False)
    assert manager._should_include_path("esphome/.esphome/cache.json", False)
    assert manager._should_include_path("scripts/a.yaml", False)
    assert manager._should_include_path("scripts2/a.yaml", False)
    assert not manager._should_include_path("secrets.yaml", False)
    assert not manager._should_include_path(".storage", True)


def test_prefixes_exclude_top_level_and_nested_dirs(tmp_path, monkeypatch):
    manager = _manager(
        tmp_path,
        monkeypatch,
        " ./custom_components/ , scripts , /tts/ , esphome/.esphome , image ",
    )
    assert manager.ignore_dirs == (
        "custom_components",
        "scripts",
        "tts",
        "esphome/.esphome",
        "image",
    )
    assert not manager._should_include_path("custom_components/foo/__init__.py", False)
    assert not manager._should_include_path("scripts/a.yaml", False)
    assert not manager._should_include_path("tts/hello.mp3", False)
    assert not manager._should_include_path("esphome/.esphome/cache.json", False)
    assert not manager._should_include_path("image", False)
    # A longer name is not the same prefix.
    assert manager._should_include_path("scripts2/a.yaml", False)
    assert manager._should_include_path("scripts2", False)
    assert manager._should_include_path("esphome/device.yaml", False)
    assert manager._should_include_path("configuration.yaml", False)
    assert not manager._should_include_path("secrets.yaml", False)


def test_sync_skips_prefixed_directories(tmp_path, monkeypatch):
    (tmp_path / "custom_components" / "foo").mkdir(parents=True)
    (tmp_path / "custom_components" / "foo" / "__init__.py").write_text("x\n", encoding="utf-8")
    (tmp_path / "esphome" / ".esphome").mkdir(parents=True)
    (tmp_path / "esphome" / ".esphome" / "cache.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "esphome" / "device.yaml").write_text("esphome:\n", encoding="utf-8")
    (tmp_path / "scripts2").mkdir()
    (tmp_path / "scripts2" / "a.yaml").write_text("a\n", encoding="utf-8")
    (tmp_path / "configuration.yaml").write_text("homeassistant:\n", encoding="utf-8")

    plain = _manager(tmp_path, monkeypatch, "")
    plain._sync_config_to_shadow()
    shadow = tmp_path / "ha_vibecode_git"
    assert (shadow / "custom_components" / "foo" / "__init__.py").is_file()

    ignored = _manager(tmp_path, monkeypatch, "custom_components, esphome/.esphome")
    ignored._sync_config_to_shadow()
    assert not (shadow / "custom_components" / "foo" / "__init__.py").exists()
    assert not (shadow / "esphome" / ".esphome" / "cache.json").exists()
    assert (shadow / "esphome" / "device.yaml").is_file()
    assert (shadow / "scripts2" / "a.yaml").is_file()
    assert (shadow / "configuration.yaml").is_file()
    assert (tmp_path / "custom_components" / "foo" / "__init__.py").is_file()


def test_sync_removes_nested_git_under_ignored_prefix(tmp_path, monkeypatch):
    excluded = tmp_path / "esphome" / ".esphome" / "external_components" / "widget" / ".git"
    excluded.mkdir(parents=True)
    (excluded / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (excluded / "config").write_text("[core]\n", encoding="utf-8")
    (tmp_path / "esphome" / ".esphome" / "cache.json").write_text("{}\n", encoding="utf-8")
    kept = tmp_path / "esphome" / "widget" / ".git"
    kept.mkdir(parents=True)
    (kept / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (tmp_path / "esphome" / "device.yaml").write_text("esphome:\n", encoding="utf-8")
    (tmp_path / "configuration.yaml").write_text("homeassistant:\n", encoding="utf-8")

    plain = _manager(tmp_path, monkeypatch, "")
    plain._sync_config_to_shadow()
    shadow = tmp_path / "ha_vibecode_git"
    shadow_excluded = shadow / "esphome" / ".esphome" / "external_components" / "widget" / ".git"
    shadow_kept = shadow / "esphome" / "widget" / ".git" / "HEAD"
    assert (shadow_excluded / "HEAD").is_file()
    assert shadow_kept.is_file()
    assert (shadow / ".git" / "HEAD").is_file()

    ignored = _manager(tmp_path, monkeypatch, "esphome/.esphome")
    ignored._sync_config_to_shadow()
    assert not (shadow_excluded / "HEAD").exists()
    assert not (shadow_excluded / "config").exists()
    assert not (shadow / "esphome" / ".esphome" / "cache.json").exists()
    assert shadow_kept.is_file()
    assert (shadow / "esphome" / "device.yaml").is_file()
    assert (shadow / ".git" / "HEAD").is_file()
    assert ignored.repo.git.rev_parse("--is-inside-work-tree").strip() == "true"
    assert (excluded / "HEAD").is_file()
