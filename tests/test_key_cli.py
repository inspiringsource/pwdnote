import stat

from typer.testing import CliRunner

from pwdnote import notes
from pwdnote.cli import app
from pwdnote.crypto import generate_key

runner = CliRunner()


def test_key_path_prints_expected_key_path(project_dir):
    result = runner.invoke(app, ["key", "path"])
    assert result.exit_code == 0
    assert result.stdout.strip() == str((project_dir / "key").resolve())
    assert not (project_dir / "key").exists()


def test_key_path_respects_xdg_config_home(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PWDNOTE_KEY_FILE", raising=False)
    monkeypatch.delenv("PWDNOTE_CONFIG_DIR", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    result = runner.invoke(app, ["key", "path"])

    assert result.exit_code == 0
    assert result.stdout.strip() == str((tmp_path / "xdg" / "pwdnote" / "key").resolve())
    assert not (tmp_path / "xdg" / "pwdnote" / "key").exists()


def test_key_export_prints_only_raw_key_to_stdout(project_dir):
    key = generate_key()
    (project_dir / "key").write_bytes(key)

    result = runner.invoke(app, ["key", "export"])

    assert result.exit_code == 0
    assert result.stdout == key.decode("ascii") + "\n"


def test_key_export_warning_goes_to_stderr(project_dir):
    (project_dir / "key").write_bytes(generate_key())

    result = runner.invoke(app, ["key", "export"])

    assert result.exit_code == 0
    assert (
        "Warning: this exports your pwdnote encryption key. Anyone with this key can read your encrypted notes."
        in result.stderr
    )
    assert "Warning:" not in result.stdout


def test_key_export_fails_when_key_missing(project_dir):
    result = runner.invoke(app, ["key", "export"])

    assert result.exit_code == 1
    assert "Key does not exist." in result.stderr


def test_key_import_imports_valid_key_from_stdin(project_dir):
    key = generate_key()

    result = runner.invoke(app, ["key", "import"], input=key.decode("ascii") + "\n")

    assert result.exit_code == 0
    assert result.stdout == "Key imported.\n"
    assert (project_dir / "key").read_bytes() == key


def test_imported_key_can_decrypt_note_encrypted_with_same_key(project_dir):
    key = generate_key()
    notes.write_note(project_dir / ".pwdnote.enc", key, "portable secret\n")

    imported = runner.invoke(app, ["key", "import"], input=key.decode("ascii") + "\n")
    assert imported.exit_code == 0

    shown = runner.invoke(app, ["read"])
    assert shown.exit_code == 0
    assert shown.stdout == "portable secret\n"


def test_key_import_refuses_invalid_keys(project_dir):
    result = runner.invoke(app, ["key", "import"], input="not-a-valid-fernet-key\n")

    assert result.exit_code == 1
    assert "Invalid key." in result.stderr
    assert not (project_dir / "key").exists()


def test_key_import_refuses_to_overwrite_without_force(project_dir):
    existing_key = generate_key()
    new_key = generate_key()
    (project_dir / "key").write_bytes(existing_key)

    result = runner.invoke(app, ["key", "import"], input=new_key.decode("ascii") + "\n")

    assert result.exit_code == 1
    assert "Key already exists. Use --force to replace it." in result.stderr
    assert (project_dir / "key").read_bytes() == existing_key


def test_key_import_force_replaces_existing_key(project_dir):
    old_key = generate_key()
    new_key = generate_key()
    (project_dir / "key").write_bytes(old_key)

    result = runner.invoke(
        app, ["key", "import", "--force"], input=new_key.decode("ascii") + "\n"
    )

    assert result.exit_code == 0
    assert result.stdout == "Key imported.\n"
    assert (
        "Warning: replacing your key may make existing notes unreadable unless you kept a backup of the old key."
        in result.stderr
    )
    assert (project_dir / "key").read_bytes() == new_key


def test_key_import_permissions(project_dir, monkeypatch):
    key = generate_key()
    monkeypatch.delenv("PWDNOTE_KEY_FILE", raising=False)

    result = runner.invoke(app, ["key", "import"], input=key.decode("ascii") + "\n")

    assert result.exit_code == 0
    assert stat.S_IMODE((project_dir / "config").stat().st_mode) == 0o700
    assert stat.S_IMODE((project_dir / "config" / "key").stat().st_mode) == 0o600
