"""Reading and writing encrypted project notes.

All persistence goes through the crypto layer, so plaintext notes are never
written to disk.
"""

from __future__ import annotations

from pathlib import Path

from .crypto import decrypt_text, encrypt_text

INITIAL_CONTENT = "# Project Notes\n"


class NoteNotFoundError(Exception):
    """Raised when a note is expected but does not exist."""


class NoteExistsError(Exception):
    """Raised when initializing a note that already exists."""


def note_exists(path: Path) -> bool:
    return path.is_file()


def read_note(path: Path, key: bytes) -> str:
    """Decrypt and return the contents of the note at ``path``."""
    if not path.is_file():
        raise NoteNotFoundError(str(path))
    return decrypt_text(path.read_bytes(), key)


def write_note(path: Path, key: bytes, text: str) -> None:
    """Encrypt ``text`` and write it to ``path``, overwriting any existing note."""
    path.write_bytes(encrypt_text(text, key))


def init_note(path: Path, key: bytes) -> None:
    """Create a new note with the default starter content."""
    if path.exists():
        raise NoteExistsError(str(path))
    write_note(path, key, INITIAL_CONTENT)


def append_line(path: Path, key: bytes, text: str) -> str:
    """Append ``text`` as a bullet point and return the updated note."""
    current = read_note(path, key)
    if current and not current.endswith("\n"):
        current += "\n"
    updated = f"{current}- {text}\n"
    write_note(path, key, updated)
    return updated
