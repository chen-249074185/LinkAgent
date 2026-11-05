from __future__ import annotations

import json
import os
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import ValidationError

from liepin_cli.core.errors import InvalidInputError


class StoredAuth(BaseModel):
    token: str | None = None


def config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "liepin-cli" / "config.json"


def _invalid_config(message: str) -> InvalidInputError:
    return InvalidInputError(f"CLI 配置文件无效（{config_path()}）：{message}")


def _load_config_data() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (JSONDecodeError, UnicodeDecodeError) as exc:
        raise _invalid_config("应为有效的 UTF-8 JSON") from exc
    if not isinstance(data, dict):
        raise _invalid_config("顶层必须是 JSON 对象")
    return data


def _write_config_data(data: dict[str, Any]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_stored_auth() -> StoredAuth:
    try:
        return StoredAuth.model_validate(_load_config_data())
    except ValidationError as exc:
        raise _invalid_config("token 字段存在时必须是字符串") from exc


def save_token(token: str) -> None:
    data = _load_config_data()
    data["token"] = token
    _write_config_data(data)


def clear_token() -> bool:
    path = config_path()
    if not path.exists():
        return False
    data = _load_config_data()
    if "token" not in data:
        return False
    data.pop("token", None)
    _write_config_data(data)
    return True
