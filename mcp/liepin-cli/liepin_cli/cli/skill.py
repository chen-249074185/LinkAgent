from __future__ import annotations

from pathlib import Path

import typer

from liepin_cli.cli.help_localization import LocalizedTyperGroup, apply_localized_command_cls
from liepin_cli.skill_distribution import install_skill

skill_app = typer.Typer(
    cls=LocalizedTyperGroup,
    help="从本仓库生成 Agent Skill，并可安装到本机各平台 skills 目录。",
)


@skill_app.command(
    "install",
    help="根据 README 生成 skill 并同步仓库内目录；可加 -g/--claude/--codex 写入用户级 skills。",
)
def skill_install(
    repo_root: Path | None = typer.Option(
        None,
        "--repo-root",
        help="源码仓库根目录，默认当前工作目录。",
    ),
    global_cursor: bool = typer.Option(
        False,
        "--global",
        "-g",
        help="同时安装到用户级 Cursor：~/.cursor/skills/liepin-cli/（类似 npx skills add -g）。",
    ),
    claude: bool = typer.Option(
        False,
        "--claude",
        help="同时安装到 ~/.claude/skills/liepin-cli/。",
    ),
    codex: bool = typer.Option(
        False,
        "--codex",
        help="同时安装到 ~/.agents/skills/liepin-cli/（Codex 常见路径）。",
    ),
) -> None:
    root = (repo_root or Path.cwd()).resolve()
    try:
        install_skill(
            root,
            global_cursor=global_cursor,
            claude=claude,
            codex=codex,
        )
    except ValueError as exc:
        typer.secho(str(exc), err=True)
        raise typer.Exit(code=1) from exc


apply_localized_command_cls(skill_app)
