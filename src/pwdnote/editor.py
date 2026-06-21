"""Editor integration for ``pwdnote edit``.

Decrypted content is written to a temporary file with restrictive permissions,
opened in the user's editor, and deleted afterwards so that plaintext is never
left behind.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

_FALLBACK_EDITORS = ("nano", "vi")


def resolve_editor() -> str:
    """Resolve the editor command using the standard precedence.

    Order: ``$VISUAL``, ``$EDITOR``, ``nano``, ``vi``.
    """
    for env_var in ("VISUAL", "EDITOR"):
        value = os.environ.get(env_var)
        if value:
            return value
    for candidate in _FALLBACK_EDITORS:
        if shutil.which(candidate):
            return candidate
    return _FALLBACK_EDITORS[-1]


def edit_text(initial: str, directory: Path) -> str:
    """Open ``initial`` in an editor and return the edited result.

    A temporary file is created in ``directory`` with ``0600`` permissions and
    is always removed before returning, even if the editor fails.
    """
    fd, tmp_name = tempfile.mkstemp(prefix=".pwdnote", suffix=".tmp", dir=str(directory))
    tmp_path = Path(tmp_name)
    try:
        os.chmod(tmp_path, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(initial)
        editor_cmd = shlex.split(resolve_editor())
        subprocess.run([*editor_cmd, str(tmp_path)], check=True)
        return tmp_path.read_text(encoding="utf-8")
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass
