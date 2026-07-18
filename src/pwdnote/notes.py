"""Reading and writing encrypted project notes.

All persistence goes through the crypto layer, so plaintext notes are never
written to disk.
"""

from __future__ import annotations

import re
from pathlib import Path

from .crypto import decrypt_text, encrypt_text

INITIAL_CONTENT = "# Project Notes\n"
MARKDOWN_LIST_ITEM_RE = re.compile(r"^-\s+(.+)$")


class NoteNotFoundError(Exception):
    """Raised when a note is expected but does not exist."""


class NoteExistsError(Exception):
    """Raised when initializing a note that already exists."""


class InvalidItemSelectorError(ValueError):
    """Raised when a list item selector is not supported."""


class NoMarkdownListItemsError(LookupError):
    """Raised when a note has no selectable top-level list items."""


class MarkdownListItemNotFoundError(LookupError):
    """Raised when a selector points beyond the available list items."""

    def __init__(self, item_number: int, item_count: int) -> None:
        self.item_number = item_number
        self.item_count = item_count
        super().__init__(item_number, item_count)


def extract_markdown_list_items(note: str) -> list[str]:
    """Return top-level, single-line Markdown dash list items."""
    items: list[str] = []
    for line in note.splitlines():
        match = MARKDOWN_LIST_ITEM_RE.fullmatch(line)
        if match is not None:
            items.append(match.group(1))
    return items


def parse_item_selector(value: str) -> int:
    """Convert a public 1-based selector to a zero-based item index."""
    if value in {"one", "first"}:
        return 0
    if value.isascii() and value.isdecimal():
        number = int(value)
        if number > 0:
            return number - 1
    raise InvalidItemSelectorError(value)


def get_markdown_list_item(note: str, selector: str) -> tuple[int, str]:
    """Resolve ``selector`` and return its zero-based index and exact content."""
    index = parse_item_selector(selector)
    items = extract_markdown_list_items(note)
    if not items:
        raise NoMarkdownListItemsError
    if index >= len(items):
        raise MarkdownListItemNotFoundError(index + 1, len(items))
    return index, items[index]


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


def init_note(path: Path, key: bytes, content: str = INITIAL_CONTENT) -> None:
    """Create a new note with the given starter content."""
    if path.exists():
        raise NoteExistsError(str(path))
    write_note(path, key, content)


def append_line(path: Path, key: bytes, text: str) -> str:
    """Append ``text`` as a bullet point and return the updated note."""
    current = read_note(path, key)
    if current and not current.endswith("\n"):
        current += "\n"
    updated = f"{current}- {text}\n"
    write_note(path, key, updated)
    return updated
