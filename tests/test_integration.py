"""Tests for the editor/extension integration commands."""

import subprocess

from pwdnote import __version__
from pwdnote.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def _init_with(project_dir, content):
    """Create a note via write --create with known content."""
    result = runner.invoke(app, ["write", "--stdin", "--create"], input=content)
    assert result.exit_code == 0
    return result


def _git(project_dir, *args):
    return subprocess.run(
        ["git", *args],
        cwd=project_dir,
        check=True,
        capture_output=True,
    )


def _init_git(project_dir):
    _git(project_dir, "init")
    _git(project_dir, "config", "user.name", "pwdnote tests")
    _git(project_dir, "config", "user.email", "pwdnote-tests@example.invalid")


def _commit_note(project_dir, message):
    _git(project_dir, "add", ".pwdnote.enc")
    _git(project_dir, "commit", "-m", message)


def _write_with(project_dir, content, *, create=False):
    args = ["write", "--stdin"]
    if create:
        args.append("--create")
    result = runner.invoke(app, args, input=content)
    assert result.exit_code == 0
    return result


def test_read_prints_decrypted_content(project_dir):
    runner.invoke(app, ["init"])
    runner.invoke(app, ["add", "rotate AWS keys"])
    result = runner.invoke(app, ["read"])
    assert result.exit_code == 0
    assert "# Project Notes" in result.stdout
    assert "- rotate AWS keys" in result.stdout


def test_read_output_has_no_rich_decoration(project_dir):
    _init_with(project_dir, "plain line one\nplain line two\n")
    result = runner.invoke(app, ["read"])
    assert result.exit_code == 0
    assert result.stdout == "plain line one\nplain line two\n"


def test_head_defaults_to_first_10_lines(project_dir):
    content = "".join(f"line {number}\n" for number in range(1, 13))
    _init_with(project_dir, content)

    result = runner.invoke(app, ["head"])

    assert result.exit_code == 0
    assert result.stdout == "".join(f"line {number}\n" for number in range(1, 11))


def test_head_short_option_prints_first_n_lines(project_dir):
    content = "".join(f"line {number}\n" for number in range(1, 8))
    _init_with(project_dir, content)

    result = runner.invoke(app, ["head", "-n", "5"])

    assert result.exit_code == 0
    assert result.stdout == "".join(f"line {number}\n" for number in range(1, 6))


def test_head_lines_option_prints_first_n_lines(project_dir):
    content = "".join(f"line {number}\n" for number in range(1, 8))
    _init_with(project_dir, content)

    result = runner.invoke(app, ["head", "--lines", "5"])

    assert result.exit_code == 0
    assert result.stdout == "".join(f"line {number}\n" for number in range(1, 6))


def test_tail_defaults_to_last_10_lines(project_dir):
    content = "".join(f"line {number}\n" for number in range(1, 13))
    _init_with(project_dir, content)

    result = runner.invoke(app, ["tail"])

    assert result.exit_code == 0
    assert result.stdout == "".join(f"line {number}\n" for number in range(3, 13))


def test_tail_short_option_prints_last_n_lines(project_dir):
    content = "".join(f"line {number}\n" for number in range(1, 8))
    _init_with(project_dir, content)

    result = runner.invoke(app, ["tail", "-n", "5"])

    assert result.exit_code == 0
    assert result.stdout == "".join(f"line {number}\n" for number in range(3, 8))


def test_tail_lines_option_prints_last_n_lines(project_dir):
    content = "".join(f"line {number}\n" for number in range(1, 8))
    _init_with(project_dir, content)

    result = runner.invoke(app, ["tail", "--lines", "5"])

    assert result.exit_code == 0
    assert result.stdout == "".join(f"line {number}\n" for number in range(3, 8))


def test_preview_fewer_than_n_lines_prints_whole_note(project_dir):
    content = "alpha\nbeta\ngamma\n"
    _init_with(project_dir, content)

    head_result = runner.invoke(app, ["head", "-n", "10"])
    tail_result = runner.invoke(app, ["tail", "-n", "10"])

    assert head_result.exit_code == 0
    assert head_result.stdout == content
    assert tail_result.exit_code == 0
    assert tail_result.stdout == content


def test_preview_invalid_line_count_fails_clearly(project_dir):
    _init_with(project_dir, "alpha\nbeta\n")

    zero_result = runner.invoke(app, ["head", "-n", "0"])
    negative_result = runner.invoke(app, ["tail", "--lines", "-1"])

    assert zero_result.exit_code != 0
    assert "Invalid value" in zero_result.stderr
    assert negative_result.exit_code != 0
    assert "Invalid value" in negative_result.stderr


def test_default_command_still_prints_full_note(project_dir):
    content = "".join(f"line {number}\n" for number in range(1, 13))
    _init_with(project_dir, content)

    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert result.stdout == content


def test_read_fails_without_note(project_dir):
    result = runner.invoke(app, ["read"])
    assert result.exit_code != 0
    assert "No project note found" in result.stderr
    assert not (project_dir / ".pwdnote.enc").exists()  # must not create a note


