import pytest

from pwdnote import cli, clipboard, notes
from typer.testing import CliRunner


runner = CliRunner()


def _write_note(content: str) -> None:
    result = runner.invoke(cli.app, ["write", "--stdin", "--create"], input=content)
    assert result.exit_code == 0


def _capture_clipboard(monkeypatch) -> list[str]:
    copied: list[str] = []
    monkeypatch.setattr(cli.clipboard, "copy_to_clipboard", copied.append)
    return copied


def test_shared_item_selection_is_one_based_and_preserves_content():
    note = (
        "# Project Notes\n"
        "A paragraph.\n"
        "\n"
        "- git checkout feature/my-branch\n"
        "  - nested item\n"
        '- git commit -m "Fix parser" && echo café\n'
    )

    assert notes.get_markdown_list_item(note, "one") == (
        0,
        "git checkout feature/my-branch",
    )
    assert notes.get_markdown_list_item(note, "first") == (
        0,
        "git checkout feature/my-branch",
    )
    assert notes.get_markdown_list_item(note, "2") == (
        1,
        'git commit -m "Fix parser" && echo café',
    )


def test_cat_prints_selected_item_with_one_newline(project_dir):
    _write_note("# Project Notes\n\n- git status\n- uv run pytest\n")

    first = runner.invoke(cli.app, ["cat", "1"])
    second = runner.invoke(cli.app, ["cat", "2"])

    assert first.exit_code == 0
    assert first.stdout == "git status\n"
    assert first.stderr == ""
    assert second.exit_code == 0
    assert second.stdout == "uv run pytest\n"


def test_cat_supports_word_selectors(project_dir):
    _write_note("- git status\n")

    assert runner.invoke(cli.app, ["cat", "one"]).stdout == "git status\n"
    assert runner.invoke(cli.app, ["cat", "first"]).stdout == "git status\n"


def test_cat_does_not_invoke_clipboard(project_dir, monkeypatch):
    _write_note("- git status\n")

    def unexpected_copy(text: str) -> None:
        raise AssertionError(f"clipboard called with {text!r}")

    monkeypatch.setattr(cli.clipboard, "copy_to_clipboard", unexpected_copy)

    result = runner.invoke(cli.app, ["cat", "1"])

    assert result.exit_code == 0
    assert result.stdout == "git status\n"


def test_paste_copies_exact_item_without_marker_or_newline(project_dir, monkeypatch):
    _write_note('- git commit -m "Fix parser"\n')
    copied = _capture_clipboard(monkeypatch)

    result = runner.invoke(cli.app, ["paste", "1"])

    assert result.exit_code == 0
    assert result.stdout == ""
    assert result.stderr == "Copied item 1 to the clipboard.\n"
    assert copied == ['git commit -m "Fix parser"']


def test_paste_supports_numeric_and_word_selectors(project_dir, monkeypatch):
    _write_note("- first item\n- second item\n- third item\n")
    copied = _capture_clipboard(monkeypatch)

    for selector in ("one", "first", "2", "3"):
        result = runner.invoke(cli.app, ["paste", selector])
        assert result.exit_code == 0
        assert result.stdout == ""

    assert copied == ["first item", "first item", "second item", "third item"]


@pytest.mark.parametrize("command", ["cat", "paste"])
@pytest.mark.parametrize("selector", ["zero", "abc", "-1", "0", "1.5"])
def test_item_commands_reject_invalid_selectors(
    project_dir, monkeypatch, command, selector
):
    _write_note("- item\n")
    _capture_clipboard(monkeypatch)

    result = runner.invoke(cli.app, [command, selector])

    assert result.exit_code != 0
    assert result.stdout == ""
    assert f"Error: invalid item selector '{selector}'." in result.stderr


@pytest.mark.parametrize("command", ["cat", "paste"])
def test_item_commands_fail_out_of_range(project_dir, monkeypatch, command):
    _write_note("- one\n- two\n- three\n")
    _capture_clipboard(monkeypatch)

    result = runner.invoke(cli.app, [command, "4"])

    assert result.exit_code != 0
    assert result.stdout == ""
    assert (
        "Error: item 4 does not exist. The note contains 3 list items."
        in result.stderr
    )


@pytest.mark.parametrize("command", ["cat", "paste"])
def test_item_commands_fail_without_list_items(project_dir, monkeypatch, command):
    _write_note("# Project Notes\n\nA normal paragraph.\n")
    _capture_clipboard(monkeypatch)

    result = runner.invoke(cli.app, [command, "1"])

    assert result.exit_code != 0
    assert result.stdout == ""
    assert "Error: the project note contains no Markdown list items." in result.stderr


@pytest.mark.parametrize("command", ["cat", "paste"])
def test_item_commands_fail_without_note(project_dir, monkeypatch, command):
    _capture_clipboard(monkeypatch)

    result = runner.invoke(cli.app, [command, "1"])

    assert result.exit_code != 0
    assert result.stdout == ""
    assert "No project note found." in result.stderr


def test_paste_clipboard_failure_is_clear_and_does_not_expose_item(
    project_dir, monkeypatch
):
    selected = "do-not-expose-this-value"
    _write_note(f"- {selected}\n")

    def fail_copy(text: str) -> None:
        raise clipboard.ClipboardCommandError("backend details")

    monkeypatch.setattr(cli.clipboard, "copy_to_clipboard", fail_copy)

    result = runner.invoke(cli.app, ["paste", "1"])

    assert result.exit_code != 0
    assert result.stdout == ""
    assert result.stderr == "Error: could not copy item 1 to the clipboard.\n"
    assert selected not in result.stderr


def test_paste_reports_missing_clipboard_backend(project_dir, monkeypatch):
    _write_note("- git status\n")

    def unavailable(text: str) -> None:
        raise clipboard.ClipboardUnavailableError("no backend installed")

    monkeypatch.setattr(cli.clipboard, "copy_to_clipboard", unavailable)

    result = runner.invoke(cli.app, ["paste", "1"])

    assert result.exit_code != 0
    assert result.stdout == ""
    assert result.stderr == "Error: no backend installed\n"


@pytest.mark.parametrize("command", ["cat", "paste"])
def test_item_commands_do_not_modify_encrypted_note(
    project_dir, monkeypatch, command
):
    _write_note("- git status\n")
    copied = _capture_clipboard(monkeypatch)
    note_path = project_dir / ".pwdnote.enc"
    ciphertext = note_path.read_bytes()

    result = runner.invoke(cli.app, [command, "1"])

    assert result.exit_code == 0
    assert note_path.read_bytes() == ciphertext
    assert copied == (["git status"] if command == "paste" else [])


def test_paste_does_not_execute_selected_item(project_dir, monkeypatch):
    marker = project_dir / "executed"
    selected = f"touch {marker}"
    _write_note(f"- {selected}\n")
    copied = _capture_clipboard(monkeypatch)

    result = runner.invoke(cli.app, ["paste", "1"])

    assert result.exit_code == 0
    assert copied == [selected]
    assert not marker.exists()


@pytest.mark.parametrize(
    ("command", "action"),
    [("cat", "printed to stdout"), ("paste", "copied without a newline")],
)
def test_item_command_help_describes_selectors_action_and_no_execution(
    command, action
):
    result = runner.invoke(cli.app, [command, "--help"])

    assert result.exit_code == 0
    assert "1-based" in result.stdout
    assert "one" in result.stdout
    assert "first" in result.stdout
    assert action in result.stdout
    assert "not executed" in result.stdout
