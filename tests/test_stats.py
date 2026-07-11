import os
import subprocess

from typer.testing import CliRunner

from pwdnote.cli import app


runner = CliRunner()


def _run(project_dir, *args, env=None):
    return subprocess.run(
        ["git", *args],
        cwd=project_dir,
        check=True,
        capture_output=True,
        env=env,
    )


def _init_git(project_dir):
    _run(project_dir, "init")
    _run(project_dir, "config", "user.name", "pwdnote tests")
    _run(project_dir, "config", "user.email", "pwdnote-tests@example.invalid")


def _write_note(content, *, create=False):
    args = ["write", "--stdin"]
    if create:
        args.append("--create")
    result = runner.invoke(app, args, input=content)
    assert result.exit_code == 0


def _commit_note(project_dir, message, date):
    _run(project_dir, "add", ".pwdnote.enc")
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = f"{date}T12:00:00+00:00"
    env["GIT_COMMITTER_DATE"] = f"{date}T12:00:00+00:00"
    _run(project_dir, "commit", "-m", message, env=env)


def test_stats_reports_content_paths_security_size_and_does_not_modify_note(project_dir):
    content = "alpha beta\ngamma\n"
    _write_note(content, create=True)
    note_path = project_dir / ".pwdnote.enc"
    ciphertext = note_path.read_bytes()

    result = runner.invoke(app, ["stats"])

    assert result.exit_code == 0
    assert f"Root: {project_dir.resolve()}" in result.output
    assert f"Note: {note_path.resolve()}" in result.output
    assert "Lines: 2" in result.output
    assert "Words: 3" in result.output
    assert f"Characters: {len(content)}" in result.output
    assert f"Encrypted size: {note_path.stat().st_size} B" in result.output
    assert "Encryption backend: Fernet" in result.output
    assert "Key backend: file" in result.output
    assert note_path.read_bytes() == ciphertext


def test_stats_reports_git_revision_count_and_dates(project_dir):
    _init_git(project_dir)
    _write_note("first note\n", create=True)
    _commit_note(project_dir, "Add note", "2026-06-22")
    _write_note("second note\n")
    _commit_note(project_dir, "Update note", "2026-07-12")

    result = runner.invoke(app, ["stats"])

    assert result.exit_code == 0
    assert "Revisions: 2" in result.output
    assert "First commit: 2026-06-22" in result.output
    assert "Latest commit: 2026-07-12" in result.output


def test_stats_works_outside_git(project_dir):
    _write_note("outside git\n", create=True)

    result = runner.invoke(app, ["stats"])

    assert result.exit_code == 0
    assert "Words: 2" in result.output
    assert "Revisions: 0" in result.output
    assert "First commit: Unavailable" in result.output
    assert "Latest commit: Unavailable" in result.output


def test_stats_works_when_note_has_no_git_history(project_dir):
    _init_git(project_dir)
    readme = project_dir / "README.md"
    readme.write_text("project\n", encoding="utf-8")
    _run(project_dir, "add", "README.md")
    _run(project_dir, "commit", "-m", "Add readme")
    _write_note("uncommitted note\n", create=True)

    result = runner.invoke(app, ["stats"])

    assert result.exit_code == 0
    assert "Revisions: 0" in result.output
    assert "First commit: Unavailable" in result.output
    assert "Latest commit: Unavailable" in result.output


def test_stats_line_count_ignores_trailing_newline_as_an_extra_line(project_dir):
    _write_note("one\ntwo\n", create=True)
    with_newline = runner.invoke(app, ["stats"])
    _write_note("one\ntwo")
    without_newline = runner.invoke(app, ["stats"])

    assert "Lines: 2" in with_newline.output
    assert "Lines: 2" in without_newline.output
