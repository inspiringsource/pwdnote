from typer.testing import CliRunner

from pwdnote.cli import app

runner = CliRunner()


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "pwdnote" in result.output.lower()


def test_init_creates_note(project_dir):
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert (project_dir / ".pwdnote.enc").exists()


def test_init_twice_reports_existing(project_dir):
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_show_without_note(project_dir):
    result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "No project note found" in result.output


def test_show_after_init(project_dir):
    runner.invoke(app, ["init"])
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Project Notes" in result.output


def test_add_appends_bullet(project_dir):
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["add", "rotate keys"])
    assert result.exit_code == 0
    shown = runner.invoke(app, [])
    assert "- rotate keys" in shown.output


def test_add_without_note(project_dir):
    result = runner.invoke(app, ["add", "something"])
    assert result.exit_code == 1
    assert "No project note found" in result.output


def test_status_with_note(project_dir):
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Encrypted:" in result.output
    assert "Yes" in result.output
    assert ".pwdnote.enc" in result.output


def test_status_without_note(project_dir):
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "No note yet" in result.output


def test_gitignore_adds_entries(project_dir):
    result = runner.invoke(app, ["gitignore"])
    assert result.exit_code == 0
    content = (project_dir / ".gitignore").read_text()
    assert ".pwdnote.tmp" in content
    assert ".pwdnote.cache" in content
    assert ".pwdnote.enc" not in content


def test_gitignore_is_idempotent(project_dir):
    runner.invoke(app, ["gitignore"])
    result = runner.invoke(app, ["gitignore"])
    assert result.exit_code == 0
    assert "already present" in result.output
    content = (project_dir / ".gitignore").read_text()
    assert content.count(".pwdnote.tmp") == 1


def _write_config(project_dir, body):
    config_dir = project_dir / "config"
    config_dir.mkdir(exist_ok=True)
    (config_dir / "config.toml").write_text(body, encoding="utf-8")


def test_init_uses_custom_initial_content(project_dir):
    _write_config(project_dir, '[notes]\ninitial_content = "# Custom Header\\n"\n')
    runner.invoke(app, ["init"])
    shown = runner.invoke(app, [])
    assert "# Custom Header" in shown.output
    assert "Project Notes" not in shown.output


def test_auto_gitignore_adds_note_file(project_dir):
    _write_config(project_dir, "[notes]\nauto_gitignore_note_file = true\n")
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    content = (project_dir / ".gitignore").read_text()
    assert ".pwdnote.enc" in content


def test_init_default_does_not_gitignore_note_file(project_dir):
    runner.invoke(app, ["init"])
    assert not (project_dir / ".gitignore").exists()


def test_unsupported_key_backend_fails(project_dir):
    _write_config(project_dir, '[security]\nkey_backend = "keychain"\n')
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 1
    assert "keychain" in result.output


def test_config_path_command(project_dir):
    result = runner.invoke(app, ["config", "path"])
    assert result.exit_code == 0
    assert "config.toml" in result.output


def test_config_show_command(project_dir):
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "[notes]" in result.output
    assert "key_backend" in result.output


def test_config_init_command(project_dir):
    result = runner.invoke(app, ["config", "init"])
    assert result.exit_code == 0
    assert "Created" in result.output
    assert (project_dir / "config" / "config.toml").exists()
    again = runner.invoke(app, ["config", "init"])
    assert "already exists" in again.output


def test_alias_i_inits(project_dir):
    result = runner.invoke(app, ["i"])
    assert result.exit_code == 0
    assert (project_dir / ".pwdnote.enc").exists()


def test_alias_e_edits(project_dir, monkeypatch):
    monkeypatch.setenv("VISUAL", "true")
    runner.invoke(app, ["i"])
    result = runner.invoke(app, ["e"])
    assert result.exit_code == 0
    assert "Saved." in result.output


def test_alias_a_adds(project_dir):
    runner.invoke(app, ["i"])
    result = runner.invoke(app, ["a", "something"])
    assert result.exit_code == 0
    assert "Added: - something" in result.output


def test_alias_s_status(project_dir):
    runner.invoke(app, ["i"])
    result = runner.invoke(app, ["s"])
    assert result.exit_code == 0
    assert "Encrypted:" in result.output
