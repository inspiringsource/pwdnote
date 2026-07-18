"""Small cross-platform system clipboard abstraction."""

from __future__ import annotations

import shutil
import subprocess
import sys


class ClipboardError(RuntimeError):
    """Base error for clipboard operations."""


class ClipboardUnavailableError(ClipboardError):
    """Raised when no supported clipboard command is installed."""


class ClipboardCommandError(ClipboardError):
    """Raised when installed clipboard commands all fail."""


def _clipboard_commands(platform: str) -> list[tuple[str, ...]]:
    if platform == "darwin":
        return [("pbcopy",)]
    if platform == "win32":
        return [("clip",)]
    if platform.startswith("linux"):
        return [
            ("wl-copy",),
            ("xclip", "-selection", "clipboard"),
            ("xsel", "--clipboard", "--input"),
        ]
    return []


def _unavailable_message(platform: str) -> str:
    if platform == "darwin":
        return "no supported clipboard command was found. Expected pbcopy."
    if platform == "win32":
        return "no supported clipboard command was found. Expected clip."
    if platform.startswith("linux"):
        return (
            "no supported clipboard command was found. "
            "Install wl-clipboard, xclip, or xsel."
        )
    return "no supported clipboard command was found on this platform."


def copy_to_clipboard(text: str) -> None:
    """Copy ``text`` using stdin without exposing it in process arguments."""
    commands = _clipboard_commands(sys.platform)
    found_command = False
    last_error: OSError | subprocess.CalledProcessError | None = None

    for candidate in commands:
        executable = shutil.which(candidate[0])
        if executable is None:
            continue
        found_command = True
        command = [executable, *candidate[1:]]
        try:
            subprocess.run(
                command,
                input=text,
                text=True,
                check=True,
                capture_output=True,
                shell=False,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            last_error = exc
            continue
        return

    if found_command:
        raise ClipboardCommandError("clipboard command failed") from last_error
    raise ClipboardUnavailableError(_unavailable_message(sys.platform))
