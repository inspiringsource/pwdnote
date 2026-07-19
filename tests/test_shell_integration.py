import os
import shlex
import shutil
import subprocess

import pytest
from pwdnote import cli, shell_integration
from typer.testing import CliRunner


runner = CliRunner()


def _configure_shell_home(monkeypatch, home, shell="/bin/zsh"):
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("SHELL", shell)
    monkeypatch.delenv("PWDNOTE_CONFIG_DIR", raising=False)
    return home


@pytest.fixture
def shell_home(tmp_path, monkeypatch):
    return _configure_shell_home(monkeypatch, tmp_path / "home")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("zsh", "zsh"),
        ("/bin/zsh", "zsh"),
        ("/usr/local/bin/zsh", "zsh"),
        ("/usr/bin/bash", "bash"),
        ("fish", "fish"),
        ("powershell", "powershell"),
        ("pwsh", "pwsh"),
        (r"C:\Program Files\PowerShell\7\pwsh.exe", "pwsh"),
        ("/bin/tcsh", None),
        ("", None),
        (None, None),
    ],
)
def test_shell_name_normalization(value, expected):
    assert shell_integration.normalize_shell(value) == expected


def test_shell_print_zsh_outputs_canonical_portable_code():
    result = runner.invoke(cli.app, ["shell", "print", "zsh"])

    assert result.exit_code == 0
    assert result.stdout == shell_integration.render_zsh_integration()
    assert "pwdnote()" in result.stdout
    assert 'command pwdnote cat "$@"' in result.stdout
    assert 'command pwdnote "$@"' in result.stdout
    assert 'print -z -- "$item"' in result.stdout
    for forbidden in (
        "eval",
        "pbcopy",
        "AppleScript",
        "osascript",
        "Terminal.app",
        "iTerm",
        "/Users/",
    ):
        assert forbidden not in result.stdout


def test_shell_print_without_argument_detects_zsh(shell_home):
    result = runner.invoke(cli.app, ["shell", "print"])

    assert result.exit_code == 0
    assert result.stdout == shell_integration.render_zsh_integration()
    assert result.stderr == ""


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
def test_zsh_wrapper_inserts_without_execution_and_delegates_commands(tmp_path):
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
        f"source {shlex.quote(str(integration))}\n"
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


