import json
import os
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from liepin_cli.cli.app import app


runner = CliRunner()


def test_resume_get_requires_token(tmp_path) -> None:
    env = {k: v for k, v in os.environ.items() if k != "LIEPIN_USER_TOKEN"}
    env["XDG_CONFIG_HOME"] = str(tmp_path)
    result = runner.invoke(app, ["resume", "get"], env=env)

    assert result.exit_code == 2
    assert "LIEPIN_USER_TOKEN" in result.stderr
    assert "https://www.liepin.com/mcp/auth" in result.stderr


@patch("liepin_cli.cli.common.run_missing_token_flow")
def test_resume_get_missing_token_offers_setup(mock_flow: Mock, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("LIEPIN_USER_TOKEN", raising=False)
    result = runner.invoke(app, ["resume", "get"])
    assert result.exit_code == 2
    mock_flow.assert_called_once()


@patch("liepin_cli.cli.common.LiepinClient")
def test_resume_get_calls_get_resume(mock_client_cls: Mock, monkeypatch) -> None:
    mock_client = mock_client_cls.return_value
    mock_client.get.return_value = {"resume": "ok"}
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")

    result = runner.invoke(app, ["resume", "get", "--output", "json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"resume": "ok"}
    mock_client.get.assert_called_once_with("/mcp/get-resume")


@patch("liepin_cli.cli.common.LiepinClient")
def test_update_base_info_reads_input_and_flag_override(
    mock_client_cls: Mock, tmp_path, monkeypatch
) -> None:
    path = tmp_path / "base.json"
    path.write_text(
        json.dumps({"realName": "张三", "cityCode": "北京"}), encoding="utf-8"
    )
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")
    mock_client_cls.return_value.post.return_value = None

    result = runner.invoke(
        app,
        [
            "resume",
            "update-base-info",
            "--input",
            str(path),
            "--city-code",
            "上海",
        ],
    )

    assert result.exit_code == 0
    mock_client_cls.return_value.post.assert_called_once_with(
        "/mcp/update-base-info",
        {"realName": "张三", "cityCode": "上海"},
    )


@patch("liepin_cli.cli.common.LiepinClient")
def test_update_base_info_invalid_json_exits_2(
    mock_client_cls: Mock, tmp_path, monkeypatch
) -> None:
    path = tmp_path / "bad.json"
    path.write_text("not json {{{", encoding="utf-8")
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")

    result = runner.invoke(
        app,
        ["resume", "update-base-info", "--input", str(path)],
    )

    assert result.exit_code == 2
    assert "错误：" in result.stderr
    assert "JSON 非法" in result.stderr
    mock_client_cls.return_value.post.assert_not_called()


@patch("liepin_cli.cli.common.LiepinClient")
def test_update_base_info_unknown_input_field_exits_2(
    mock_client_cls: Mock, tmp_path, monkeypatch
) -> None:
    path = tmp_path / "bad-fields.json"
    path.write_text(json.dumps({"real_name": "张三"}), encoding="utf-8")
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")

    result = runner.invoke(
        app,
        ["resume", "update-base-info", "--input", str(path)],
    )

    assert result.exit_code == 2
    assert "错误：" in result.stderr
    mock_client_cls.return_value.post.assert_not_called()


@patch("liepin_cli.cli.common.LiepinClient")
def test_add_work_exp_supports_boolean_flag(mock_client_cls: Mock, monkeypatch) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")
    mock_client_cls.return_value.post.return_value = None

    result = runner.invoke(
        app,
        [
            "resume",
            "add-work-exp",
            "--comp-name",
            "猎聘",
            "--rw-title",
            "后端工程师",
            "--work-start",
            "202301",
            "--work-end",
            "202402",
            "--shield-comp",
        ],
    )

    assert result.exit_code == 0
    mock_client_cls.return_value.post.assert_called_once_with(
        "/mcp/add-work-exp",
        {
            "compName": "猎聘",
            "rwTitle": "后端工程师",
            "workStart": "202301",
            "workEnd": "202402",
            "shieldComp": True,
        },
    )


@patch("liepin_cli.cli.common.LiepinClient")
def test_update_self_assess_posts_required_field(
    mock_client_cls: Mock, monkeypatch
) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")
    mock_client_cls.return_value.post.return_value = None

    result = runner.invoke(
        app,
        [
            "resume",
            "update-self-assess",
            "--self-assess",
            "擅长平台后端设计",
        ],
    )

    assert result.exit_code == 0
    mock_client_cls.return_value.post.assert_called_once_with(
        "/mcp/update-self-assess",
        {"selfAssess": "擅长平台后端设计"},
    )


@patch("liepin_cli.cli.common.LiepinClient")
def test_update_project_exp_posts_id_and_optional_fields(
    mock_client_cls: Mock, monkeypatch
) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")
    mock_client_cls.return_value.post.return_value = None

    result = runner.invoke(
        app,
        [
            "resume",
            "update-project-exp",
            "--id",
            "9",
            "--name",
            "推荐系统重构",
            "--start",
            "202301",
            "--end",
            "202312",
        ],
    )

    assert result.exit_code == 0
    mock_client_cls.return_value.post.assert_called_once_with(
        "/mcp/update-project-exp",
        {
            "id": 9,
            "name": "推荐系统重构",
            "start": "202301",
            "end": "202312",
        },
    )


@patch("liepin_cli.cli.common.LiepinClient")
def test_update_base_info_now_work_status_and_salary_fields(
    mock_client_cls: Mock, monkeypatch
) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")
    mock_client_cls.return_value.post.return_value = None

    result = runner.invoke(
        app,
        [
            "resume",
            "update-base-info",
            "--now-work-status",
            "1",
            "--now-salary",
            "25000",
            "--now-months",
            "14",
        ],
    )

    assert result.exit_code == 0
    mock_client_cls.return_value.post.assert_called_once_with(
        "/mcp/update-base-info",
        {
            "nowWorkStatus": "1",
            "nowSalary": 25000,
            "nowMonths": 14,
        },
    )


@patch("liepin_cli.cli.common.LiepinClient")
def test_add_job_want_salary_and_practice_fields(
    mock_client_cls: Mock, monkeypatch
) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")
    mock_client_cls.return_value.post.return_value = None

    result = runner.invoke(
        app,
        [
            "resume",
            "add-job-want",
            "--jobtitle",
            "Java",
            "--dq",
            "上海",
            "--want-salary-low",
            "20000",
            "--want-salary-high",
            "35000",
            "--want-salary-months",
            "15",
            "--work-type",
            "1",
            "--workweek",
            "5",
            "--practice-months",
            "6",
        ],
    )

    assert result.exit_code == 0
    mock_client_cls.return_value.post.assert_called_once_with(
        "/mcp/add-job-want",
        {
            "jobtitle": "Java",
            "dq": "上海",
            "wantSalaryLow": 20000,
            "wantSalaryHigh": 35000,
            "wantSalaryMonths": 15,
            "workType": "1",
            "workweek": 5,
            "practiceMonths": 6,
        },
    )


@patch("liepin_cli.cli.common.LiepinClient")
def test_add_job_want_repeated_industry_flags(
    mock_client_cls: Mock, monkeypatch
) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")
    mock_client_cls.return_value.post.return_value = None

    result = runner.invoke(
        app,
        [
            "resume",
            "add-job-want",
            "--jobtitle",
            "Java",
            "--dq",
            "上海",
            "--industries",
            "互联网",
            "--industries",
            "金融",
            "--other-expect-dqs",
            "北京",
            "--other-expect-dqs",
            "深圳",
        ],
    )

    assert result.exit_code == 0
    mock_client_cls.return_value.post.assert_called_once_with(
        "/mcp/add-job-want",
        {
            "jobtitle": "Java",
            "dq": "上海",
            "industries": ["互联网", "金融"],
            "otherExpectDqs": ["北京", "深圳"],
        },
    )


def test_resume_get_invalid_output_exits_2(monkeypatch) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")

    result = runner.invoke(app, ["resume", "get", "--output", "xml"])

    assert result.exit_code == 2
    assert "错误：" in result.stderr
    assert "output" in result.stderr.lower()


def test_resume_get_help_is_localized() -> None:
    result = runner.invoke(app, ["resume", "get", "--help"])

    assert result.exit_code == 0
    assert "用法：" in result.stdout
    assert "[选项]" in result.stdout
    assert "获取当前简历" in result.stdout
    assert "--help" not in result.stdout
    assert "--token" not in result.stdout
    assert "--base-url" not in result.stdout
    assert "--timeout" not in result.stdout
    assert "--output" not in result.stdout
    assert "Usage:" not in result.stdout
    assert "Options" not in result.stdout
    assert "Show this message and exit." not in result.stdout


def test_resume_help_lists_user_facing_subcommand_descriptions() -> None:
    result = runner.invoke(app, ["resume", "--help"])

    assert result.exit_code == 0
    assert "查询或更新简历" in result.stdout
    assert "update-base-info" in result.stdout
    assert "更新基础资料" in result.stdout
    assert "update-self-assess" in result.stdout
    assert "更新自我评价" in result.stdout
    assert "add-edu-exp" in result.stdout
    assert "新增教育经历" in result.stdout
    assert "update-work-exp" in result.stdout
    assert "更新工作经历" in result.stdout
    assert "update-job-want" in result.stdout
    assert "更新求职期望" in result.stdout


def test_resume_update_base_info_help_shows_friendly_field_descriptions() -> None:
    result = runner.invoke(app, ["resume", "update-base-info", "--help"])

    assert result.exit_code == 0
    assert "更新基础资料" in result.stdout
    assert "--real-name" in result.stdout
    assert "姓名" in result.stdout
    assert "--sex" in result.stdout
    assert "性别" in result.stdout
    assert "--birthday" in result.stdout
    assert "生日" in result.stdout
    assert "--city-code" in result.stdout
    assert "城市代码" in result.stdout
    assert "--start-job" in result.stdout
    assert "参加工作年份" in result.stdout
    assert "--start-job-month" in result.stdout
    assert "参加工作月份" in result.stdout


def test_resume_add_edu_exp_help_shows_friendly_field_descriptions() -> None:
    result = runner.invoke(app, ["resume", "add-edu-exp", "--help"])

    assert result.exit_code == 0
    assert "新增教育经历" in result.stdout
    assert "--school" in result.stdout
    assert "学校名称" in result.stdout
    assert "--major" in result.stdout
    assert "专业名称" in result.stdout
    assert "--degree" in result.stdout
    assert "学历代码" in result.stdout
    assert "--tz" in result.stdout
    assert "是否统招" in result.stdout
    assert "--experience" in result.stdout
    assert "在校经历" in result.stdout


def test_resume_add_work_exp_help_shows_friendly_field_descriptions() -> None:
    result = runner.invoke(app, ["resume", "add-work-exp", "--help"])

    assert result.exit_code == 0
    assert "新增工作经历" in result.stdout
    assert "--industry" in result.stdout
    assert "所属行业" in result.stdout
    assert "--jobtitle" in result.stdout
    assert "职能名称" in result.stdout
    assert "--dq" in result.stdout
    assert "工作地点" in result.stdout
    assert "--report" in result.stdout
    assert "汇报对象" in result.stdout
    assert "--subordinate" in result.stdout
    assert "下属人数" in result.stdout
    assert "--months" in result.stdout
    assert "薪资月数" in result.stdout
    assert "--shield-comp" in result.stdout
    assert "是否屏蔽公司" in result.stdout


def test_resume_add_job_want_help_shows_friendly_field_descriptions() -> None:
    result = runner.invoke(app, ["resume", "add-job-want", "--help"])

    assert result.exit_code == 0
    assert "新增求职期望" in result.stdout
    assert "--industries" in result.stdout
    assert "期望行业" in result.stdout
    assert "--other-expect-dqs" in result.stdout
    assert "其他期望地点" in result.stdout
    assert "--want-salary-months" in result.stdout
    assert "期望年收入月数" in result.stdout
    assert "--work-type" in result.stdout
    assert "工作类型" in result.stdout
    assert "--workweek" in result.stdout
    assert "每周工作天数" in result.stdout
    assert "--practice-months" in result.stdout
    assert "实习月数" in result.stdout
