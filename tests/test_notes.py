import pytest

from pwdnote import notes


def test_init_and_read(tmp_path, key):
    path = tmp_path / ".pwdnote.enc"
    notes.init_note(path, key)
    assert notes.read_note(path, key) == notes.INITIAL_CONTENT


def test_init_existing_raises(tmp_path, key):
    path = tmp_path / ".pwdnote.enc"
    notes.init_note(path, key)
    with pytest.raises(notes.NoteExistsError):
        notes.init_note(path, key)


def test_read_missing_raises(tmp_path, key):
    with pytest.raises(notes.NoteNotFoundError):
        notes.read_note(tmp_path / ".pwdnote.enc", key)


def test_append_line(tmp_path, key):
    path = tmp_path / ".pwdnote.enc"
    notes.init_note(path, key)
    notes.append_line(path, key, "rotate AWS keys")
    text = notes.read_note(path, key)
    assert "- rotate AWS keys" in text
    assert text.endswith("\n")


def test_append_adds_trailing_newline_when_missing(tmp_path, key):
    path = tmp_path / ".pwdnote.enc"
    notes.write_note(path, key, "no newline here")
    notes.append_line(path, key, "second")
    text = notes.read_note(path, key)
    assert "no newline here\n- second\n" == text


def test_write_overwrites(tmp_path, key):
    path = tmp_path / ".pwdnote.enc"
    notes.write_note(path, key, "alpha")
    notes.write_note(path, key, "beta")
    assert notes.read_note(path, key) == "beta"


def test_note_is_encrypted_on_disk(tmp_path, key):
    path = tmp_path / ".pwdnote.enc"
    notes.write_note(path, key, "TOPSECRET")
    assert b"TOPSECRET" not in path.read_bytes()


def test_note_exists(tmp_path, key):
    path = tmp_path / ".pwdnote.enc"
    assert not notes.note_exists(path)
    notes.init_note(path, key)
    assert notes.note_exists(path)
