"""Key management and configuration.

Version 1 stores a single auto-generated key on disk with restrictive
permissions. The lookup is structured so alternative backends (macOS Keychain,
1Password, age, GPG) can be added later behind ``load_or_create_key``.
"""

from __future__ import annotations

import os
from pathlib import Path

from .crypto import generate_key


def get_config_dir() -> Path:
    """Return the directory that holds pwdnote configuration and the key.

    Honours ``PWDNOTE_CONFIG_DIR`` and ``XDG_CONFIG_HOME`` overrides, falling
    back to ``~/.config/pwdnote``.
    """
    override = os.environ.get("PWDNOTE_CONFIG_DIR")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "pwdnote"
    return Path.home() / ".config" / "pwdnote"


def get_key_path() -> Path:
    """Return the path to the encryption key file."""
    override = os.environ.get("PWDNOTE_KEY_FILE")
    if override:
        return Path(override)
    return get_config_dir() / "key"


def load_or_create_key() -> bytes:
    """Load the encryption key, creating it on first use.

    The key file is created with ``0600`` permissions inside a ``0700``
    directory so that other users on the system cannot read it.
    """
    path = get_key_path()
    if path.exists():
        return path.read_bytes().strip()

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        # Best effort; not all filesystems support chmod.
        pass

    key = generate_key()
    # O_EXCL guards against a concurrent writer; 0o600 keeps it private.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(key)
    return key
