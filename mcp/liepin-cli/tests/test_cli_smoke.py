from typer.testing import CliRunner

from liepin_cli.cli.app import app


runner = CliRunner()


def test_root_help_lists_resume_and_job_groups() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "用法：" in result.stdout
    assert "命令" in result.stdout
    assert "resume" in result.stdout
    assert "job" in result.stdout
    assert "skill" in result.stdout
    assert "setup" in result.stdout
    assert "auth" in result.stdout
    assert "首次配置或刷新登录状态" in result.stdout
    assert "管理认证" in result.stdout
    assert "查询或更新简历" in result.stdout
    assert "搜索职位、投递职位" in result.stdout
    assert "--help" not in result.stdout
    assert "--install-completion" not in result.stdout
    assert "--show-completion" not in result.stdout
    assert "Usage:" not in result.stdout
    assert "Commands" not in result.stdout
    assert "Show this message and exit." not in result.stdout


def test_job_help_mentions_apply_command() -> None:
    result = runner.invoke(app, ["job", "--help"])

    assert result.exit_code == 0
    assert "用法：" in result.stdout
    assert "命令" in result.stdout
    assert "search" in result.stdout
    assert "apply" in result.stdout
    assert "搜索职位" in result.stdout
    assert "投递职位" in result.stdout
    assert "--help" not in result.stdout
