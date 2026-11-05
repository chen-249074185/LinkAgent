from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from liepin_cli.core.errors import InvalidInputError


def load_payload_file(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise InvalidInputError(f"找不到输入文件：{path}") from exc
    except UnicodeDecodeError as exc:
        raise InvalidInputError(f"无法读取输入文件 {path}：文件不是有效的 UTF-8 编码") from exc
    except OSError as exc:
        raise InvalidInputError(f"无法读取输入文件 {path}：{exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidInputError(f"{path} 中的 JSON 非法") from exc
    if not isinstance(data, dict):
        raise InvalidInputError(
            f"{path} 的 JSON 顶层必须是对象（当前为 {type(data).__name__}）"
        )
    return data


def merge_payload(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if value is not None:
            merged[key] = value
    return {key: value for key, value in merged.items() if value is not None}
