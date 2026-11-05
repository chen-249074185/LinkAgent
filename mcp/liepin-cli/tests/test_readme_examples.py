import json
import re
from pathlib import Path
from unittest.mock import Mock, patch

import typer.main
from typer.testing import CliRunner

from liepin_cli.cli.app import app
from liepin_cli.models.job import ApplyJobInput, SearchJobInput
from liepin_cli.models.resume import AddJobWantInput, AddWorkExpInput, UpdateBaseInfoInput
from liepin_cli.readme_examples import (
    extract_fenced_block_after_label,
    extract_shell_commands_after_marker,
)


runner = CliRunner()

_REPO_ROOT = Path(__file__).resolve().parent.parent
README_PATH = str(_REPO_ROOT / "README.md")


def _find_command(commands: list[list[str]], prefix: list[str]) -> list[str]:
    for command in commands:
        if command[: len(prefix)] == prefix:
            return command
    raise AssertionError(f"Could not find README command starting with {prefix!r}")


def _parse_command_overview_table(readme: str, heading: str) -> list[dict[str, str]]:
    # Header cells may use alignment padding; separator is a full markdown table line.
    pattern = (
        rf"{re.escape(heading)}\n\n"
        r"\|\s*命令\s*\|\s*用途\s*\|\s*常见关键参数\s*\|\s*是否支持 `--input`\s*\|\n"
        r"\|[^\n]+\n"
        r"((?:\|.*\n)+)"
    )
    match = re.search(pattern, readme)
    if not match:
        raise AssertionError(f"Could not find README table for {heading!r}")

    rows: list[dict[str, str]] = []
    for line in match.group(1).strip().splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append(
            {
                "command": cells[0],
                "description": cells[1],
                "common_args": cells[2],
                "supports_input": cells[3],
            }
        )
    return rows


def _registered_group_commands(group_name: str) -> dict[str, bool]:
    root = typer.main.get_command(app)
    group = root.commands[group_name]
    commands: dict[str, bool] = {}
    for name, command in group.commands.items():
        option_names = {
            opt
            for param in command.params
            for opt in getattr(param, "opts", [])
        }
        commands[f"`liepin-cli {group_name} {name}`"] = "--input" in option_names
    return commands


def test_readme_payload_examples_validate_against_models() -> None:
    payload_examples = [
        ("`payloads/base-info.json`", UpdateBaseInfoInput),
        ("`payloads/add-work-exp.json`", AddWorkExpInput),
        ("`payloads/add-job-want.json`", AddJobWantInput),
        ("`payloads/search-job.json`", SearchJobInput),
        ("`payloads/apply-job.json`", ApplyJobInput),
    ]

    for label, model_cls in payload_examples:
        payload_text = extract_fenced_block_after_label(README_PATH, label, "json")
        payload = json.loads(payload_text)
        model = model_cls.model_validate(payload)
        assert model.model_dump(exclude_none=True) == payload


@patch("liepin_cli.cli.common.LiepinClient")
def test_readme_core_command_examples_succeed(mock_client_cls: Mock, monkeypatch) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")
    mock_client = mock_client_cls.return_value
    mock_client.get.return_value = {"resume": "ok"}
    mock_client.post.return_value = {"ok": True}

    commands = extract_shell_commands_after_marker(README_PATH, "## 示例")
    command_prefixes = {tuple(args[:2]) for args in commands}

    assert {
        ("resume", "get"),
        ("job", "search"),
        ("job", "apply"),
        ("resume", "update-base-info"),
    }.issubset(command_prefixes)

    get_args = _find_command(commands, ["resume", "get"])
    result = runner.invoke(app, get_args)
    assert result.exit_code == 0, result.stdout
    mock_client.get.assert_called_once_with("/mcp/get-resume")

    search_args = _find_command(commands, ["job", "search"])
    mock_client.post.reset_mock()
    result = runner.invoke(app, search_args)
    assert result.exit_code == 0, result.stdout
    assert mock_client.post.call_args.args == (
        "/mcp/search-job",
        {"jobName": "Python开发", "address": "北京", "page": 0},
    )

    apply_args = _find_command(commands, ["job", "apply"])
    mock_client.post.reset_mock()
    result = runner.invoke(app, apply_args)
    assert result.exit_code == 0, result.stdout
    assert mock_client.post.call_args.args == (
        "/mcp/apply-job",
        {"jobId": 123456, "jobKind": "2"},
    )

    update_base_info_args = _find_command(commands, ["resume", "update-base-info"])
    mock_client.post.reset_mock()
    result = runner.invoke(app, update_base_info_args)
    assert result.exit_code == 0, result.stdout
    assert mock_client.post.call_args.args == (
        "/mcp/update-base-info",
        {"realName": "张三", "sex": "男", "birthday": "19950101"},
    )


@patch("liepin_cli.cli.common.LiepinClient")
def test_readme_input_example_uses_extracted_payload_file(
    mock_client_cls: Mock, monkeypatch
) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")
    mock_client = mock_client_cls.return_value
    mock_client.post.return_value = {"ok": True}

    commands = extract_shell_commands_after_marker(README_PATH, "你可以这样调用：")
    command_prefixes = {tuple(args[:2]) for args in commands}

    assert {
        ("resume", "update-base-info"),
        ("resume", "add-work-exp"),
        ("resume", "add-job-want"),
        ("job", "search"),
        ("job", "apply"),
    }.issubset(command_prefixes)

    args = _find_command(commands, ["job", "search"])
    payload_text = extract_fenced_block_after_label(
        README_PATH, "`payloads/search-job.json`", "json"
    )
    expected_payload = json.loads(payload_text)

    with runner.isolated_filesystem():
        payload_path = Path("payloads/search-job.json")
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        payload_path.write_text(payload_text, encoding="utf-8")

        result = runner.invoke(app, args)

    assert result.exit_code == 0, result.stdout
    assert mock_client.post.call_args.args == ("/mcp/search-job", expected_payload)


