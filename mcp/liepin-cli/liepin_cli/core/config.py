from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field

from liepin_cli.core.auth_store import load_stored_auth
from liepin_cli.core.errors import InvalidInputError, MissingTokenError

_DEFAULT_BASE_URL = "https://open-agent.liepin.com"


class RuntimeConfig(BaseModel):
    token: str = Field(..., min_length=1)
    token_source: Literal["cli", "env", "config"]
    base_url: str = Field(default=_DEFAULT_BASE_URL)
    timeout: float = Field(default=30.0)
    output: str = Field(default="pretty")


def resolve_config(
    token: str | None,
    base_url: str | None,
    timeout: float | None,
    output: str | None,
) -> RuntimeConfig:
    resolved_output = output if output is not None else "pretty"
    if resolved_output not in {"pretty", "json"}:
        raise InvalidInputError("`--output` 只能是：pretty、json")

    flag_token = (token or "").strip()
    if flag_token:
        resolved, source = flag_token, "cli"
    else:
        env_token = (os.environ.get("LIEPIN_USER_TOKEN") or "").strip()
        if env_token:
            resolved, source = env_token, "env"
        else:
            stored_token = (load_stored_auth().token or "").strip()
            if stored_token:
                resolved, source = stored_token, "config"
            else:
                raise MissingTokenError(
                    "缺少 x-user-token。请通过 `--token`、`LIEPIN_USER_TOKEN` 或 CLI 配置文件提供 token。"
                    "可前往 https://www.liepin.com/mcp/auth 生成。"
                )
    return RuntimeConfig(
        token=resolved,
        token_source=source,
        base_url=base_url if base_url is not None else _DEFAULT_BASE_URL,
        timeout=timeout if timeout is not None else 30.0,
        output=resolved_output,
    )
