from pathlib import Path

from typer.testing import CliRunner

from liepin_cli.cli.app import app

runner = CliRunner()

_REPO = Path(__file__).resolve().parents[1]


def test_skill_install_help_lists_install_command() -> None:
    result = runner.invoke(app, ["skill", "--help"])
    assert result.exit_code == 0
    assert "install" in result.stdout


def test_skill_install_cli_global_writes_user_cursor(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    result = runner.invoke(
        app,
        ["skill", "install", "--repo-root", str(_REPO), "-g"],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    dest = tmp_path / ".cursor" / "skills" / "liepin-cli" / "SKILL.md"
    assert dest.exists()