def test_write_stdin_replaces_content(project_dir):
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["write", "--stdin"], input="brand new body\n")
    assert result.exit_code == 0
    shown = runner.invoke(app, ["read"])
    assert shown.stdout == "brand new body\n"


def test_write_stdin_fails_without_note(project_dir):
    result = runner.invoke(app, ["write", "--stdin"], input="data")
    assert result.exit_code != 0
    assert "No project note found" in result.stderr
    assert not (project_dir / ".pwdnote.enc").exists()


def test_write_requires_stdin(project_dir):
    result = runner.invoke(app, ["write"])
    assert result.exit_code != 0
    assert "--stdin" in result.stderr


def test_write_create_creates_and_encrypts(project_dir):
    content = "secret deployment notes\n"
    result = runner.invoke(app, ["write", "--stdin", "--create"], input=content)
    assert result.exit_code == 0
    note_file = project_dir / ".pwdnote.enc"
    assert note_file.exists()
    # Stored as ciphertext, not plaintext.
    assert b"secret deployment notes" not in note_file.read_bytes()
    # Round-trips through read.
    shown = runner.invoke(app, ["read"])
    assert shown.stdout == content


def test_log_lists_commits_that_changed_note(project_dir):
    _init_git(project_dir)
    _write_with(project_dir, "first note\n", create=True)
    _commit_note(project_dir, "Add project note")
    _write_with(project_dir, "second note\n")
    _commit_note(project_dir, "Update project note")

    result = runner.invoke(app, ["log"])

    assert result.exit_code == 0
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2
    assert "Update project note" in lines[0]
    assert "Add project note" in lines[1]
    assert all(len(line.split("  ")[0]) >= 7 for line in lines)


def test_show_head_decrypts_committed_note(project_dir):
    _init_git(project_dir)
    _write_with(project_dir, "committed note\n", create=True)
    _commit_note(project_dir, "Add note")

    result = runner.invoke(app, ["show", "HEAD"])

    assert result.exit_code == 0
    assert result.stdout == "committed note\n"


def test_show_old_revision_decrypts_older_note(project_dir):
    _init_git(project_dir)
    _write_with(project_dir, "older note\n", create=True)
    _commit_note(project_dir, "Add note")
    _write_with(project_dir, "newer note\n")
    _commit_note(project_dir, "Update note")

    result = runner.invoke(app, ["show", "HEAD~1"])

    assert result.exit_code == 0
    assert result.stdout == "older note\n"


def test_diff_between_committed_versions_is_readable(project_dir):
    _init_git(project_dir)
    _write_with(project_dir, "line one\nold line\n", create=True)
    _commit_note(project_dir, "Add note")
    _write_with(project_dir, "line one\nnew line\n")
    _commit_note(project_dir, "Update note")

    result = runner.invoke(app, ["diff", "HEAD~1", "HEAD"])

    assert result.exit_code == 0
    assert "--- .pwdnote.enc (HEAD~1)" in result.stdout
    assert "+++ .pwdnote.enc (HEAD)" in result.stdout
    assert "-old line\n" in result.stdout
    assert "+new line\n" in result.stdout
    assert ".pwdnote.enc" in result.stdout


def test_diff_compares_head_with_working_tree(project_dir):
    _init_git(project_dir)
    _write_with(project_dir, "line one\ncommitted line\n", create=True)
    _commit_note(project_dir, "Add note")
    _write_with(project_dir, "line one\nworking tree line\n")

    result = runner.invoke(app, ["diff"])

    assert result.exit_code == 0
    assert "--- .pwdnote.enc (HEAD)" in result.stdout
    assert "+++ .pwdnote.enc (working tree)" in result.stdout
    assert "-committed line\n" in result.stdout
    assert "+working tree line\n" in result.stdout


def test_history_commands_fail_helpfully_outside_git(project_dir):
    _write_with(project_dir, "note without git\n", create=True)

    result = runner.invoke(app, ["log"])

    assert result.exit_code != 0
    assert "Not in a Git repository." in result.stderr


def test_show_fails_helpfully_when_revision_lacks_note(project_dir):
    _init_git(project_dir)
    (project_dir / "README.md").write_text("hello\n", encoding="utf-8")
    _git(project_dir, "add", "README.md")
    _git(project_dir, "commit", "-m", "Add readme")

    result = runner.invoke(app, ["show", "HEAD"])

    assert result.exit_code != 0
    assert "Revision does not contain .pwdnote.enc" in result.stderr


def test_root_prints_project_root(project_dir):
    result = runner.invoke(app, ["root"])
    assert result.exit_code == 0
    assert result.stdout.strip() == str(project_dir.resolve())


def test_note_path_when_missing(project_dir):
    result = runner.invoke(app, ["note-path"])
    assert result.exit_code == 0
    assert result.stdout.strip() == str((project_dir / ".pwdnote.enc").resolve())


def test_note_path_when_present(project_dir):
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["note-path"])
    assert result.exit_code == 0
    assert result.stdout.strip() == str((project_dir / ".pwdnote.enc").resolve())


def test_version_flag(project_dir):
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == f"pwdnote {__version__}"
    assert __version__ == "0.3.5"
