"""Command-line interface for pwdnote."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import typer
from rich.console import Console

from . import editor as editor_mod
from . import notes, project, settings
from .config import load_or_create_key
from .crypto import DecryptionError

app = typer.Typer(
    name="pwdnote",
    help="Encrypted, project-local notes for your terminal.",
    no_args_is_help=False,
    add_completion=False,
)

config_app = typer.Typer(help="Inspect and create the pwdnote config file.")
app.add_typer(config_app, name="config")

console = Console()


def _fail(message: str) -> NoReturn:
    console.print(message)
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


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
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


# Built-in command aliases. Not user-configurable.
app.command(name="i", hidden=True)(init)
app.command(name="e", hidden=True)(edit)
app.command(name="a", hidden=True)(add)
app.command(name="s", hidden=True)(status)


if __name__ == "__main__":  # pragma: no cover
    app()
