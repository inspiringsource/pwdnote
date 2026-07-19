"""Command-line interface for pwdnote."""

from __future__ import annotations

import difflib
import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

import typer
from rich.console import Console

from . import __version__
from . import editor as editor_mod
from . import clipboard, notes, project, settings, shell_integration
from .config import (
    InvalidKeyError,
    KeyExistsError,
    KeyNotFoundError,
    get_key_path,
    import_key as import_key_file,
    load_existing_key,
    load_or_create_key,
)
from .crypto import BACKEND_NAME, DecryptionError, decrypt_text

app = typer.Typer(
    name="pwdnote",
    help="Encrypted, project-local notes for your terminal.",
    no_args_is_help=False,
    add_completion=False,
)

config_app = typer.Typer(help="Inspect and create the pwdnote config file.")
app.add_typer(config_app, name="config")

key_app = typer.Typer(help="Manage the pwdnote encryption key.")
app.add_typer(key_app, name="key")

shell_app = typer.Typer(help="Manage the optional Zsh integration.")
app.add_typer(shell_app, name="shell")

console = Console()


def _fail(message: str) -> NoReturn:
    console.print(message)
    raise typer.Exit(code=1)


def _err(message: str) -> NoReturn:
    """Fail an integration command with a clean, human-readable stderr message.

    Keeps stdout reserved for machine-consumable output.
    """
    print(message, file=sys.stderr)
    raise typer.Exit(code=1)


def _load_config() -> dict:
    try:
        return settings.load_config()
    except settings.ConfigError as exc:
        _fail(str(exc))


def _ensure_gitignored(root: Path, entries: list[str]) -> list[str]:
    """Append any missing ``entries`` to ``root/.gitignore``. Returns added entries."""
    gitignore_path = root / ".gitignore"
    content = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    existing = set(content.splitlines())
    to_add = [entry for entry in entries if entry not in existing]
    if not to_add:
        return []
    prefix = "" if content == "" or content.endswith("\n") else "\n"
    with gitignore_path.open("a", encoding="utf-8") as handle:
        handle.write(prefix + "".join(f"{entry}\n" for entry in to_add))
    return to_add


def _no_note() -> NoReturn:
    console.print("No project note found.")
    console.print("Run:")
    console.print("  pwdnote init")
    raise typer.Exit(code=1)


def _read_existing() -> tuple[Path, bytes, str]:
    """Locate the note, load the key, and decrypt — or fail with a message."""
    note_path = project.find_existing_note(Path.cwd())
    if note_path is None:
        _no_note()
    key = load_or_create_key()
    try:
        text = notes.read_note(note_path, key)
    except DecryptionError:
        _fail("Unable to decrypt project note.")
    except PermissionError:
        _fail("Unable to access note file.")
    return note_path, key, text


def _read_existing_plain() -> str:
    """Read the current note for stdout-only commands."""
    note_path = project.find_existing_note(Path.cwd())
    if note_path is None:
        _err("No project note found.")
    key = load_or_create_key()
    try:
        return notes.read_note(note_path, key)
    except DecryptionError:
        _err("Unable to decrypt project note.")
    except PermissionError:
        _err("Unable to access note file.")


def _preview_lines(text: str, lines: int, *, from_end: bool) -> str:
    split = text.splitlines(keepends=True)
    if from_end:
        return "".join(split[-lines:])
    return "".join(split[:lines])


def _resolve_markdown_list_item(selector: str) -> tuple[int, str]:
    note = _read_existing_plain()
    try:
        return notes.get_markdown_list_item(note, selector)
    except notes.InvalidItemSelectorError:
        _err(
            f"Error: invalid item selector '{selector}'. "
            "Use a positive number, 'one', or 'first'."
        )
    except notes.NoMarkdownListItemsError:
        _err("Error: the project note contains no Markdown list items.")
    except notes.MarkdownListItemNotFoundError as exc:
        noun = "item" if exc.item_count == 1 else "items"
        _err(
            f"Error: item {exc.item_number} does not exist. "
            f"The note contains {exc.item_count} list {noun}."
        )


