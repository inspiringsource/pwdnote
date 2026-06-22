from pwdnote import editor


def test_resolve_editor_prefers_visual(monkeypatch):
    monkeypatch.setenv("VISUAL", "myvisual")
    monkeypatch.setenv("EDITOR", "myeditor")
    assert editor.resolve_editor() == "myvisual"


def test_resolve_editor_falls_back_to_editor(monkeypatch):
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.setenv("EDITOR", "myeditor")
    assert editor.resolve_editor() == "myeditor"


def test_resolve_editor_override_wins(monkeypatch):
    monkeypatch.setenv("VISUAL", "myvisual")
    monkeypatch.setenv("EDITOR", "myeditor")
    assert editor.resolve_editor("configured") == "configured"


def test_resolve_editor_default(monkeypatch):
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    assert editor.resolve_editor() in {"nano", "vi"}


def test_edit_text_invokes_editor(tmp_path, monkeypatch):
    script = tmp_path / "fake_editor.sh"
    script.write_text('#!/bin/sh\nprintf " EDITED" >> "$1"\n')
    script.chmod(0o755)
    monkeypatch.setenv("VISUAL", str(script))

    result = editor.edit_text("start", tmp_path)
    assert result == "start EDITED"


def test_edit_text_cleans_up_temp_file(tmp_path, monkeypatch):
    monkeypatch.setenv("VISUAL", "true")
    editor.edit_text("hello", tmp_path)
    assert list(tmp_path.glob(".pwdnote*")) == []
