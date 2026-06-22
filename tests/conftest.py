import pytest

from pwdnote.crypto import generate_key


@pytest.fixture
def key() -> bytes:
    return generate_key()


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    """An isolated working directory with its own key file and config dir."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PWDNOTE_KEY_FILE", str(tmp_path / "key"))
    monkeypatch.setenv("PWDNOTE_CONFIG_DIR", str(tmp_path / "config"))
    return tmp_path


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """An isolated pwdnote config directory."""
    target = tmp_path / "config"
    target.mkdir()
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("PWDNOTE_CONFIG_DIR", str(target))
    return target
