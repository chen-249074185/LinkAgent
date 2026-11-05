from __future__ import annotations

import json
from typing import Any

import typer


def render_output(data: Any, mode: str) -> None:
    if mode == "json":
        typer.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return
    if mode == "pretty":
        if data is None:
            typer.echo("成功。")
            return
        if isinstance(data, str):
            typer.echo(data)
            return
        if isinstance(data, (dict, list)):
            typer.echo(json.dumps(data, ensure_ascii=False, indent=2))
            return
        typer.echo(str(data))
        return
    typer.echo(str(data) if data is not None else "成功。")
