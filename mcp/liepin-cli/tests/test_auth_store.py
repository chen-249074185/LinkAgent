import json
from pathlib import Path

import pytest

from liepin_cli.core.auth_store import clear_token, config_path, load_stored_auth, save_token
from liepin_cli.core.config import resolve_config
from liepin_cli.core.errors import InvalidInputError, MissingTokenError


def test_save_and_load_token_uses_config_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    save_token("x-user-token-123")

    stored = load_stored_auth()
    assert stored.token == "x-user-token-123"
    assert config_path() == tmp_path / "liepin-cli" / "config.json"


def test_clear_token_removes_saved_token(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save_token("x-user-token-123")

    assert clear_token() is True
    assert load_stored_auth().token is None


def test_save_token_preserves_unrelated_config_keys(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")

    save_token("x-user-token-123")

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "theme": "dark",
        "token": "x-user-token-123",
    }


def test_clear_token_preserves_unrelated_config_keys(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"theme": "dark", "token": "x-user-token-123"}),
        encoding="utf-8",
    )

    assert clear_token() is True
    assert load_stored_auth().token is None
    assert json.loads(path.read_text(encoding="utf-8")) == {"theme": "dark"}


def test_clear_token_returns_false_when_file_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    assert clear_token() is False


def test_load_stored_auth_invalid_json_raises_invalid_input_error(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{bad json", encoding="utf-8")

    with pytest.raises(InvalidInputError) as exc_info:
        load_stored_auth()

    assert "配置文件无效" in str(exc_info.value)


def test_load_stored_auth_invalid_schema_raises_invalid_input_error(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"token": 123}), encoding="utf-8")

    with pytest.raises(InvalidInputError) as exc_info:
        load_stored_auth()

    assert "配置文件无效" in str(exc_info.value)


def test_resolve_config_prefers_cli_token_over_env_and_config(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "env-token")
    save_token("config-token")

    config = resolve_config("cli-token", None, None, None)

    assert config.token == "cli-token"
    assert config.token_source == "cli"


def test_resolve_config_prefers_env_token_over_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "env-token")
    save_token("config-token")

    config = resolve_config(None, None, None, None)

    assert config.token == "env-token"
    assert config.token_source == "env"


def test_resolve_config_does_not_read_broken_config_when_env_token_exists(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "env-token")
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{bad json", encoding="utf-8")

    config = resolve_config(None, None, None, None)

    assert config.token == "env-token"
    assert config.token_source == "env"


def test_resolve_config_uses_saved_config_when_higher_priority_sources_absent(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("LIEPIN_USER_TOKEN", raising=False)
    save_token("config-token")

    config = resolve_config(None, None, None, None)

    assert config.token == "config-token"
    assert config.token_source == "config"


def test_resolve_config_missing_token_raises(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("LIEPIN_USER_TOKEN", raising=False)

    with pytest.raises(MissingTokenError):
        resolve_config(None, None, None, None)


def test_resolve_config_invalid_output_raises(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("LIEPIN_USER_TOKEN", raising=False)
    save_token("config-token")

    with pytest.raises(InvalidInputError, match="`--output`"):
        resolve_config(None, None, None, "xml")


def test_resolve_config_invalid_output_takes_precedence_over_missing_token(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("LIEPIN_USER_TOKEN", raising=False)

    with pytest.raises(InvalidInputError, match="`--output`"):
        resolve_config(None, None, None, "xml")
