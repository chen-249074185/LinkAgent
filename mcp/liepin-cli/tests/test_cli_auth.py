from unittest.mock import Mock, patch

from typer.testing import CliRunner

from liepin_cli.cli.app import app
from liepin_cli.core.auth_store import save_token
from liepin_cli.core.errors import AuthorizationError


runner = CliRunner()


def test_root_help_mentions_setup_and_auth() -> None:
    result = runner.invoke(app, ["--help"])
    assert "setup" in result.stdout
    assert "auth" in result.stdout
    assert "猎聘简历与职位 CLI" in result.stdout


def test_auth_status_reports_missing_config(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 0
    assert "没有已保存的 token" in result.stdout


def test_auth_status_shows_masked_token_when_present(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save_token("x-user-token-abcdef")
    result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 0
    assert "已保存 token：" in result.stdout
    assert "****" in result.stdout


def test_auth_status_handles_malformed_config(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_dir = tmp_path / "liepin-cli"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{bad json", encoding="utf-8")
    result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 2
    assert "错误：" in result.stderr
    assert "CLI 配置文件无效" in result.stderr


def test_auth_clear_when_no_token(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    result = runner.invoke(app, ["auth", "clear"])
    assert result.exit_code == 0
    assert "没有可清除的已保存 token" in result.stdout


def test_auth_clear_when_token_present(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save_token("x-user-token-abc")
    result = runner.invoke(app, ["auth", "clear"])
    assert result.exit_code == 0
    assert "已清除保存的 token" in result.stdout


def test_auth_clear_handles_malformed_config(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_dir = tmp_path / "liepin-cli"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{bad json", encoding="utf-8")
    result = runner.invoke(app, ["auth", "clear"])
    assert result.exit_code == 2
    assert "错误：" in result.stderr
    assert "CLI 配置文件无效" in result.stderr


def test_auth_open_prints_success(monkeypatch) -> None:
    monkeypatch.setattr("liepin_cli.core.browser.webbrowser.open", lambda url: True)
    result = runner.invoke(app, ["auth", "open"])
    assert result.exit_code == 0
    assert "已打开猎聘授权页面" in result.stdout


def test_auth_open_browser_failure_uses_cli_error_path(monkeypatch) -> None:
    monkeypatch.setattr("liepin_cli.core.browser.webbrowser.open", lambda url: False)
    result = runner.invoke(app, ["auth", "open"])
    assert result.exit_code == 2
    assert "错误：" in result.stderr
    assert "打开授权页面失败" in result.stderr


@patch("liepin_cli.cli.auth.LiepinClient")
def test_verify_token_with_resume_get_calls_get(mock_client_cls: Mock) -> None:
    from liepin_cli.cli.auth import verify_token_with_resume_get

    verify_token_with_resume_get("tok-123")
    mock_client_cls.return_value.get.assert_called_once_with("/mcp/get-resume")


def test_setup_invokes_same_flow_as_auth_setup(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    calls: list[str] = []

    def fake_run(*, verifier) -> str | None:
        calls.append("run")
        return "t"

    monkeypatch.setattr("liepin_cli.cli.auth.run_auth_setup", fake_run)

    result = runner.invoke(app, ["setup"])
    assert result.exit_code == 0
    assert calls == ["run"]


def test_auth_setup_invokes_same_flow(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    calls: list[str] = []

    def fake_run(*, verifier) -> str | None:
        calls.append("run")
        return "t"

    monkeypatch.setattr("liepin_cli.cli.auth.run_auth_setup", fake_run)

    result = runner.invoke(app, ["auth", "setup"])
    assert result.exit_code == 0
    assert calls == ["run"]


@patch("liepin_cli.cli.auth.LiepinClient")
def test_setup_returns_cli_error_when_token_verification_fails(
    mock_client_cls: Mock, monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr("liepin_cli.core.onboarding.is_interactive_terminal", lambda: True)
    monkeypatch.setattr("liepin_cli.core.onboarding.confirm_open_auth_page", lambda: False)
    monkeypatch.setattr("liepin_cli.core.onboarding.prompt_for_token", lambda: "x-user-token-bad")
    mock_client_cls.return_value.get.side_effect = AuthorizationError("token expired")

    result = runner.invoke(app, ["setup"])
    assert result.exit_code == 1
    assert "授权失败" in result.stderr
    assert "错误：token expired" in result.stderr


def test_setup_non_interactive_exits_non_zero(monkeypatch) -> None:
    monkeypatch.setattr("liepin_cli.cli.auth.run_auth_setup", lambda *, verifier: None)
    monkeypatch.setattr("liepin_cli.cli.auth.is_interactive_terminal", lambda: False)

    result = runner.invoke(app, ["setup"])
    assert result.exit_code == 2
    assert "错误：setup 需要支持粘贴输入的交互式终端" in result.stderr


def test_setup_interactive_no_token_exits_with_distinct_message(monkeypatch) -> None:
    monkeypatch.setattr("liepin_cli.cli.auth.run_auth_setup", lambda *, verifier: None)
    monkeypatch.setattr("liepin_cli.cli.auth.is_interactive_terminal", lambda: True)

    result = runner.invoke(app, ["setup"])
    assert result.exit_code == 2
    assert "错误：未收到 token" in result.stderr
    assert "liepin-cli auth open" in result.stderr


@patch("liepin_cli.cli.common.run_authorization_recovery")
@patch("liepin_cli.cli.common.LiepinClient")
def test_resume_get_authorization_error_offers_reauth(
    mock_client_cls: Mock, mock_recover: Mock, monkeypatch
) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")
    mock_client_cls.return_value.get.side_effect = AuthorizationError("token expired")
    result = runner.invoke(app, ["resume", "get"])
    assert result.exit_code == 1
    mock_recover.assert_called_once()


def test_auth_help_is_localized() -> None:
    result = runner.invoke(app, ["auth", "--help"])
    assert result.exit_code == 0
    assert "用法：" in result.stdout
    assert "命令" in result.stdout
    assert "管理认证" in result.stdout
    assert "查看当前登录状态" in result.stdout
    assert "清除当前认证信息" in result.stdout
    assert "打开认证相关页面" in result.stdout
    assert "设置或更新认证" in result.stdout
    assert "--help" not in result.stdout
    assert "Usage:" not in result.stdout
    assert "Commands" not in result.stdout
