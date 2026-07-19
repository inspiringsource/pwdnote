import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest
from pwdnote import cli, shell_integration
from typer.testing import CliRunner


runner = CliRunner()


@pytest.fixture
def shell_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.delenv("PWDNOTE_CONFIG_DIR", raising=False)
    return home


def test_shell_print_outputs_canonical_safe_zsh_code():
    result = runner.invoke(cli.app, ["shell", "print"])

    assert result.exit_code == 0
    assert result.stdout == shell_integration.render_zsh_integration()
    assert "pwdnote()" in result.stdout
    assert '"paste"' in result.stdout
    assert '"p"' in result.stdout
    assert 'command pwdnote cat "$@"' in result.stdout
    assert 'command pwdnote "$@"' in result.stdout
    assert 'print -z -- "$item"' in result.stdout
    assert "eval" not in result.stdout


@pytest.mark.skipif(shutil.which("zsh") is None, reason="Zsh is not installed")
def test_generated_integration_is_valid_zsh():
    result = subprocess.run(
        ["zsh", "-n"],
        input=shell_integration.render_zsh_integration(),
        text=True,
        check=False,
        capture_output=True,
    )

    assert result.returncode == 0
    assert result.stderr == ""


@pytest.mark.skipif(shutil.which("zsh") is None, reason="Zsh is not installed")
def test_zsh_wrapper_inserts_paste_and_p_but_delegates_other_commands(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker = tmp_path / "executed"
    selected = f"touch {marker}"
    fake_pwdnote = bin_dir / "pwdnote"
    fake_pwdnote.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "cat" ]; then\n'
        f"    printf '%s\\n' {shlex.quote(selected)}\n"
        "else\n"
        '    printf \'delegated:%s\\n\' "$*"\n'
        "fi\n",
        encoding="utf-8",
    )
    fake_pwdnote.chmod(0o700)
    integration = tmp_path / "pwdnote.zsh"
    integration.write_text(shell_integration.render_zsh_integration(), encoding="utf-8")
    script = (
        f"source {integration}\n"
        "pwdnote paste 2\n"
        "read -z first\n"
        "pwdnote p first\n"
        "read -z second\n"
        'print -r -- "inserted:$first"\n'
        'print -r -- "alias:$second"\n'
        "pwdnote copy 2\n"
        "pwdnote status\n"
    )
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"

    result = subprocess.run(
        ["zsh", "-f"],
        input=script,
        text=True,
        check=False,
        capture_output=True,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        f"inserted:{selected}",
        f"alias:{selected}",
        "delegated:copy 2",
        "delegated:status",
    ]
    assert result.stderr == ""
    assert not marker.exists()


def test_shell_install_creates_file_and_one_managed_block(shell_home):
    zshrc = shell_home / ".zshrc"
    zshrc.write_text("export KEEP_ME=yes\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["shell", "install"])

    integration = shell_home / ".config" / "pwdnote" / "shell" / "pwdnote.zsh"
    assert result.exit_code == 0
    assert "Installed pwdnote Zsh integration." in result.stdout
    assert integration.read_text(encoding="utf-8") == (
        shell_integration.render_zsh_integration()
    )
    content = zshrc.read_text(encoding="utf-8")
    assert "export KEEP_ME=yes\n" in content
    assert content.count(shell_integration.MANAGED_BLOCK_START) == 1
    assert content.count(shell_integration.MANAGED_BLOCK_END) == 1
    assert f"source {integration}" in content


def test_shell_install_is_idempotent_and_refreshes_generated_file(shell_home):
    first = runner.invoke(cli.app, ["shell", "install"])
    integration = shell_integration.get_integration_path()
    integration.write_text("stale integration\n", encoding="utf-8")

    second = runner.invoke(cli.app, ["shell", "install"])

    assert first.exit_code == second.exit_code == 0
    assert integration.read_text(encoding="utf-8") == (
        shell_integration.render_zsh_integration()
    )
    zshrc = (shell_home / ".zshrc").read_text(encoding="utf-8")
    assert zshrc.count(shell_integration.MANAGED_BLOCK_START) == 1
    assert zshrc.count(shell_integration.MANAGED_BLOCK_END) == 1


def test_shell_install_honors_xdg_and_creates_missing_zshrc(shell_home):
    result = runner.invoke(cli.app, ["shell", "install"])

    assert result.exit_code == 0
    assert (shell_home / ".zshrc").is_file()
    assert shell_integration.get_integration_path() == (
        shell_home / ".config" / "pwdnote" / "shell" / "pwdnote.zsh"
    ).resolve()


def test_shell_install_warns_but_does_not_block_other_current_shells(
    shell_home, monkeypatch
):
    monkeypatch.setenv("SHELL", "/bin/bash")

    result = runner.invoke(cli.app, ["shell", "install"])

    assert result.exit_code == 0
    assert "Warning:" in result.stderr
    assert shell_integration.is_installed()


def test_shell_status_reports_complete_installation(shell_home):
    runner.invoke(cli.app, ["shell", "install"])

    result = runner.invoke(cli.app, ["shell", "status"])

    assert result.exit_code == 0
    assert result.stdout == "pwdnote Zsh integration is installed.\n"


@pytest.mark.parametrize("missing_piece", ["file", "block"])
def test_shell_status_fails_for_incomplete_installation(shell_home, missing_piece):
    runner.invoke(cli.app, ["shell", "install"])
    if missing_piece == "file":
        shell_integration.get_integration_path().unlink()
    else:
        (shell_home / ".zshrc").write_text("export KEEP_ME=yes\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["shell", "status"])

    assert result.exit_code != 0
    assert result.stdout == ""
    assert "pwdnote Zsh integration is not installed." in result.stderr
    assert "pwdnote shell install" in result.stderr


def test_shell_uninstall_removes_only_managed_content_and_is_idempotent(shell_home):
    zshrc = shell_home / ".zshrc"
    zshrc.write_text("export KEEP_ME=yes\n", encoding="utf-8")
    runner.invoke(cli.app, ["shell", "install"])

    first = runner.invoke(cli.app, ["shell", "uninstall"])
    second = runner.invoke(cli.app, ["shell", "uninstall"])

    assert first.exit_code == second.exit_code == 0
    assert "Removed pwdnote Zsh integration." in first.stdout
    assert "was not installed" in second.stdout
    assert zshrc.read_text(encoding="utf-8") == "export KEEP_ME=yes\n"
    assert not shell_integration.get_integration_path().exists()
    assert not shell_integration.get_integration_path().parent.exists()


def test_shell_help_lists_management_commands():
    result = runner.invoke(cli.app, ["shell", "--help"])

    assert result.exit_code == 0
    for command in ("install", "status", "uninstall", "print"):
        assert command in result.stdout
        command_help = runner.invoke(cli.app, ["shell", command, "--help"])
        assert command_help.exit_code == 0
