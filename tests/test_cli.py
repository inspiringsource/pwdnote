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