def _try_run_git(
    args: list[str], *, cwd: Path
) -> subprocess.CompletedProcess[bytes] | None:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=False,
        )
    except FileNotFoundError:
        return None


def _run_git(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[bytes]:
    result = _try_run_git(args, cwd=cwd)
    if result is None:
        _err("git executable not found.")
    return result


def _note_history_stats(note_path: Path) -> tuple[int, str | None, str | None]:
    """Return revision count and boundary dates, tolerating unavailable Git."""
    root_result = _try_run_git(
        ["rev-parse", "--show-toplevel"], cwd=note_path.parent
    )
    if root_result is None or root_result.returncode != 0:
        return 0, None, None

    git_root = Path(root_result.stdout.decode("utf-8").strip())
    try:
        rel_path = note_path.resolve().relative_to(git_root.resolve()).as_posix()
    except ValueError:
        return 0, None, None

    log_result = _try_run_git(
        ["log", "--format=%cs", "--", rel_path], cwd=git_root
    )
    if log_result is None or log_result.returncode != 0:
        return 0, None, None

    dates = log_result.stdout.decode("utf-8").splitlines()
    if not dates:
        return 0, None, None
    return len(dates), dates[-1], dates[0]


def _format_file_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    value = float(size)
    for unit in ("KB", "MB", "GB"):
        value /= 1024
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
    raise AssertionError("unreachable")


def _git_root() -> Path:
    result = _run_git(["rev-parse", "--show-toplevel"], cwd=Path.cwd())
    if result.returncode != 0:
        _err("Not in a Git repository.")
    return Path(result.stdout.decode("utf-8").strip())


def _history_note_path(git_root: Path) -> tuple[Path, str]:
    root = project.resolve_project_root(Path.cwd())
    note_path = project.note_path_for(root)
    try:
        rel_path = note_path.resolve().relative_to(git_root.resolve()).as_posix()
    except ValueError:
        _err("Project note is not inside the current Git repository.")
    return note_path, rel_path


def _decrypt_note_bytes(token: bytes, *, source: str) -> str:
    key = load_or_create_key()
    try:
        return decrypt_text(token, key)
    except DecryptionError:
        _err(
            f"Unable to decrypt {source}. The current key may not match this note version."
        )


def _read_note_at_revision(rev: str, rel_path: str, git_root: Path) -> bytes:
    result = _run_git(["show", f"{rev}:{rel_path}"], cwd=git_root)
    if result.returncode != 0:
        _err(f"Revision does not contain {project.NOTE_FILENAME}: {rev}")
    return result.stdout


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"pwdnote {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Print the pwdnote version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Show the decrypted project note when no subcommand is given."""
    if ctx.invoked_subcommand is not None:
        return
    _, _, text = _read_existing()
    console.print(text, end="" if text.endswith("\n") else "\n", highlight=False)


@app.command()
def init() -> None:
    """Create an encrypted project note."""
    config = _load_config()
    root = project.resolve_project_root(Path.cwd())
    note_path = project.note_path_for(root)
    key = load_or_create_key()
    try:
        notes.init_note(note_path, key, config["notes"]["initial_content"])
    except notes.NoteExistsError:
        _fail("Project note already exists.")
    except PermissionError:
        _fail("Unable to access note file.")
    console.print(f"Created {note_path}")
    if config["notes"]["auto_gitignore_note_file"]:
        if _ensure_gitignored(root, [project.NOTE_FILENAME]):
            console.print(f"Added {project.NOTE_FILENAME} to .gitignore")


@app.command()
def edit() -> None:
    """Edit the project note in your editor."""
    config = _load_config()
    note_path, key, text = _read_existing()
    edited = editor_mod.edit_text(text, note_path.parent, config["editor"]["command"])
    try:
        notes.write_note(note_path, key, edited)
    except PermissionError:
        _fail("Unable to access note file.")
    console.print("Saved.")


@app.command()
def add(text: str = typer.Argument(..., help="Text to append as a bullet point.")) -> None:
    """Append a line to the project note without opening an editor."""
    note_path, key, _ = _read_existing()
    try:
        notes.append_line(note_path, key, text)
    except PermissionError:
        _fail("Unable to access note file.")
    console.print(f"Added: - {text}")


@app.command()
def status() -> None:
    """Show the project root, note file, and encryption status."""
    start = Path.cwd()
    note_path = project.find_existing_note(start)
    if note_path is None:
        root = project.resolve_project_root(start)
        console.print("Project root:")
        console.print(f"  {root}")
        console.print("Note file:")
        console.print("  (none — run 'pwdnote init')")
        console.print("Encrypted:")
        console.print("  No note yet")
        return
    console.print("Project root:")
    console.print(f"  {note_path.parent}")
    console.print("Note file:")
    console.print(f"  {note_path.name}")
    console.print("Encrypted:")
    console.print("  Yes")


@app.command()
def stats() -> None:
    """Summarize the current note and its Git history."""
    note_path, _, text = _read_existing()
    config = _load_config()
    revisions, first_commit, latest_commit = _note_history_stats(note_path)

    console.print("Project")
    console.print(f"  Root: {note_path.parent}", soft_wrap=True)
    console.print(f"  Note: {note_path}", soft_wrap=True)
    console.print()
    console.print("Content")
    console.print(f"  Lines: {len(text.splitlines())}")
    console.print(f"  Words: {len(text.split())}")
    console.print(f"  Characters: {len(text)}")
    console.print(f"  Encrypted size: {_format_file_size(note_path.stat().st_size)}")
    console.print()
    console.print("Security")
    console.print(f"  Encryption backend: {BACKEND_NAME}")
    console.print(f"  Key backend: {config['security']['key_backend']}")
    console.print()
    console.print("History")
    console.print(f"  Revisions: {revisions}")
    console.print(f"  First commit: {first_commit or 'Unavailable'}")
    console.print(f"  Latest commit: {latest_commit or 'Unavailable'}")


@app.command()
def gitignore() -> None:
    """Add recommended pwdnote entries to the project's .gitignore."""
    root = project.resolve_project_root(Path.cwd())
    to_add = _ensure_gitignored(root, [".pwdnote.tmp", ".pwdnote.cache"])
    if not to_add:
        console.print("All recommended entries are already present.")
        return
    console.print(f"Added to {root / '.gitignore'}:")
    for entry in to_add:
        console.print(f"  {entry}")


# --- Integration commands (for editors/extensions) ------------------------
# These print machine-consumable output to stdout and human-readable errors to
# stderr. They never log decrypted note content beyond the requested output.


@app.command()
def read() -> None:
    """Decrypt and print the current project note to stdout (no formatting)."""
    sys.stdout.write(_read_existing_plain())


@app.command()
def head(
    lines: int = typer.Option(
        10,
        "-n",
        "--lines",
        min=1,
        help="Number of lines to print.",
    ),
) -> None:
    """Print the first lines of the decrypted project note."""
    sys.stdout.write(_preview_lines(_read_existing_plain(), lines, from_end=False))


@app.command()
def tail(
    lines: int = typer.Option(
        10,
        "-n",
        "--lines",
        min=1,
        help="Number of lines to print.",
    ),
) -> None:
    """Print the last lines of the decrypted project note."""
    sys.stdout.write(_preview_lines(_read_existing_plain(), lines, from_end=True))


@app.command(context_settings={"ignore_unknown_options": True})
def cat(
    item: str = typer.Argument(
        ...,
        help="1-based item number; 'one' and 'first' select the first item.",
    ),
) -> None:
    """Print one Markdown list item without its list marker.

    The stored content is printed to stdout and is not executed.
    """
    _, selected = _resolve_markdown_list_item(item)
    sys.stdout.write(selected + "\n")


@app.command(context_settings={"ignore_unknown_options": True})
def copy(
    item: str = typer.Argument(
        ...,
        help="1-based item number; 'one' and 'first' select the first item.",
    ),
) -> None:
    """Copy one Markdown list item to the system clipboard.

    The stored content is copied without a newline and is not executed.
    """
    index, selected = _resolve_markdown_list_item(item)
    try:
        clipboard.copy_to_clipboard(selected)
    except clipboard.ClipboardUnavailableError as exc:
        _err(f"Error: {exc}")
    except clipboard.ClipboardError:
        _err(f"Error: could not copy item {index + 1} to the clipboard.")
    print(f"Copied item {index + 1} to the clipboard.", file=sys.stderr)


@app.command(context_settings={"ignore_unknown_options": True})
def paste(
    item: str = typer.Argument(
        ...,
        help="1-based item number; 'one' and 'first' select the first item.",
    ),
) -> None:
    """Insert one Markdown list item into the Zsh command line.

    Requires the optional Zsh integration and never executes the stored content.
    """
    _err(
        "Error: direct paste requires the pwdnote Zsh integration. "
        "Run 'pwdnote shell install'."
    )


@app.command()
def log() -> None:
    """Show commits that changed the encrypted project note."""
    git_root = _git_root()
    _, rel_path = _history_note_path(git_root)
    result = _run_git(
        ["log", "--format=%h  %cs  %s", "--", rel_path],
        cwd=git_root,
    )
    if result.returncode != 0:
        _err("Unable to read Git history for project note.")
    output = result.stdout.decode("utf-8")
    if not output.strip():
        _err(f"No Git history found for {project.NOTE_FILENAME}.")
    sys.stdout.write(output)


@app.command()
def show(rev: str = typer.Argument(..., help="Git revision to read.")) -> None:
    """Decrypt and print the project note at a Git revision."""
    git_root = _git_root()
    _, rel_path = _history_note_path(git_root)
    token = _read_note_at_revision(rev, rel_path, git_root)
    sys.stdout.write(_decrypt_note_bytes(token, source=f"{project.NOTE_FILENAME} at {rev}"))


@app.command()
def diff(
    old: str | None = typer.Argument(None, help="Old Git revision."),
    new: str | None = typer.Argument(None, help="New Git revision."),
) -> None:
    """Show a readable diff between decrypted note versions."""
    git_root = _git_root()
    note_path, rel_path = _history_note_path(git_root)
    if old is None and new is None:
        old_label = f"{project.NOTE_FILENAME} (HEAD)"
        new_label = f"{project.NOTE_FILENAME} (working tree)"
        old_text = _decrypt_note_bytes(
            _read_note_at_revision("HEAD", rel_path, git_root), source=old_label
        )
        if not note_path.is_file():
            _err("No project note found in the working tree.")
        new_text = _decrypt_note_bytes(note_path.read_bytes(), source=new_label)
    elif old is not None and new is not None:
        old_label = f"{project.NOTE_FILENAME} ({old})"
        new_label = f"{project.NOTE_FILENAME} ({new})"
        old_text = _decrypt_note_bytes(
            _read_note_at_revision(old, rel_path, git_root), source=old_label
        )
        new_text = _decrypt_note_bytes(
            _read_note_at_revision(new, rel_path, git_root), source=new_label
        )
    else:
        _err("diff requires both old and new revisions, or neither.")

    sys.stdout.write(
        "".join(
            difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=old_label,
                tofile=new_label,
            )
        )
    )


