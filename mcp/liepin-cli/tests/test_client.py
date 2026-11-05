from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from liepin_cli.core.client import LiepinClient
from liepin_cli.core.config import RuntimeConfig
from liepin_cli.core.errors import AuthorizationError, RequestError
from liepin_cli.core.output import render_output


def _runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        token="token-123",
        token_source="cli",
        base_url="https://open-agent.liepin.com",
        timeout=12,
        output="json",
    )


def test_get_uses_auth_header_and_no_json_body() -> None:
    config = _runtime_config()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.text = '{"ok": true}'
    mock_response.json.return_value = {"ok": True}

    with patch("liepin_cli.core.client.requests.request", return_value=mock_response) as req:
        client = LiepinClient(config)
        result = client.get("/mcp/get-resume")

    assert result == {"ok": True}
    assert req.call_count == 1
    _, kwargs = req.call_args
    assert kwargs["method"] == "GET"
    assert kwargs["url"] == "https://open-agent.liepin.com/mcp/get-resume"
    assert kwargs["headers"]["x-user-token"] == "token-123"
    assert kwargs["timeout"] == 12
    assert "json" not in kwargs


def test_post_sends_json_payload() -> None:
    config = _runtime_config()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.text = "{}"
    mock_response.json.return_value = {}

    payload = {"jobId": 1, "jobKind": "2"}
    with patch("liepin_cli.core.client.requests.request", return_value=mock_response) as req:
        client = LiepinClient(config)
        client.post("/mcp/apply-job", payload)

    _, kwargs = req.call_args
    assert kwargs["method"] == "POST"
    assert kwargs["url"] == "https://open-agent.liepin.com/mcp/apply-job"
    assert kwargs["json"] == payload
    assert kwargs["headers"]["x-user-token"] == "token-123"


def test_get_preserves_base_url_path_prefix() -> None:
    config = RuntimeConfig(
        token="token-123",
        token_source="cli",
        base_url="https://open-agent.liepin.com/proxy/api",
        timeout=12,
        output="json",
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.text = '{"ok": true}'
    mock_response.json.return_value = {"ok": True}

    with patch("liepin_cli.core.client.requests.request", return_value=mock_response) as req:
        client = LiepinClient(config)
        client.get("/mcp/get-resume")

    _, kwargs = req.call_args
    assert kwargs["url"] == "https://open-agent.liepin.com/proxy/api/mcp/get-resume"


def test_unauthorized_status_raises_authorization_error() -> None:
    config = _runtime_config()
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.headers = {"Content-Type": "text/plain"}
    mock_response.text = "unauthorized"

    with patch("liepin_cli.core.client.requests.request", return_value=mock_response):
        client = LiepinClient(config)
        with pytest.raises(AuthorizationError) as exc_info:
            client.get("/any")

    msg = str(exc_info.value)
    assert "401" in msg
    assert "unauthorized" in msg


def test_forbidden_status_raises_authorization_error() -> None:
    config = _runtime_config()
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.headers = {"Content-Type": "text/plain"}
    mock_response.text = ""

    with patch("liepin_cli.core.client.requests.request", return_value=mock_response):
        client = LiepinClient(config)
        with pytest.raises(AuthorizationError) as exc_info:
            client.post("/any", {})

    assert "403" in str(exc_info.value)


def test_non_success_status_raises_request_error_with_status_in_message() -> None:
    config = _runtime_config()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.headers = {"Content-Type": "text/plain"}
    mock_response.text = "server error"

    with patch("liepin_cli.core.client.requests.request", return_value=mock_response):
        client = LiepinClient(config)
        with pytest.raises(RequestError) as exc_info:
            client.get("/any")

    assert "500" in str(exc_info.value)


def test_render_output_json_mode_none_prints_null(capsys: pytest.CaptureFixture[str]) -> None:
    assert render_output(None, "json") is None
    out = capsys.readouterr().out.strip()
    assert json.loads(out) is None


def test_render_output_pretty_mode_none_prints_success(capsys: pytest.CaptureFixture[str]) -> None:
    assert render_output(None, "pretty") is None
    assert capsys.readouterr().out.rstrip("\n") == "成功。"


def test_render_output_json_mode_dict(capsys: pytest.CaptureFixture[str]) -> None:
    data = {"a": 1}
    assert render_output(data, "json") is None
    out = capsys.readouterr().out.rstrip("\n")
    assert json.loads(out) == data
    assert "\n" in out or " " in out  # indent=2 produces whitespace


def test_render_output_pretty_mode_dict(capsys: pytest.CaptureFixture[str]) -> None:
    data = {"a": 1}
    assert render_output(data, "pretty") is None
    out = capsys.readouterr().out.rstrip("\n")
    assert json.loads(out) == data
    assert "\n" in out


def test_render_output_pretty_mode_string(capsys: pytest.CaptureFixture[str]) -> None:
    assert render_output("hello", "pretty") is None
    assert capsys.readouterr().out.rstrip("\n") == "hello"


def test_render_output_string_mode_echoes(capsys: pytest.CaptureFixture[str]) -> None:
    assert render_output("hello", "string") is None
    assert capsys.readouterr().out.rstrip("\n") == "hello"


def test_transport_exception_becomes_request_error() -> None:
    config = _runtime_config()
    with patch(
        "liepin_cli.core.client.requests.request",
        side_effect=requests.ConnectionError("network down"),
    ):
        client = LiepinClient(config)
        with pytest.raises(RequestError) as exc_info:
            client.get("/x")

    assert "请求失败" in str(exc_info.value)
    assert "network down" in str(exc_info.value)


def test_invalid_json_response_becomes_request_error() -> None:
    config = _runtime_config()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json; charset=utf-8"}
    mock_response.text = "not-json"
    mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "not-json", 0)

    with patch("liepin_cli.core.client.requests.request", return_value=mock_response):
        client = LiepinClient(config)
        with pytest.raises(RequestError) as exc_info:
            client.get("/bad-json")

    assert "响应 JSON 非法" in str(exc_info.value)
