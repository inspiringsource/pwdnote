"""Project root detection.

Starting from the current working directory we search upward:

1. If ``.pwdnote.enc`` exists, use that location.
2. Otherwise, if ``.git`` exists, treat that location as the project root.
3. Stop at the filesystem root.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Optional

NOTE_FILENAME = ".pwdnote.enc"


def note_path_for(root: Path) -> Path:
    """Return the encrypted note path for a given project root."""
    return root / NOTE_FILENAME


def _iter_up(start: Path) -> Iterator[Path]:
    start = start.resolve()
    yield start
    yield from start.parents


def find_existing_note(start: Path) -> Optional[Path]:
    """Walk upward from ``start`` and return the first ``.pwdnote.enc`` found."""
    for directory in _iter_up(start):
        candidate = directory / NOTE_FILENAME
        if candidate.is_file():
            return candidate
    return None


def find_git_root(start: Path) -> Optional[Path]:
    """Walk upward from ``start`` and return the first directory with ``.git``."""
    for directory in _iter_up(start):
        if (directory / ".git").exists():
            return directory
    return None


def resolve_project_root(start: Path) -> Path:
    """Determine where a note should live for ``start``.

    Prefers an existing note's directory, then the git root, then ``start``.
    """
    note = find_existing_note(start)
    if note is not None:
        return note.parent
    git_root = find_git_root(start)
    if git_root is not None:
        return git_root
    return start.resolve()
