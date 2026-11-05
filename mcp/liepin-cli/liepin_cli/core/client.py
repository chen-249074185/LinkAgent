from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import requests

from liepin_cli.core.config import RuntimeConfig
from liepin_cli.core.errors import AuthorizationError, RequestError


class LiepinClient:
    def __init__(self, config: RuntimeConfig) -> None:
        self._config = config

    def _url(self, path: str) -> str:
        base = self._config.base_url.rstrip("/") + "/"
        rel = path.lstrip("/")
        return urljoin(base, rel)

    def _headers(self) -> dict[str, str]:
        return {"x-user-token": self._config.token}

    def _request(self, **kwargs: Any) -> requests.Response:
        try:
            return requests.request(**kwargs)
        except requests.RequestException as exc:
            raise RequestError(f"请求失败：{exc}") from exc

    def _parse_response(self, resp: requests.Response) -> Any:
        if resp.status_code in {401, 403}:
            parts = [str(resp.status_code)]
            detail = (resp.text or "").strip()
            if detail:
                parts.append(detail)
            raise AuthorizationError(" ".join(parts))
        if resp.status_code >= 400:
            parts = [str(resp.status_code)]
            if resp.text:
                parts.append(resp.text)
            raise RequestError(" ".join(parts))
        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type.lower():
            try:
                return resp.json()
            except ValueError as exc:
                raise RequestError(f"响应 JSON 非法：{exc}") from exc
        text = resp.text
        return text if text else None

    def get(self, path: str) -> Any:
        resp = self._request(
            method="GET",
            url=self._url(path),
            headers=self._headers(),
            timeout=self._config.timeout,
        )
        return self._parse_response(resp)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        resp = self._request(
            method="POST",
            url=self._url(path),
            headers=self._headers(),
            timeout=self._config.timeout,
            json=payload,
        )
        return self._parse_response(resp)
