import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "update_website.py"
SPEC = importlib.util.spec_from_file_location("update_website", SCRIPT_PATH)
assert SPEC is not None
update_website = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.dont_write_bytecode = True
SPEC.loader.exec_module(update_website)


def _write_metadata(path):
    path.write_text(
        """{
  "version": "0.3.1",
  "title": "What’s new in v0.3.1",
  "items": [
    "New key management commands.",
    "Export your encryption key for backups."
  ],
  "commands": [
    "pwdnote key path",
    "cat pwdnote-key.backup | pwdnote key import"
  ]
}
""",
        encoding="utf-8",
    )


def test_update_website_replaces_marked_sections(tmp_path):
    metadata_file = tmp_path / "pwdnote-latest.json"
    website_file = tmp_path / "index.html"
    _write_metadata(metadata_file)
    website_file.write_text(
        """<html>
<body>
<p>Before</p>
<!-- PWDNOTE_VERSION_START -->
old version
<!-- PWDNOTE_VERSION_END -->
<main>
<!-- PWDNOTE_WHATS_NEW_START -->
old release notes
<!-- PWDNOTE_WHATS_NEW_END -->
</main>
<p>After</p>
</body>
</html>
""",
        encoding="utf-8",
    )

    changed = update_website.update_website(website_file, metadata_file)

    assert changed is True
    updated = website_file.read_text(encoding="utf-8")
    assert "<p>Before</p>" in updated
    assert "<p>After</p>" in updated
    assert "Latest CLI release: v0.3.1" in updated
    assert "<h2 id=\"whats-new-heading\">What’s new in v0.3.1</h2>" in updated
    assert "<li>New key management commands.</li>" in updated
    assert '<span class="prompt">$ </span>pwdnote key path' in updated
    assert "old version" not in updated
    assert "old release notes" not in updated


def test_update_website_returns_false_when_unchanged(tmp_path):
    metadata_file = tmp_path / "pwdnote-latest.json"
    website_file = tmp_path / "index.html"
    _write_metadata(metadata_file)
    website_file.write_text(
        f"""<!-- PWDNOTE_VERSION_START -->
{update_website._render_version(update_website._load_metadata(metadata_file))}
<!-- PWDNOTE_VERSION_END -->
<!-- PWDNOTE_WHATS_NEW_START -->
{update_website._render_whats_new(update_website._load_metadata(metadata_file))}
<!-- PWDNOTE_WHATS_NEW_END -->
""",
        encoding="utf-8",
    )

    changed = update_website.update_website(website_file, metadata_file)

    assert changed is False


def test_update_website_fails_when_markers_are_missing(tmp_path):
    metadata_file = tmp_path / "pwdnote-latest.json"
    website_file = tmp_path / "index.html"
    _write_metadata(metadata_file)
    website_file.write_text("<html></html>\n", encoding="utf-8")

    with pytest.raises(update_website.UpdateError) as excinfo:
        update_website.update_website(website_file, metadata_file)

    assert "Expected exactly one marker pair" in str(excinfo.value)


def test_update_website_escapes_metadata_html(tmp_path):
    metadata_file = tmp_path / "pwdnote-latest.json"
    website_file = tmp_path / "index.html"
    metadata_file.write_text(
        """{
  "version": "0.3.1<script>",
  "title": "Release <b>",
  "items": ["Use <trusted> backups."],
  "commands": ["pwdnote key export > backup"]
}
""",
        encoding="utf-8",
    )
    website_file.write_text(
        """<!-- PWDNOTE_VERSION_START -->
old
<!-- PWDNOTE_VERSION_END -->
<!-- PWDNOTE_WHATS_NEW_START -->
old
<!-- PWDNOTE_WHATS_NEW_END -->
""",
        encoding="utf-8",
    )

    update_website.update_website(website_file, metadata_file)

    updated = website_file.read_text(encoding="utf-8")
    assert "0.3.1&lt;script&gt;" in updated
    assert "Release &lt;b&gt;" in updated
    assert "Use &lt;trusted&gt; backups." in updated
    assert "pwdnote key export &gt; backup" in updated