@app.command()
def write(
    stdin: bool = typer.Option(
        False, "--stdin", help="Read the new note content from stdin."
    ),
    create: bool = typer.Option(
        False, "--create", help="Create the note if it does not already exist."
    ),
) -> None:
    """Replace the current project note with content read from stdin."""
    if not stdin:
        _err("write requires --stdin.")
    content = sys.stdin.read()
    note_path = project.find_existing_note(Path.cwd())
    if note_path is None:
        if not create:
            _err("No project note found. Pass --create to create one.")
        note_path = project.note_path_for(project.resolve_project_root(Path.cwd()))
    key = load_or_create_key()
    try:
        notes.write_note(note_path, key, content)
    except PermissionError:
        _err("Unable to access note file.")


@app.command()
def root() -> None:
    """Print the detected project root path to stdout."""
    typer.echo(str(project.resolve_project_root(Path.cwd())))


@app.command(name="note-path")
def note_path() -> None:
    """Print the resolved .pwdnote.enc path (existing, or where it would be created)."""
    existing = project.find_existing_note(Path.cwd())
    if existing is not None:
        typer.echo(str(existing))
        return
    typer.echo(str(project.note_path_for(project.resolve_project_root(Path.cwd()))))


@key_app.command("path")
def key_path() -> None:
    """Print the current key file path."""
    typer.echo(str(get_key_path().expanduser().resolve()))