@patch("liepin_cli.cli.common.LiepinClient")
def test_readme_all_input_examples_match_extracted_payloads(
    mock_client_cls: Mock, monkeypatch
) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")
    mock_client = mock_client_cls.return_value
    mock_client.post.return_value = {"ok": True}

    commands = extract_shell_commands_after_marker(README_PATH, "你可以这样调用：")
    cases = [
        (["resume", "update-base-info"], "`payloads/base-info.json`", "/mcp/update-base-info"),
        (["resume", "add-work-exp"], "`payloads/add-work-exp.json`", "/mcp/add-work-exp"),
        (["resume", "add-job-want"], "`payloads/add-job-want.json`", "/mcp/add-job-want"),
        (["job", "search"], "`payloads/search-job.json`", "/mcp/search-job"),
        (["job", "apply"], "`payloads/apply-job.json`", "/mcp/apply-job"),
    ]

    with runner.isolated_filesystem():
        for _, label, _ in cases:
            payload_text = extract_fenced_block_after_label(README_PATH, label, "json")
            payload_path = Path(label.strip("`"))
            payload_path.parent.mkdir(parents=True, exist_ok=True)
            payload_path.write_text(payload_text, encoding="utf-8")

        for prefix, label, endpoint in cases:
            mock_client.post.reset_mock()
            args = _find_command(commands, prefix)
            payload_text = extract_fenced_block_after_label(README_PATH, label, "json")
            expected_payload = json.loads(payload_text)

            result = runner.invoke(app, args)

            assert result.exit_code == 0, result.stdout
            assert mock_client.post.call_args.args == (endpoint, expected_payload)


@patch("liepin_cli.cli.common.LiepinClient")
def test_readme_repeatable_flag_example_matches_generated_payload(
    mock_client_cls: Mock, monkeypatch
) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "token-123")
    mock_client = mock_client_cls.return_value
    mock_client.post.return_value = {"ok": True}

    commands = extract_shell_commands_after_marker(
        README_PATH, "数组字段可以通过重复传参来构造。例如："
    )
    args = _find_command(commands, ["resume", "add-job-want"])
    expected_payload = json.loads(
        extract_fenced_block_after_label(README_PATH, "会生成：", "json")
    )

    result = runner.invoke(app, args)

    assert result.exit_code == 0, result.stdout
    assert mock_client.post.call_args.args == ("/mcp/add-job-want", expected_payload)


def test_readme_mentions_setup_first() -> None:
    readme = Path(README_PATH).read_text(encoding="utf-8")
    assert "liepin-cli setup" in readme
    assert "auth setup" in readme


def test_readme_documents_auth_subcommands_and_token_priority() -> None:
    readme = Path(README_PATH).read_text(encoding="utf-8")
    for sub in ("auth setup", "auth status", "auth clear", "auth open"):
        assert sub in readme, f"README should mention `{sub}`"
    assert "--token > env > config" in readme
    assert "LIEPIN_USER_TOKEN" in readme


def test_readme_documents_auth_recovery_guidance() -> None:
    readme = Path(README_PATH).read_text(encoding="utf-8")
    assert "未找到 token" in readme
    assert "**stderr**" in readme
    assert "liepin-cli auth setup" in readme
    assert "授权失败" in readme


def test_readme_mentions_localized_help_pages() -> None:
    readme = Path(README_PATH).read_text(encoding="utf-8")
    assert "liepin-cli --help" in readme
    assert "liepin-cli auth --help" in readme
    assert "用法" in readme
    assert "选项" in readme
    assert "命令" in readme


def test_readme_clarifies_flag_naming_edge_cases_and_output_modes() -> None:
    readme = Path(README_PATH).read_text(encoding="utf-8")
    assert "## 参数名与 JSON 字段名的映射" in readme
    assert "--jobtitle" in readme
    assert "--dq" in readme
    assert "camelCase" in readme
    assert "## 输出模式" in readme
    assert "成功。" in readme
    assert "`null`" in readme


def test_readme_resume_command_overview_matches_registered_commands() -> None:
    readme = Path(README_PATH).read_text(encoding="utf-8")
    rows = _parse_command_overview_table(readme, "### Resume 命令")
    expected = _registered_group_commands("resume")

    assert {row["command"] for row in rows} == set(expected)
    assert {
        row["command"]: row["supports_input"] == "是"
        for row in rows
    } == expected


def test_readme_job_command_overview_matches_registered_commands() -> None:
    readme = Path(README_PATH).read_text(encoding="utf-8")
    rows = _parse_command_overview_table(readme, "### Job 命令")
    expected = _registered_group_commands("job")

    assert {row["command"] for row in rows} == set(expected)
    assert {
        row["command"]: row["supports_input"] == "是"
        for row in rows
    } == expected


def test_readme_clarifies_example_payload_paths_are_local() -> None:
    readme = Path(README_PATH).read_text(encoding="utf-8")
    assert "不会随仓库一起提供" in readme
    assert "手动创建" in readme
