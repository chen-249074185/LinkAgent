from __future__ import annotations

import sys

import typer


def is_interactive_terminal() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def confirm_open_auth_page() -> bool:
    return typer.confirm("现在打开猎聘授权页面吗？", default=True)


def prompt_for_token() -> str | None:
    value = typer.prompt("请粘贴 x-user-token", default="", show_default=False).strip()
    return value or None