def test_explicit_zsh_install_creates_file_and_managed_block(shell_home):
    zshrc = shell_home / ".zshrc"
    zshrc.write_text("export KEEP_ME=yes\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["shell", "install", "zsh"])

    integration = shell_home / ".config" / "pwdnote" / "shell" / "pwdnote.zsh"
    assert result.exit_code == 0
    assert result.stderr == ""
    assert "Installed pwdnote Zsh integration." in result.stdout
    assert integration.read_text(encoding="utf-8") == (
        shell_integration.render_zsh_integration()
    )
    content = zshrc.read_text(encoding="utf-8")
    assert "export KEEP_ME=yes\n" in content
    assert content.count(shell_integration.MANAGED_BLOCK_START) == 1
    assert content.count(shell_integration.MANAGED_BLOCK_END) == 1
    assert ".bashrc" not in content


def test_explicit_zsh_install_from_bash_warns_but_succeeds(shell_home, monkeypatch):
    monkeypatch.setenv("SHELL", "/usr/bin/bash")

    result = runner.invoke(cli.app, ["shell", "install", "zsh"])

    assert result.exit_code == 0
    assert "Zsh does not appear to be your configured shell" in result.stderr
    assert shell_integration.is_installed()


def test_explicit_install_honors_xdg_and_paths_with_spaces(tmp_path, monkeypatch):
    home = _configure_shell_home(monkeypatch, tmp_path / "home with spaces")

    first = runner.invoke(cli.app, ["shell", "install", "/bin/zsh"])
    second = runner.invoke(cli.app, ["shell", "install", "zsh"])

    integration = (
        home / ".config" / "pwdnote" / "shell" / "pwdnote.zsh"
    ).resolve()
    assert first.exit_code == second.exit_code == 0
    assert f"source {shlex.quote(str((home / '.zshrc').resolve()))}" in first.stdout
    assert shell_integration.get_integration_path() == integration
    zshrc = (home / ".zshrc").read_text(encoding="utf-8")
    assert zshrc.count(shell_integration.MANAGED_BLOCK_START) == 1
    assert f"source {shlex.quote(str(integration))}" in zshrc


def test_reinstall_refreshes_file_and_migrates_legacy_block(shell_home):
    zshrc = shell_home / ".zshrc"
    zshrc.write_text(
        "export KEEP_ME=yes\n"
        "# >>> pwdnote shell integration >>>\n"
        "source /old/pwdnote.zsh\n"
        "# <<< pwdnote shell integration <<<\n",
        encoding="utf-8",
    )
    integration = shell_integration.get_integration_path()
    integration.parent.mkdir(parents=True)
    integration.write_text("stale\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["shell", "install", "zsh"])

    assert result.exit_code == 0
    assert integration.read_text(encoding="utf-8") == (
        shell_integration.render_zsh_integration()
    )
    content = zshrc.read_text(encoding="utf-8")
    assert "pwdnote shell integration" not in content
    assert content.count(shell_integration.MANAGED_BLOCK_START) == 1
    assert "export KEEP_ME=yes\n" in content


def test_automatic_install_detects_zsh(shell_home):
    result = runner.invoke(cli.app, ["shell", "install"])

    assert result.exit_code == 0
    assert "Detected Zsh." in result.stdout
    assert shell_integration.is_installed()


def test_automatic_install_detects_bash_and_modifies_nothing(shell_home, monkeypatch):
    monkeypatch.setenv("SHELL", "/usr/bin/bash")
    bashrc = shell_home / ".bashrc"
    bashrc.write_text("export KEEP_ME=yes\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["shell", "install"])

    assert result.exit_code != 0
    assert result.stdout == ""
    assert "available only for Zsh" in result.stderr
    assert "appears to be Bash" in result.stderr
    assert "pwdnote cat" in result.stderr
    assert "pwdnote copy" in result.stderr
    assert bashrc.read_text(encoding="utf-8") == "export KEEP_ME=yes\n"
    assert not (shell_home / ".zshrc").exists()
    assert not shell_integration.get_integration_path().exists()


def test_automatic_install_unknown_shell_modifies_nothing(shell_home, monkeypatch):
    monkeypatch.setenv("SHELL", "/bin/tcsh")

    result = runner.invoke(cli.app, ["shell", "install"])

    assert result.exit_code != 0
    assert "could not determine a supported shell" in result.stderr
    assert "pwdnote shell install zsh" in result.stderr
    assert not (shell_home / ".zshrc").exists()
    assert not shell_integration.get_integration_path().exists()


@pytest.mark.parametrize(
    ("shell_name", "display"),
    [
        ("bash", "Bash"),
        ("fish", "Fish"),
        ("powershell", "PowerShell"),
        ("pwsh", "PowerShell"),
    ],
)
def test_explicit_unsupported_install_fails_without_shell_file_changes(
    shell_home, shell_name, display
):
    bashrc = shell_home / ".bashrc"
    bashrc.write_text("unchanged\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["shell", "install", shell_name])

    assert result.exit_code != 0
    assert f"not currently available for {display}" in result.stderr
    assert "pwdnote cat" in result.stderr
    assert "pwdnote copy" in result.stderr
    assert bashrc.read_text(encoding="utf-8") == "unchanged\n"
    assert not (shell_home / ".zshrc").exists()
    assert not (shell_home / ".config").exists()


@pytest.mark.parametrize("command", ["print", "status", "uninstall"])
def test_unsupported_shell_management_commands_do_not_modify_files(
    shell_home, command
):
    bashrc = shell_home / ".bashrc"
    bashrc.write_text("unchanged\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["shell", command, "bash"])

    assert result.exit_code != 0
    assert result.stdout == ""
    assert "not currently available for Bash" in result.stderr
    assert bashrc.read_text(encoding="utf-8") == "unchanged\n"
    assert not (shell_home / ".zshrc").exists()


def test_zsh_status_reports_complete_installation(shell_home):
    runner.invoke(cli.app, ["shell", "install", "zsh"])

    result = runner.invoke(cli.app, ["shell", "status", "zsh"])

    assert result.exit_code == 0
    assert result.stdout == (
        "pwdnote Zsh integration is installed.\n"
        "Integration file: present\n"
        ".zshrc source block: present\n"
    )


@pytest.mark.parametrize(
    ("missing_piece", "file_status", "block_status"),
    [
        ("file", "missing", "present"),
        ("block", "present", "missing"),
        ("stale", "out of date", "present"),
    ],
)
def test_zsh_status_reports_incomplete_installation(
    shell_home, missing_piece, file_status, block_status
):
    runner.invoke(cli.app, ["shell", "install", "zsh"])
    if missing_piece == "file":
        shell_integration.get_integration_path().unlink()
    elif missing_piece == "block":
        (shell_home / ".zshrc").write_text("export KEEP_ME=yes\n", encoding="utf-8")
    else:
        shell_integration.get_integration_path().write_text("stale\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["shell", "status", "zsh"])

    assert result.exit_code != 0
    assert "pwdnote Zsh integration is incomplete." in result.stdout
    assert f"Integration file: {file_status}" in result.stdout
    assert f".zshrc source block: {block_status}" in result.stdout
    assert "pwdnote shell install zsh" in result.stdout


def test_zsh_uninstall_removes_only_managed_content_and_is_idempotent(shell_home):
    zshrc = shell_home / ".zshrc"
    zshrc.write_text("export KEEP_ME=yes\n", encoding="utf-8")
    runner.invoke(cli.app, ["shell", "install", "zsh"])

    first = runner.invoke(cli.app, ["shell", "uninstall", "zsh"])
    second = runner.invoke(cli.app, ["shell", "uninstall", "zsh"])

    assert first.exit_code == second.exit_code == 0
    assert "Removed pwdnote Zsh integration." in first.stdout
    assert "was not installed" in second.stdout
    assert zshrc.read_text(encoding="utf-8") == "export KEEP_ME=yes\n"
    assert not shell_integration.get_integration_path().exists()
    assert not shell_integration.get_integration_path().parent.exists()


def test_shell_support_distinguishes_shell_and_command_support():
    result = runner.invoke(cli.app, ["shell", "support"])

    assert result.exit_code == 0
    assert "Zsh         Supported on macOS and Linux" in result.stdout
    assert "Bash        Not currently supported" in result.stdout
    assert "Fish        Not currently supported" in result.stdout
    assert "PowerShell  Not currently supported" in result.stdout
    assert "pwdnote cat" in result.stdout
    assert "pwdnote copy" in result.stdout


def test_shell_help_lists_commands_arguments_and_examples():
    result = runner.invoke(cli.app, ["shell", "--help"])

    assert result.exit_code == 0
    for command in ("install", "status", "uninstall", "print", "support"):
        assert command in result.stdout
        command_help = runner.invoke(cli.app, ["shell", command, "--help"])
        assert command_help.exit_code == 0
    assert "pwdnote shell install zsh" in runner.invoke(
        cli.app, ["shell", "install", "--help"]
    ).stdout
    assert "pwdnote shell status zsh" in runner.invoke(
        cli.app, ["shell", "status", "--help"]
    ).stdout
