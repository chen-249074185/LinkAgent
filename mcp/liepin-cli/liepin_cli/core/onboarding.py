from __future__ import annotations

from collections.abc import Callable

from liepin_cli.core.auth_store import save_token
from liepin_cli.core.browser import open_auth_page
from liepin_cli.core.interaction import confirm_open_auth_page
from liepin_cli.core.interaction import is_interactive_terminal
from liepin_cli.core.interaction import prompt_for_token


def mask_token(token: str) -> str:
    if not token:
        return ""
    if len(token) <= 4:
        return "****"
    if "-" in token:
        head, _, tail = token.rpartition("-")
        if len(tail) <= 4:
            return f"{head}-****"
        return f"{head}-****{tail[-4:]}"
    return f"****{token[-4:]}"


def run_auth_setup(*, verifier: Callable[[str], None]) -> str | None:
    interactive = is_interactive_terminal()
    if interactive and confirm_open_auth_page():
        open_auth_page()
    token = prompt_for_token() if interactive else None
    if not token:
        return None
    verifier(token)
    save_token(token)
    return token
