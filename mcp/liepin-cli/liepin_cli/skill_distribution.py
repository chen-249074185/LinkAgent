from __future__ import annotations

import json
import shutil
from pathlib import Path
from textwrap import dedent, indent


def _markdown_block(text: str) -> str:
    return dedent(text).strip() + "\n"


def _indented_block(text: str, prefix: str = "        ") -> str:
    return indent(text, prefix)


def _readme_text(repo_root: Path) -> str:
    return (repo_root / "README.md").read_text(encoding="utf-8")


def _table_cells(line: str) -> list[str]:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if not cells or any(cell == "" for cell in cells):
        raise ValueError(f"Invalid markdown table row: {line!r}")
    return cells


def _rows_after_heading(
    readme: str, heading: str, expected_headers: list[str]
) -> list[list[str]]:
    heading_index = readme.find(heading)
    if heading_index == -1:
        raise ValueError(f"Could not find heading {heading!r}")

    section_lines = readme[heading_index + len(heading) :].splitlines()
    for index, line in enumerate(section_lines):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue

        headers = _table_cells(stripped)
        if headers != expected_headers:
            continue

        if index + 1 >= len(section_lines) or not section_lines[index + 1].strip().startswith(
            "|"
        ):
            raise ValueError(f"Table under {heading!r} is missing a separator row")

        rows: list[list[str]] = []
        for data_line in section_lines[index + 2 :]:
            if not data_line.strip().startswith("|"):
                break

            cells = _table_cells(data_line)
            if len(cells) != len(expected_headers):
                raise ValueError(
                    f"Expected {len(expected_headers)} cells under {heading!r}, got {len(cells)} in row {data_line!r}"
                )
            rows.append(cells)
        if not rows:
            raise ValueError(f"Table under {heading!r} has no data rows")
        return rows

    raise ValueError(f"Could not find table with headers {expected_headers!r} under {heading!r}")


def _parse_four_column_table(readme: str, heading: str) -> list[dict[str, str]]:
    rows = _rows_after_heading(
        readme,
        heading,
        ["命令", "用途", "常见关键参数", "是否支持 `--input`"],
    )
    parsed_rows: list[dict[str, str]] = []
    for cells in rows:
        parsed_rows.append(
            {
                "command": cells[0],
                "description": cells[1],
                "common_args": cells[2],
                "supports_input": cells[3],
            }
        )
    return parsed_rows


def _parse_auth_table(readme: str) -> list[dict[str, str]]:
    rows = _rows_after_heading(readme, "### 授权子命令", ["子命令", "用途"])
    parsed_rows: list[dict[str, str]] = []
    for cells in rows:
        parsed_rows.append({"command": cells[0], "description": cells[1]})
    return parsed_rows


def _render_command_map() -> str:
    rows = [
        ("Get current resume", "`liepin-cli resume get --output json`"),
        ("Search jobs", "`liepin-cli job search ... --output json`"),
        (
            "Apply to job",
            "`liepin-cli job apply --job-id <id> --job-kind <kind> --output json`",
        ),
        ("First-time token setup", "`liepin-cli setup`"),
        ("Auth management", "`liepin-cli auth setup/status/open/clear`"),
    ]
    body = "\n".join(f"| {intent} | {command} |" for intent, command in rows)
    return "| Intent | Preferred command |\n|------|------|\n" + body


def _render_reference_table(
    heading: str, headers: str, rows: list[dict[str, str]], keys: list[str]
) -> str:
    body = "\n".join(
        "| " + " | ".join(row[key] for key in keys) + " |" for row in rows
    )
    return f"### {heading}\n\n{headers}\n{body}\n"


def _distribution_targets() -> list[dict[str, str]]:
    return [
        {
            "id": "cursor-project",
            "platform": "Cursor Project",
            "install_root": "<project>/.cursor/skills",
            "copy_from": "skills/liepin-cli",
            "status": "documented",
            "notes": "Copy the liepin-cli folder from the repo into the project-level skills directory.",
        },
        {
            "id": "cursor-home",
            "platform": "Cursor Home",
            "install_root": "~/.cursor/skills",
            "copy_from": "skills/liepin-cli",
            "status": "documented",
            "notes": "Use this when you want the skill available across Cursor workspaces.",
        },
        {
            "id": "claude-home",
            "platform": "Claude Code",
            "install_root": "~/.claude/skills",
            "copy_from": "skills/liepin-cli",
            "status": "documented",
            "notes": "Copy the liepin-cli folder into the Claude Code skills root.",
        },
        {
            "id": "codex-home",
            "platform": "Codex",
            "install_root": "<codex-skill-root>",
            "copy_from": "skills/liepin-cli",
            "status": "documented",
            "notes": "Use the skills root configured by your Codex environment, then copy the liepin-cli folder into it.",
        },
        {
            "id": "opencode-home",
            "platform": "OpenCode / OpenClaw-compatible",
            "install_root": "<opencode-skill-root>",
            "copy_from": "skills/liepin-cli",
            "status": "documented",
            "notes": "Use the platform skill root, then copy the liepin-cli folder into it.",
        },
        {
            "id": "cowork-generic",
            "platform": "Cowork / Other Compatible Agents",
            "install_root": "<platform-skill-root>",
            "copy_from": "skills/liepin-cli",
            "status": "generic",
            "notes": "Any agent platform that supports a skills directory can reuse the same liepin-cli folder.",
        },
    ]


