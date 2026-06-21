import pytest

from pwdnote.crypto import generate_key


@pytest.fixture
def key() -> bytes:
    return generate_key()


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    """An isolated working directory with its own key file."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PWDNOTE_KEY_FILE", str(tmp_path / "key"))
    return tmp_path
