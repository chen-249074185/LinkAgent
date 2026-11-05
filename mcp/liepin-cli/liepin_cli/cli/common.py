from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Type

import typer
from pydantic import BaseModel, ValidationError

from liepin_cli.core.client import LiepinClient
from liepin_cli.core.config import RuntimeConfig, resolve_config
from liepin_cli.core.errors import (
    AuthorizationError,
    InvalidInputError,
    LiepinCliError,
    MissingTokenError,
    RequestError,
)
from liepin_cli.core.interaction import is_interactive_terminal
from liepin_cli.core.output import render_output
from liepin_cli.core.payloads import load_payload_file, merge_payload

TokenOption = typer.Option(
    None,
    "--token",
    help="猎聘用户 token（也可设置 `LIEPIN_USER_TOKEN`，或使用本地配置文件）。",
    hidden=True,
)
BaseUrlOption = typer.Option(
    None,
    "--base-url",
    help="API 基础 URL。",
    hidden=True,
)
TimeoutOption = typer.Option(
    None,
    "--timeout",
    help="请求超时时间（秒）。",
    hidden=True,
)
OutputOption = typer.Option(
    None,
    "--output",
    help="输出格式，例如 `pretty`、`json`。",
    hidden=True,
)
InputOption = Annotated[
    Path | None,
    typer.Option("--input", help="JSON 请求体文件路径。", hidden=True),
]


def build_config(
    token: str | None,
    base_url: str | None,
    timeout: float | None,
    output: str | None,
) -> RuntimeConfig:
    return resolve_config(token, base_url, timeout, output)


def exit_with_error(err: LiepinCliError) -> None:
    typer.echo(f"错误：{err}", err=True)
    code = 1 if isinstance(err, RequestError) else 2
    raise typer.Exit(code=code)


def run_missing_token_flow(err: MissingTokenError) -> None:
    if is_interactive_terminal():
        typer.echo("未找到 token。请先运行 setup 流程。", err=True)


def run_authorization_recovery(
    err: AuthorizationError, *, force: bool = False
) -> None:
    if force or is_interactive_terminal():
        typer.echo(
            "授权失败。请尝试运行 `liepin-cli setup` 或 `liepin-cli auth setup` "
            "刷新 token。",
            err=True,
        )


def build_model_payload(
    model_cls: Type[BaseModel],
    input_path: Path | None,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    try:
        payload = merge_payload(load_payload_file(input_path), overrides)
        model = model_cls.model_validate(payload)
        return model.model_dump(exclude_none=True)
    except ValidationError as exc:
        raise InvalidInputError(str(exc)) from exc


def execute_get(
    path: str,
    *,
    token: str | None,
    base_url: str | None,
    timeout: float | None,
    output: str | None,
) -> None:
    try:
        config = build_config(token, base_url, timeout, output)
        data = LiepinClient(config).get(path)
        render_output(data, config.output)
    except MissingTokenError as exc:
        run_missing_token_flow(exc)
        raise
    except AuthorizationError as exc:
        run_authorization_recovery(exc)
        raise


def execute_post(
    path: str,
    *,
    token: str | None,
    base_url: str | None,
    timeout: float | None,
    output: str | None,
    model_cls: Type[BaseModel],
    input_path: Path | None,
    overrides: dict[str, Any],
) -> None:
    try:
        config = build_config(token, base_url, timeout, output)
        payload = build_model_payload(model_cls, input_path, overrides)
        data = LiepinClient(config).post(path, payload)
        render_output(data, config.output)
    except MissingTokenError as exc:
        run_missing_token_flow(exc)
        raise
    except AuthorizationError as exc:
        run_authorization_recovery(exc)
        raise
