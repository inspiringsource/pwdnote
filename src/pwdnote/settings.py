"""Lightweight TOML configuration for pwdnote.

The config file lives at ``~/.config/pwdnote/config.toml`` (honouring
``PWDNOTE_CONFIG_DIR`` and ``XDG_CONFIG_HOME``). It is entirely optional: when
absent, the built-in defaults apply and behaviour is unchanged.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from .config import get_config_dir

DEFAULT_CONFIG: dict[str, dict[str, Any]] = {
    "notes": {
        "initial_content": "# Project Notes\n",
        "auto_gitignore_note_file": False,
    },
    "editor": {
        "command": "",
    },
    "security": {
        "key_backend": "file",
    },
}

SUPPORTED_KEY_BACKENDS = {"file"}


class ConfigError(Exception):
    """Raised when the configuration file is invalid."""


def get_config_path() -> Path:
    """Return the path to ``config.toml``."""
    return get_config_dir() / "config.toml"


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        escaped = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\t", "\\t")
        )
        return f'"{escaped}"'
    return str(value)


def dump_config(config: dict[str, dict[str, Any]]) -> str:
    """Render a config mapping as TOML text."""
    blocks = []
    for section, values in config.items():
        lines = [f"[{section}]"]
        lines.extend(f"{key} = {_toml_value(value)}" for key, value in values.items())
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


DEFAULT_CONFIG_TOML = dump_config(DEFAULT_CONFIG)


def _merge(base: dict[str, dict[str, Any]], override: dict[str, Any]) -> dict[str, Any]:
    result = {section: dict(values) for section, values in base.items()}
    for section, values in override.items():
        if section in result and isinstance(values, dict):
            result[section].update(values)
        else:
            result[section] = values
    return result


def load_config() -> dict[str, Any]:
    """Load the effective config, merging defaults with the config file.

    Raises ``ConfigError`` if the file is malformed or selects an unsupported
    key backend.
    """
    path = get_config_path()
    if not path.is_file():
        return {section: dict(values) for section, values in DEFAULT_CONFIG.items()}

    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid config at {path}: {exc}") from exc

    config = _merge(DEFAULT_CONFIG, data)
    backend = config["security"]["key_backend"]
    if backend not in SUPPORTED_KEY_BACKENDS:
        raise ConfigError(
            f"Unsupported security.key_backend: {backend!r}. "
            "Only 'file' is supported."
        )
    return config


def create_default_config() -> tuple[Path, bool]:
    """Write the default config file if it does not exist.

    Returns ``(path, created)`` where ``created`` is ``False`` if the file was
    already present.
    """
    path = get_config_path()
    if path.exists():
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_CONFIG_TOML, encoding="utf-8")
    return path, True
