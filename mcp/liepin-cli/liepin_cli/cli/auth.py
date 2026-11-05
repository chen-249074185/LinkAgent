from __future__ import annotations

import typer

from liepin_cli.cli.common import exit_with_error, run_authorization_recovery
from liepin_cli.cli.help_localization import (
    LocalizedTyperGroup,
    apply_localized_command_cls,
)
from liepin_cli.core.auth_store import clear_token, load_stored_auth
from liepin_cli.core.browser import open_auth_page
from liepin_cli.core.client import LiepinClient
from liepin_cli.core.config import resolve_config
from liepin_cli.core.errors import (
    AuthorizationError,
    BrowserOpenError,
    InvalidInputError,
    LiepinCliError,
)
from liepin_cli.core.interaction import is_interactive_terminal
from liepin_cli.core.onboarding import mask_token, run_auth_setup

app = typer.Typer(cls=LocalizedTyperGroup, help="认证与授权辅助命令。")


def verify_token_with_resume_get(token: str) -> None:
    config = resolve_config(token, None, None, None)
    LiepinClient(config).get("/mcp/get-resume")


def run_cli_setup() -> None:
    try:
        token = run_auth_setup(verifier=verify_token_with_resume_get)
        if token is None:
            if is_interactive_terminal():
                raise InvalidInputError(
                    "未收到 token（输入为空或已取消）。"
                    "请粘贴 token，或先运行 `liepin-cli auth open` 再重新执行 setup。"
                )
            raise InvalidInputError(
                "setup 需要支持粘贴输入的交互式终端。"
            )
    except AuthorizationError as exc:
        run_authorization_recovery(exc, force=True)
        exit_with_error(exc)
    except LiepinCliError as exc:
        exit_with_error(exc)


@app.command("status", help="查看当前登录状态。")
def auth_status() -> None:
    try:
        stored = load_stored_auth()
    except LiepinCliError as exc:
        exit_with_error(exc)
    if stored.token:
        typer.echo(f"已保存 token：{mask_token(stored.token)}")
    else:
        typer.echo("配置文件中没有已保存的 token。")


@app.command("clear", help="清除当前认证信息。")
def auth_clear() -> None:
    try:
        cleared = clear_token()
    except LiepinCliError as exc:
        exit_with_error(exc)
    if cleared:
        typer.echo("已清除保存的 token。")
    else:
        typer.echo("没有可清除的已保存 token。")


@app.command("open", help="打开认证相关页面。")
def auth_open() -> None:
    try:
        open_auth_page()
    except BrowserOpenError as exc:
        exit_with_error(exc)
    typer.echo("已打开猎聘授权页面。")


@app.command("setup", help="设置或更新认证。")
def auth_setup_cmd() -> None:
    run_cli_setup()


apply_localized_command_cls(app)
