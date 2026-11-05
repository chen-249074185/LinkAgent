from pathlib import Path
from unittest.mock import Mock

import pytest

from liepin_cli.core.errors import AuthorizationError
from liepin_cli.core.errors import BrowserOpenError
from liepin_cli.core.errors import RequestError
from liepin_cli.core.onboarding import mask_token, run_auth_setup


def test_mask_token_hides_middle_characters() -> None:
    assert mask_token("x-user-token-abcdef") == "x-user-token-****cdef"


def test_mask_token_masks_short_hyphen_suffix_without_leaking_it() -> None:
    assert mask_token("x-user-token-ab") == "x-user-token-****"


def test_mask_token_masks_short_token_without_hyphen() -> None:
    assert mask_token("abc") == "****"


def test_mask_token_masks_long_token_without_hyphen() -> None:
    assert mask_token("plainsecret") == "****cret"


def test_mask_token_returns_empty_string_for_empty_token() -> None:
    assert mask_token("") == ""


def test_authorization_error_is_request_error_subclass() -> None:
    assert issubclass(AuthorizationError, RequestError)


def test_open_auth_page_raises_browser_open_error_when_browser_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("liepin_cli.core.browser.webbrowser.open", lambda url: False)
    from liepin_cli.core.browser import open_auth_page

    with pytest.raises(BrowserOpenError, match="打开授权页面失败"):
        open_auth_page()


def test_open_auth_page_wraps_webbrowser_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(url: str) -> bool:
        raise RuntimeError("browser unavailable")

    monkeypatch.setattr("liepin_cli.core.browser.webbrowser.open", _raise)
    from liepin_cli.core.browser import open_auth_page

    with pytest.raises(BrowserOpenError, match="打开授权页面失败"):
        open_auth_page()


def test_is_interactive_terminal_true_when_both_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    stdin = Mock(isatty=Mock(return_value=True))
    stdout = Mock(isatty=Mock(return_value=True))
    monkeypatch.setattr("liepin_cli.core.interaction.sys.stdin", stdin)
    monkeypatch.setattr("liepin_cli.core.interaction.sys.stdout", stdout)
    from liepin_cli.core.interaction import is_interactive_terminal

    assert is_interactive_terminal() is True


def test_is_interactive_terminal_false_when_stdin_not_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    stdin = Mock(isatty=Mock(return_value=False))
    stdout = Mock(isatty=Mock(return_value=True))
    monkeypatch.setattr("liepin_cli.core.interaction.sys.stdin", stdin)
    monkeypatch.setattr("liepin_cli.core.interaction.sys.stdout", stdout)
    from liepin_cli.core.interaction import is_interactive_terminal

    assert is_interactive_terminal() is False


def test_run_auth_setup_saves_and_verifies_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    prompts = iter([True, "x-user-token-abc"])
    monkeypatch.setattr("liepin_cli.core.onboarding.is_interactive_terminal", lambda: True)
    monkeypatch.setattr("liepin_cli.core.onboarding.open_auth_page", lambda: None)
    monkeypatch.setattr("liepin_cli.core.onboarding.confirm_open_auth_page", lambda: next(prompts))
    monkeypatch.setattr("liepin_cli.core.onboarding.prompt_for_token", lambda: next(prompts))

    verifier = Mock()
    token = run_auth_setup(verifier=verifier)

    assert token == "x-user-token-abc"
    verifier.assert_called_once_with("x-user-token-abc")
    from liepin_cli.core.auth_store import load_stored_auth

    assert load_stored_auth().token == "x-user-token-abc"


def test_run_auth_setup_verifies_before_saving_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr("liepin_cli.core.onboarding.is_interactive_terminal", lambda: True)
    monkeypatch.setattr("liepin_cli.core.onboarding.confirm_open_auth_page", lambda: False)
    monkeypatch.setattr(
        "liepin_cli.core.onboarding.prompt_for_token", lambda: "x-user-token-verify"
    )

    from liepin_cli.core.auth_store import load_stored_auth

    def verifier(token: str) -> None:
        assert token == "x-user-token-verify"
        assert load_stored_auth().token is None

    token = run_auth_setup(verifier=verifier)

    assert token == "x-user-token-verify"
    assert load_stored_auth().token == "x-user-token-verify"


def test_run_auth_setup_returns_none_when_not_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("liepin_cli.core.onboarding.is_interactive_terminal", lambda: False)
    verifier = Mock()
    assert run_auth_setup(verifier=verifier) is None
    verifier.assert_not_called()


def test_run_auth_setup_returns_none_when_empty_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr("liepin_cli.core.onboarding.is_interactive_terminal", lambda: True)
    monkeypatch.setattr("liepin_cli.core.onboarding.confirm_open_auth_page", lambda: False)
    monkeypatch.setattr("liepin_cli.core.onboarding.prompt_for_token", lambda: None)
    verifier = Mock()
    assert run_auth_setup(verifier=verifier) is None
    verifier.assert_not_called()


def test_run_auth_setup_does_not_save_token_when_verifier_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr("liepin_cli.core.onboarding.is_interactive_terminal", lambda: True)
    monkeypatch.setattr("liepin_cli.core.onboarding.confirm_open_auth_page", lambda: False)
    monkeypatch.setattr("liepin_cli.core.onboarding.prompt_for_token", lambda: "x-user-token-bad")

    from liepin_cli.core.auth_store import load_stored_auth

    def verifier(token: str) -> None:
        raise AuthorizationError(f"rejected {token}")

    with pytest.raises(AuthorizationError, match="rejected x-user-token-bad"):
        run_auth_setup(verifier=verifier)

    assert load_stored_auth().token is None
