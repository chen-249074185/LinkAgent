from unittest.mock import Mock, patch

from typer.testing import CliRunner

from liepin_cli.cli.app import app
from liepin_cli.core.errors import AuthorizationError, RequestError


runner = CliRunner()


@patch("liepin_cli.cli.common.LiepinClient")
def test_job_search_posts_scalar_fields_job_name_address_page(
    mock_client_cls: Mock, monkeypatch
) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")
    mock_client_cls.return_value.post.return_value = {"jobs": []}

    result = runner.invoke(
        app,
        [
            "job",
            "search",
            "--job-name",
            "后端",
            "--address",
            "北京",
            "--page",
            "0",
        ],
    )

    assert result.exit_code == 0
    mock_client_cls.return_value.post.assert_called_once_with(
        "/mcp/search-job",
        {"jobName": "后端", "address": "北京", "page": 0},
    )


@patch("liepin_cli.cli.common.LiepinClient")
def test_job_apply_posts_required_fields_job_id_job_kind(
    mock_client_cls: Mock, monkeypatch
) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")
    mock_client_cls.return_value.post.return_value = {"ok": True}

    result = runner.invoke(
        app,
        [
            "job",
            "apply",
            "--job-id",
            "42",
            "--job-kind",
            "2",
        ],
    )

    assert result.exit_code == 0
    mock_client_cls.return_value.post.assert_called_once_with(
        "/mcp/apply-job",
        {"jobId": 42, "jobKind": "2"},
    )


def test_job_apply_help_is_localized() -> None:
    result = runner.invoke(app, ["job", "apply", "--help"])

    assert result.exit_code == 0
    assert "用法：" in result.stdout
    assert "核心参数" in result.stdout or "选项" in result.stdout
    assert "职位 ID" in result.stdout
    assert "职位类型编号" in result.stdout
    assert "必填" in result.stdout
    assert "--job-id" in result.stdout
    assert "--job-kind" in result.stdout
    assert "--help" not in result.stdout
    assert "--token" not in result.stdout
    assert "--input" not in result.stdout
    assert "--base-url" not in result.stdout
    assert "--timeout" not in result.stdout
    assert "--output" not in result.stdout
    assert "Usage:" not in result.stdout
    assert "Show this message and exit." not in result.stdout


def test_job_search_help_shows_only_user_facing_filters() -> None:
    result = runner.invoke(app, ["job", "search", "--help"])

    assert result.exit_code == 0
    assert "用法：" in result.stdout
    assert "--job-name" in result.stdout
    assert "--address" in result.stdout
    assert "--salary-floor" in result.stdout
    assert "--salary-cap" in result.stdout
    assert "--company-name" in result.stdout
    assert "职位关键词" in result.stdout
    assert "工作地点" in result.stdout
    assert "最低薪资" in result.stdout
    assert "最高薪资" in result.stdout
    assert "公司名称" in result.stdout
    assert "工作经验要求" in result.stdout
    assert "公司性质或类型" in result.stdout
    assert "结果页码" in result.stdout
    assert "首页通常为 0" in result.stdout
    assert "--help" not in result.stdout
    assert "--token" not in result.stdout
    assert "--input" not in result.stdout
    assert "--base-url" not in result.stdout
    assert "--timeout" not in result.stdout
    assert "--output" not in result.stdout
    assert "Usage:" not in result.stdout
    assert "Show this message and exit." not in result.stdout


@patch("liepin_cli.cli.common.LiepinClient")
def test_job_apply_request_error_exits_1(mock_client_cls: Mock, monkeypatch) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")
    mock_client_cls.return_value.post.side_effect = RequestError(
        "request failed with status 500"
    )

    result = runner.invoke(
        app,
        [
            "job",
            "apply",
            "--job-id",
            "42",
            "--job-kind",
            "2",
        ],
    )

    assert result.exit_code == 1
    assert "request failed with status 500" in result.stderr


@patch("liepin_cli.cli.common.run_authorization_recovery")
@patch("liepin_cli.cli.common.LiepinClient")
def test_job_apply_authorization_error_offers_reauth(
    mock_client_cls: Mock, mock_recover: Mock, monkeypatch
) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")
    mock_client_cls.return_value.post.side_effect = AuthorizationError("token expired")
    result = runner.invoke(
        app,
        [
            "job",
            "apply",
            "--job-id",
            "1",
            "--job-kind",
            "2",
        ],
    )
    assert result.exit_code == 1
    mock_recover.assert_called_once()