def _render_install_targets_table(targets: list[dict[str, str]]) -> str:
    headers = "| Platform | Install root | What to copy | Notes |\n|------|------|------|------|"
    body = "\n".join(
        "| "
        + " | ".join(
            [
                target["platform"],
                f"`{target['install_root']}`",
                f"`{target['copy_from']}`",
                target["notes"],
            ]
        )
        + " |"
        for target in targets
    )
    return headers + "\n" + body


def build_distribution_bundle(repo_root: Path) -> dict[str, str]:
    readme = _readme_text(repo_root)
    auth_rows = _parse_auth_table(readme)
    resume_rows = _parse_four_column_table(readme, "### Resume 命令")
    job_rows = _parse_four_column_table(readme, "### Job 命令")

    skill_md = _markdown_block(
        f"""
        ---
        name: liepin-cli
        description: Use when Liepin (猎聘) workflows need the CLI—missing or expired token, unauthorized responses, first-time setup, resume fetch/update, job search or apply, choosing job-kind from search results, machine-readable JSON for parsing, or summarizing user-facing `liepin-cli` help without advanced flags.
        ---

        # liepin-cli

        This skill is generated from the current project source. Do not edit distributed copies directly.

        ## Overview
        `liepin-cli` is the local CLI for Liepin resume, job, and auth workflows. Prefer it over ad hoc HTTP requests.

        ## When to Use
        - run `liepin-cli`
        - inspect or explain `liepin-cli --help`
        - manage Liepin token setup, refresh, or status
        - fetch or update resume data
        - search jobs or apply to jobs

        Do not use this skill for unrelated non-Liepin tasks.

        ## Core Rules
        - Prefer the installed `liepin-cli` command.
        - **Explaining help in chat (first pass):** Do not mention `--token`, `--input`, `--base-url`, `--timeout`, `--output`, or `--help` unless the user explicitly asks for raw/full/advanced help.
        - **Running commands:** Follow the Command Map; use `--output json` there for machine-readable results. Omit `--output json` when the user only needs human-readable CLI output.
        - For expired auth, guide the user to `liepin-cli auth open`, then `liepin-cli auth setup`.
        - `job apply --job-kind` must reuse the type code from search results; do not guess labels like `social`.
        - Do not assume README sample payload files already exist locally.

        ## Command Map
{_indented_block(_render_command_map())}

        ## Help Summary Defaults
        - Root help: `setup`, `auth`, `resume`, `job`
        - `auth --help`: `status`, `clear`, `open`, `setup`
        - `resume --help`: purpose plus subcommand overview only
        - `job --help`: `search`, `apply`
        - `job apply --help`: `--job-id`, `--job-kind`

        ## Common Mistakes
        - Surfacing hidden/internal flags in the first help answer
        - Guessing `jobKind` instead of reusing the search result
        - Treating README payload paths as shipped files
        - Dumping every resume field at once instead of summarizing the most useful business fields first

        ## Reference
        Read [reference.md](reference.md) for install, command tables, auth recovery, and `--input` / `--output` notes. To install the CLI from source, follow the repository root `README.md`.
        """
    )

    auth_table = _render_reference_table(
        "Auth Commands",
        "| Command | Description |\n|------|------|",
        auth_rows,
        ["command", "description"],
    )
    resume_table = _render_reference_table(
        "Resume Commands",
        "| Command | Description | Common args | Supports `--input` |\n|------|------|------|------|",
        resume_rows,
        ["command", "description", "common_args", "supports_input"],
    )
    job_table = _render_reference_table(
        "Job Commands",
        "| Command | Description | Common args | Supports `--input` |\n|------|------|------|------|",
        job_rows,
        ["command", "description", "common_args", "supports_input"],
    )

    reference_md = _markdown_block(
        f"""
        # liepin-cli Reference

        This file is generated from the current project source. Use it as the heavier companion to `SKILL.md`.

        ## Install Context
        - The target user should already have `liepin-cli` available.
        - If not installed, follow the repository root `README.md` install section (`pip install -e` / `liepin-cli` on PATH).
        - The local project documents auth, help, command tables, payload formats, and examples in `README.md`.

        ## Core Commands
        ```bash
        liepin-cli setup
        liepin-cli auth setup
        liepin-cli auth status
        liepin-cli auth open
        liepin-cli auth clear

        liepin-cli resume get --output json
        liepin-cli job search --job-name "Java开发" --address "北京" --page 0 --output json
        liepin-cli job apply --job-id 123456 --job-kind 2 --output json
        ```

        ## User-Facing Help Rule
        - First-pass help should show only business-facing commands and flags.
        - Do not mention hidden/internal flags unless the user explicitly asks for raw/full help.
        - `job apply` first-pass help should focus on `--job-id` and `--job-kind`.
        - `resume --help` first-pass help should stay at purpose plus subcommand overview.

{_indented_block(auth_table)}
{_indented_block(resume_table)}
{_indented_block(job_table)}

        ## Auth Recovery
        - Missing token: run `liepin-cli setup` or `liepin-cli auth setup`
        - Unauthorized token: run `liepin-cli auth open`, then refresh with `liepin-cli auth setup`
        - Token priority: `--token` > `LIEPIN_USER_TOKEN` > local config file

        ## `jobKind` Rule
        - `job apply --job-kind` must use the returned type code such as `1` or `2`
        - Search first, then reuse the returned type value

        ## `--input` Rule
        - Many add/update commands support `--input <json-file>`
        - Merge order: file first, explicit CLI overrides second, then null stripping and validation
        - README payload paths are illustrative only and are not bundled

        ## Output Mode Rule
        - Prefer `--output json` when Chat needs machine-readable output
        - `pretty` may print `成功。` for empty responses while `json` prints `null`

        ## Agent 人工验收清单（手动）
        在技能正文或 CLI 行为变更后、或对外发布前，用下表各测一遍：**先不加载**本 skill 记录基线，再**加载** `liepin-cli` skill 复测；失败则改 `SKILL.md` / 本文件后重跑。

        | # | 示例提示 | 期望行为 |
        |---|----------|----------|
        | 1 | 用一句话说明根命令能做什么，不要提 token 和高级参数 | 只提业务向分组；首答不出现 `--token`、`--output`、`--base-url` 等（除非用户要看完整帮助）。 |
        | 2 | 帮我查简历并把结果给你解析 | 使用或建议使用 `resume get` 且带 `--output json`。 |
        | 3 | token 过期了怎么办 | 引导 `auth open` 再 `auth setup`（或 `setup`），优先 CLI 而非手写 HTTP。 |
        | 4 | 直接投递职位（未给 search 结果） | 要求先 search 或索要 `job-id` 与来自结果的 `job-kind`，不猜测 kind。 |
        | 5 | README 里的示例 payload 文件在哪个路径 | 说明仅示例、默认不随仓库提供该文件；不假定路径存在。 |

        可选加压：提示里加「越快越好」，或将 1 与 4 合并，观察是否跳过规则。
        """
    )

    readme_md = _markdown_block(
        """# liepin-cli Skill bundle（两文件产物说明）

此 **bundle** 仅含 `SKILL.md` 与 `reference.md`（及本说明），由 `liepin-cli skill install` 从源码生成。写入项目内技能目录时通常**不包含**本文件—仅同步两文件到例如 `.cursor/skills/liepin-cli/`。

## 落位方式
将 `SKILL.md` 与 `reference.md` 放在 `<skills-root>/liepin-cli/` 下（例如 `~/.cursor/skills/liepin-cli/` 或 `<project>/.cursor/skills/liepin-cli/`）。

**仓库内唯一技能目录**为源码根目录 `skills/liepin-cli/`（含 `SKILL.md`、`reference.md`、`README.md`、`install-targets.json`）；安装时复制该目录到目标平台的 skills 根目录下，使最终路径为 `<skills-root>/liepin-cli/`。

## 重新生成 / 安装
在源码仓库根目录执行（推荐，与「安装」语义一致）：

```bash
uv run liepin-cli skill install
```

安装到用户级 Cursor（等价于常见 `npx skills add … -g` 落位）：

```bash
uv run liepin-cli skill install -g
```

仅同步仓库内产物、不写入用户目录时，使用 `uv run liepin-cli skill install`（不加 `-g` / `--claude` / `--codex`）即可。

默认会同时更新 `skills/liepin-cli/` 与 `.cursor/skills/liepin-cli/`。

## 说明
- 本安装包由当前工程源码经 `liepin-cli skill install` 生成
- `.cursor/skills/liepin-cli/` 在本仓库中视为同步产物，不应再作为源码手工维护
"""
    )

    return {
        "SKILL.md": skill_md,
        "reference.md": reference_md,
        "README.md": readme_md,
    }


