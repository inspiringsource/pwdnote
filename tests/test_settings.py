import pytest

from pwdnote import settings


def test_config_defaults(config_dir):
    config = settings.load_config()
    assert config["notes"]["initial_content"] == "# Project Notes\n"
    assert config["notes"]["auto_gitignore_note_file"] is False
    assert config["editor"]["command"] == ""
    assert config["security"]["key_backend"] == "file"


def test_xdg_config_home_support(tmp_path, monkeypatch):
    monkeypatch.delenv("PWDNOTE_CONFIG_DIR", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert settings.get_config_path() == tmp_path / "pwdnote" / "config.toml"


def test_custom_initial_content(config_dir):
    (config_dir / "config.toml").write_text(
        '[notes]\ninitial_content = "hello world\\n"\n', encoding="utf-8"
    )
    config = settings.load_config()
    assert config["notes"]["initial_content"] == "hello world\n"


def test_unsupported_key_backend_fails_clearly(config_dir):
    (config_dir / "config.toml").write_text(
        '[security]\nkey_backend = "keychain"\n', encoding="utf-8"
    )
    with pytest.raises(settings.ConfigError) as excinfo:
        settings.load_config()
    assert "keychain" in str(excinfo.value)
    assert "file" in str(excinfo.value)


def test_create_default_config(config_dir):
    path, created = settings.create_default_config()
    assert created is True
    assert path == config_dir / "config.toml"
    assert "[notes]" in path.read_text(encoding="utf-8")

    # Idempotent: second call does not overwrite.
    path2, created2 = settings.create_default_config()
    assert created2 is False
    assert path2 == path


def test_default_config_toml_roundtrips():
    assert settings.dump_config(settings.DEFAULT_CONFIG) == settings.DEFAULT_CONFIG_TOML
