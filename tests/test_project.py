from pwdnote import project


def test_find_in_current_directory(tmp_path):
    note = tmp_path / ".pwdnote.enc"
    note.write_bytes(b"x")
    assert project.find_existing_note(tmp_path) == note


def test_find_in_nested_directory(tmp_path):
    note = tmp_path / ".pwdnote.enc"
    note.write_bytes(b"x")
    nested = tmp_path / "backend" / "api"
    nested.mkdir(parents=True)
    assert project.find_existing_note(nested) == note


def test_git_root_detection(tmp_path):
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "backend" / "api"
    nested.mkdir(parents=True)
    assert project.find_git_root(nested) == tmp_path
    assert project.resolve_project_root(nested) == tmp_path


def test_filesystem_root_returns_none(tmp_path):
    nested = tmp_path / "deep"
    nested.mkdir()
    assert project.find_existing_note(nested) is None
    assert project.find_git_root(nested) is None
    assert project.resolve_project_root(nested) == nested.resolve()


def test_existing_note_preferred_over_git(tmp_path):
    (tmp_path / ".git").mkdir()
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / ".pwdnote.enc").write_bytes(b"x")
    assert project.resolve_project_root(sub) == sub.resolve()


def test_note_path_for(tmp_path):
    assert project.note_path_for(tmp_path) == tmp_path / ".pwdnote.enc"
