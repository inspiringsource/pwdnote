from pwdnote import notes
from pwdnote.cli import app
from typer.testing import CliRunner


runner = CliRunner()


def _write_note(content: str) -> None:
    result = runner.invoke(app, ["write", "--stdin", "--create"], input=content)
    assert result.exit_code == 0


def test_paste_selects_first_and_second_items(project_dir):
    _write_note("# Project Notes\n\n- git status\n- uv run pytest\n")

    first = runner.invoke(app, ["paste", "1"])
    second = runner.invoke(app, ["paste", "2"])

    assert first.exit_code == 0
    assert first.stdout == "git status\n"
    assert second.exit_code == 0
    assert second.stdout == "uv run pytest\n"


def test_paste_word_aliases_select_first_item(project_dir):
    _write_note("- git status\n- uv run pytest\n")

    one = runner.invoke(app, ["paste", "one"])
    first = runner.invoke(app, ["paste", "first"])

    assert one.exit_code == 0
    assert one.stdout == "git status\n"
    assert first.exit_code == 0
    assert first.stdout == "git status\n"


def test_paste_preserves_item_content_after_marker(project_dir):
    _write_note(
        '- git checkout feature/my-branch\n- git commit -m "Fix parser"\n'
    )

    branch = runner.invoke(app, ["paste", "1"])
    quoted = runner.invoke(app, ["paste", "2"])

    assert branch.stdout == "git checkout feature/my-branch\n"
    assert quoted.stdout == 'git commit -m "Fix parser"\n'


def test_extract_items_ignores_non_items_and_nested_items():
    content = (
        "# Project Notes\n"
        "A normal paragraph.\n"
        "\n"
        "- top level\n"
        "  - nested item\n"
        "\t- tab-indented item\n"
        "- another top-level item\n"
    )

    assert notes.extract_markdown_list_items(content) == [
        "top level",
        "another top-level item",
    ]


def test_paste_out_of_range_fails_clearly(project_dir):
    _write_note("- one\n- two\n- three\n")

    result = runner.invoke(app, ["paste", "4"])

    assert result.exit_code != 0
    assert result.stdout == ""
    assert (
        "Error: item 4 does not exist. The note contains 3 list items."
        in result.stderr
    )


def test_paste_fails_when_note_has_no_list_items(project_dir):
    _write_note("# Project Notes\n\nA normal paragraph.\n")

    result = runner.invoke(app, ["paste", "1"])

    assert result.exit_code != 0
    assert result.stdout == ""
    assert "Error: the project note contains no Markdown list items." in result.stderr


def test_paste_fails_without_note(project_dir):
    result = runner.invoke(app, ["paste", "1"])

    assert result.exit_code != 0
    assert result.stdout == ""
    assert "No project note found." in result.stderr


def test_paste_rejects_invalid_selectors(project_dir):
    _write_note("- item\n")

    for selector in ("zero", "abc", "-1", "0", "1.5"):
        result = runner.invoke(app, ["paste", selector])

        assert result.exit_code != 0
        assert result.stdout == ""
        assert f"Error: invalid item selector '{selector}'." in result.stderr


def test_paste_does_not_modify_encrypted_note(project_dir):
    _write_note("- git status\n")
    note_path = project_dir / ".pwdnote.enc"
    ciphertext = note_path.read_bytes()

    result = runner.invoke(app, ["paste", "1"])

    assert result.exit_code == 0
    assert note_path.read_bytes() == ciphertext


def test_paste_help_describes_numbering_and_aliases():
    result = runner.invoke(app, ["paste", "--help"])

    assert result.exit_code == 0
    assert "1-based" in result.stdout
    assert "one" in result.stdout
    assert "first" in result.stdout
