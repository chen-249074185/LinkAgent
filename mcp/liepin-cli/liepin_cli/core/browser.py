from __future__ import annotations

import webbrowser

from liepin_cli.core.errors import BrowserOpenError

_AUTH_URL = "https://www.liepin.com/mcp/auth"


def open_auth_page() -> None:
    try:
        opened = webbrowser.open(_AUTH_URL)
    except Exception as exc:
        raise BrowserOpenError(
            "打开授权页面失败；请手动访问 https://www.liepin.com/mcp/auth"
        ) from exc
    if not opened:
        raise BrowserOpenError(
            "打开授权页面失败；请手动访问 https://www.liepin.com/mcp/auth"
        )
