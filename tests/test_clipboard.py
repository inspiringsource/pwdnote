import subprocess
from unittest.mock import Mock

import pytest

from pwdnote import clipboard


@pytest.mark.parametrize(
    ("platform", "available", "expected"),
    [
        ("darwin", "pbcopy", ["/mock/pbcopy"]),
        ("win32", "clip", ["/mock/clip"]),
    ],
)
def test_native_clipboard_backend_passes_plaintext_through_stdin(
    monkeypatch, platform, available, expected
):
    run = Mock()
    monkeypatch.setattr(clipboard.sys, "platform", platform)
    monkeypatch.setattr(
        clipboard.shutil,
        "which",
        lambda name: f"/mock/{name}" if name == available else None,
    )
    monkeypatch.setattr(clipboard.subprocess, "run", run)

    clipboard.copy_to_clipboard("git status")

    run.assert_called_once_with(
        expected,
        input="git status",
        text=True,
        check=True,
        capture_output=True,
        shell=False,
    )
    assert "git status" not in run.call_args.args[0]


@pytest.mark.parametrize(
    ("available", "expected", "discovery"),
    [
        ("wl-copy", ["/mock/wl-copy"], ["wl-copy"]),
        (
            "xclip",
            ["/mock/xclip", "-selection", "clipboard"],
            ["wl-copy", "xclip"],
        ),
        (
            "xsel",
            ["/mock/xsel", "--clipboard", "--input"],
            ["wl-copy", "xclip", "xsel"],
        ),
    ],
)
def test_linux_clipboard_backend_selection(
    monkeypatch, available, expected, discovery
):
    checked: list[str] = []
    run = Mock()

    def which(name: str) -> str | None:
        checked.append(name)
        return f"/mock/{name}" if name == available else None

    monkeypatch.setattr(clipboard.sys, "platform", "linux")
    monkeypatch.setattr(clipboard.shutil, "which", which)
    monkeypatch.setattr(clipboard.subprocess, "run", run)

    clipboard.copy_to_clipboard("echo café")

    assert checked == discovery
    assert run.call_args.args[0] == expected
    assert run.call_args.kwargs["input"] == "echo café"
    assert "echo café" not in run.call_args.args[0]
    assert run.call_args.kwargs["shell"] is False


def test_linux_falls_back_when_an_installed_backend_fails(monkeypatch):
    failed = subprocess.CalledProcessError(1, ["/mock/wl-copy"])
    run = Mock(side_effect=[failed, None])
    monkeypatch.setattr(clipboard.sys, "platform", "linux")
    monkeypatch.setattr(clipboard.shutil, "which", lambda name: f"/mock/{name}")
    monkeypatch.setattr(clipboard.subprocess, "run", run)

    clipboard.copy_to_clipboard("git status")

    assert run.call_count == 2
    assert run.call_args_list[0].args[0] == ["/mock/wl-copy"]
    assert run.call_args_list[1].args[0] == [
        "/mock/xclip",
        "-selection",
        "clipboard",
    ]


def test_missing_linux_backend_fails_clearly(monkeypatch):
    monkeypatch.setattr(clipboard.sys, "platform", "linux")
    monkeypatch.setattr(clipboard.shutil, "which", lambda name: None)

    with pytest.raises(clipboard.ClipboardUnavailableError) as exc_info:
        clipboard.copy_to_clipboard("git status")

    assert "Install wl-clipboard, xclip, or xsel." in str(exc_info.value)


def test_installed_backend_failures_raise_clipboard_error(monkeypatch):
    monkeypatch.setattr(clipboard.sys, "platform", "darwin")
    monkeypatch.setattr(clipboard.shutil, "which", lambda name: "/mock/pbcopy")
    monkeypatch.setattr(
        clipboard.subprocess,
        "run",
        Mock(side_effect=OSError("backend failed")),
    )

    with pytest.raises(clipboard.ClipboardCommandError) as exc_info:
        clipboard.copy_to_clipboard("sensitive item")

    assert "sensitive item" not in str(exc_info.value)
