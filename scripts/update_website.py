#!/usr/bin/env python3
"""Update the pwdnote static website release sections."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any


VERSION_START = "<!-- PWDNOTE_VERSION_START -->"
VERSION_END = "<!-- PWDNOTE_VERSION_END -->"
WHATS_NEW_START = "<!-- PWDNOTE_WHATS_NEW_START -->"
WHATS_NEW_END = "<!-- PWDNOTE_WHATS_NEW_END -->"


class UpdateError(Exception):
    """Raised when the website file cannot be updated safely."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_metadata(path: Path) -> dict[str, Any]:
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise UpdateError(f"Release metadata not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise UpdateError(f"Release metadata is invalid JSON: {exc}") from exc

    required = {
        "version": str,
        "title": str,
        "items": list,
        "commands": list,
    }
    for key, expected_type in required.items():
        value = metadata.get(key)
        if not isinstance(value, expected_type):
            raise UpdateError(f"Release metadata field '{key}' must be {expected_type.__name__}.")

    for key in ("items", "commands"):
        if not all(isinstance(item, str) for item in metadata[key]):
            raise UpdateError(f"Release metadata field '{key}' must contain only strings.")

    return metadata


def _replace_marked_section(text: str, start: str, end: str, replacement: str) -> str:
    start_count = text.count(start)
    end_count = text.count(end)
    if start_count != 1 or end_count != 1:
        raise UpdateError(
            f"Expected exactly one marker pair for {start} / {end}; "
            f"found {start_count} start marker(s) and {end_count} end marker(s)."
        )

    start_index = text.index(start)
    content_start = start_index + len(start)
    end_index = text.find(end, content_start)
    if end_index == -1:
        raise UpdateError(f"Marker order is invalid for {start} / {end}.")

    end_line_start = text.rfind("\n", 0, end_index) + 1
    return text[:content_start] + "\n" + replacement.rstrip() + "\n" + text[end_line_start:]


def _render_version(metadata: dict[str, Any]) -> str:
    version = html.escape(metadata["version"], quote=True)
    return f"          Latest CLI release: v{version}"


def _render_whats_new(metadata: dict[str, Any]) -> str:
    title = html.escape(metadata["title"], quote=True)
    items = "\n".join(
        f"          <li>{html.escape(item, quote=True)}</li>" for item in metadata["items"]
    )
    commands = "\n".join(
        f'<span class="prompt">$ </span>{html.escape(command, quote=True)}'
        for command in metadata["commands"]
    )
    return f"""      <section class="pwd-section" aria-labelledby="whats-new-heading">
        <h2 id="whats-new-heading">{title}</h2>
        <ul class="security-list">
{items}
        </ul>
        <pre class="code"><code>{commands}</code></pre>
      </section>"""


def update_website(website_file: Path, metadata_file: Path) -> bool:
    metadata = _load_metadata(metadata_file)
    try:
        original = website_file.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise UpdateError(f"Website file not found: {website_file}") from exc

    updated = _replace_marked_section(
        original, VERSION_START, VERSION_END, _render_version(metadata)
    )
    updated = _replace_marked_section(
        updated, WHATS_NEW_START, WHATS_NEW_END, _render_whats_new(metadata)
    )

    if updated == original:
        return False

    website_file.write_text(updated, encoding="utf-8")
    return True


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update pwdnote release sections in the static website HTML."
    )
    parser.add_argument(
        "--website-file",
        required=True,
        type=Path,
        help="Path to the website HTML file to update, for example pwdnote/index.html.",
    )
    parser.add_argument(
        "--metadata-file",
        default=_repo_root() / "release" / "pwdnote-latest.json",
        type=Path,
        help="Path to pwdnote release metadata JSON.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        changed = update_website(args.website_file, args.metadata_file)
    except UpdateError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if changed:
        print(f"Updated {args.website_file}")
    else:
        print(f"No changes for {args.website_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