@key_app.command("export")
def key_export() -> None:
    """Print the current key to stdout."""
    try:
        key = load_existing_key()
    except KeyNotFoundError:
        _err("Key does not exist.")
    print(
        "Warning: this exports your pwdnote encryption key. Anyone with this key can read your encrypted notes.",
        file=sys.stderr,
    )
    sys.stdout.write(key.decode("ascii") + "\n")


@key_app.command("import")
def key_import(
    force: bool = typer.Option(
        False, "--force", help="Replace the current key if one already exists."
    ),
) -> None:
    """Import a key from stdin."""
    key = sys.stdin.read().encode("utf-8")
    if force and get_key_path().exists():
        print(
            "Warning: replacing your key may make existing notes unreadable unless you kept a backup of the old key.",
            file=sys.stderr,
        )
    try:
        import_key_file(key, force=force)
    except InvalidKeyError:
        _err("Invalid key.")
    except KeyExistsError:
        _err("Key already exists. Use --force to replace it.")
    console.print("Key imported.")


@config_app.command("path")
def config_path() -> None:
    """Print the config file path."""
    console.print(str(settings.get_config_path()))


@config_app.command("show")
def config_show() -> None:
    """Print the effective configuration."""
    config = _load_config()
    console.print(settings.dump_config(config), end="", highlight=False, markup=False)