def build_repo_skills_dir_files(repo_root: Path) -> dict[str, str]:
    root_bundle = build_distribution_bundle(repo_root)
    targets = _distribution_targets()
    package_readme = _markdown_block(
        f"""# liepin-cli Skill（仓库 `skills/liepin-cli/`）

本目录由当前工程源码经 `liepin-cli skill install` **生成**，不要手改 `SKILL.md` 与 `reference.md`；安装说明与目标映射见本文件与 `install-targets.json`。

## 目录内容

- `SKILL.md`、`reference.md`：Agent 使用的技能正文
- `README.md`：本说明（人工安装与跨平台目标）
- `install-targets.json`：机器可读的平台安装路径映射

## 支持的安装目标

{_render_install_targets_table(targets)}

## 安装原则

1. 先确保目标环境已经可以运行 `liepin-cli`
2. 找到目标平台的 skills 根目录
3. 将本目录（`skills/liepin-cli/`）**整个**复制到该根下，使最终路径为 `<skills-root>/liepin-cli/`

## 目标说明

- 下列平台的默认安装路径已文档化：Cursor、Claude Code、Codex、OpenCode / OpenClaw-compatible
- `Cowork` 等未在当前仓库内建适配器的平台，同样复制本目录即可

## 重新生成 / 安装

在源码仓库根目录执行（推荐）：

```bash
uv run liepin-cli skill install
```

用户级 Cursor（`-g`）：

```bash
uv run liepin-cli skill install -g
```

默认会同时更新：
- `skills/liepin-cli/`（供 `npx skills add liubx009/liepin-cli` 等从仓库发现 Skill）
- `.cursor/skills/liepin-cli/`（本仓库内项目级 skill，便于开发）

## 说明

- `.cursor/skills/liepin-cli/` 在本仓库中视为同步产物，不应手工维护
- `install-targets.json` 提供机器可读的目标映射
"""
    )
    install_targets_json = json.dumps(
        {
            "skillName": "liepin-cli",
            "targets": targets,
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"

    return {
        "README.md": package_readme,
        "SKILL.md": root_bundle["SKILL.md"],
        "reference.md": root_bundle["reference.md"],
        "install-targets.json": install_targets_json,
    }


def _write_files(target_dir: Path, files: dict[str, str], *, include_readme: bool) -> None:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        if name == "README.md" and not include_readme:
            continue
        output_path = target_dir / name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")


def write_distribution_bundle(
    repo_root: Path,
    project_skill_dir: Path,
    *,
    repo_skills_dir: Path | None = None,
) -> dict[str, str]:
    root_files = build_distribution_bundle(repo_root)
    repo_skills_files = build_repo_skills_dir_files(repo_root)
    _write_files(project_skill_dir, root_files, include_readme=False)
    if repo_skills_dir is not None:
        # Repo-root skills/liepin-cli — for `npx skills add <owner>/<repo> -y -g` discovery
        _write_files(repo_skills_dir, repo_skills_files, include_readme=True)
    return root_files


def resolve_repo_root(candidate: Path) -> Path:
    repo_root = candidate.resolve()
    required_paths = [repo_root / "README.md", repo_root / "pyproject.toml"]
    missing = [str(path.relative_to(repo_root)) for path in required_paths if not path.exists()]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(
            f"{repo_root} is not a liepin-cli source checkout. Missing: {missing_text}"
        )
    return repo_root


def _install_skill_bundle_to_dir(bundle: dict[str, str], dest: Path) -> None:
    """Write SKILL.md and reference.md under dest (e.g. .../skills/liepin-cli/)."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("SKILL.md", "reference.md"):
        (dest / name).write_text(bundle[name], encoding="utf-8")


def install_skill(
    repo_root: Path,
    *,
    global_cursor: bool = False,
    claude: bool = False,
    codex: bool = False,
) -> None:
    """Sync skill artifacts under the repo, then optionally install to user skill roots."""
    repo_root = resolve_repo_root(repo_root)
    project_skill_dir = repo_root / ".cursor" / "skills" / "liepin-cli"
    repo_skills_dir = repo_root / "skills" / "liepin-cli"
    bundle = write_distribution_bundle(
        repo_root=repo_root,
        project_skill_dir=project_skill_dir,
        repo_skills_dir=repo_skills_dir,
    )
    home = Path.home()
    if global_cursor:
        _install_skill_bundle_to_dir(bundle, home / ".cursor" / "skills" / "liepin-cli")
    if claude:
        _install_skill_bundle_to_dir(bundle, home / ".claude" / "skills" / "liepin-cli")
    if codex:
        _install_skill_bundle_to_dir(bundle, home / ".agents" / "skills" / "liepin-cli")