@config_app.command("init")
def config_init() -> None:
    """Create config.toml with defaults if it does not exist."""
    path, created = settings.create_default_config()
    if created:
        console.print(f"Created {path}")
    else:
        console.print(f"Config already exists at {path}")


@shell_app.command("print")
def shell_print() -> None:
    """Print the pwdnote Zsh integration script."""
    sys.stdout.write(shell_integration.render_zsh_integration())


@shell_app.command("install")
def shell_install() -> None:
    """Install or update the optional Zsh integration."""
    current_shell = os.environ.get("SHELL")
    if current_shell and Path(current_shell).name != "zsh":
        print(
            "Warning: installing Zsh integration while the current shell is not Zsh.",
            file=sys.stderr,
        )
    try:
        _, zshrc_path = shell_integration.install()
    except OSError:
        _err("Error: unable to install the pwdnote Zsh integration.")
    console.print("Installed pwdnote Zsh integration.")
    console.print(f"Restart Zsh or run: source {zshrc_path}")


@shell_app.command("status")
def shell_status() -> None:
    """Check whether the Zsh integration is completely installed."""
    if shell_integration.is_installed():
        console.print("pwdnote Zsh integration is installed.")
        return
    _err(
        "pwdnote Zsh integration is not installed.\n"
        "Run 'pwdnote shell install'."
    )


@shell_app.command("uninstall")
def shell_uninstall() -> None:
    """Remove only the pwdnote-managed Zsh integration."""
    try:
        changed, zshrc_path = shell_integration.uninstall()
    except OSError:
        _err("Error: unable to remove the pwdnote Zsh integration.")
    if not changed:
        console.print("pwdnote Zsh integration was not installed.")
        return
    console.print("Removed pwdnote Zsh integration.")
    console.print(f"Restart Zsh or run: source {zshrc_path}")


# Built-in command aliases. Not user-configurable.
app.command(name="i", help="Alias for init.")(init)
app.command(name="e", help="Alias for edit.")(edit)
app.command(name="a", help="Alias for add.")(add)
app.command(name="s", help="Alias for status.")(status)
app.command(
    name="c",
    help="Alias for cat.",
    context_settings={"ignore_unknown_options": True},
)(cat)
app.command(
    name="y",
    help="Alias for copy.",
    context_settings={"ignore_unknown_options": True},
)(copy)
app.command(
    name="p",
    help="Alias for paste.",
    context_settings={"ignore_unknown_options": True},
)(paste)


if __name__ == "__main__":  # pragma: no cover
    app()
