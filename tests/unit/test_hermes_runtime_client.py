from __future__ import annotations

import json
from urllib.error import HTTPError

import pytest

from src.discovery.hermes_runtime_client import (
    HermesRuntimeClient,
    HermesRuntimeConfig,
)


class _Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps({"ok": True}).encode("utf-8")


def test_client_sends_bearer_authorization(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["accept"] = request.get_header("Accept")
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(
        "src.discovery.hermes_runtime_client.urlopen",
        fake_urlopen,
    )

    client = HermesRuntimeClient(
        HermesRuntimeConfig(
            base_url="http://hermes-agent:9119/",
            token="secret-token",
            timeout=7.5,
        )
    )

    assert client.status() == {"ok": True}
    assert captured == {
        "url": "http://hermes-agent:9119/api/status",
        "authorization": "Bearer secret-token",
        "accept": "application/json",
        "timeout": 7.5,
    }


def test_client_exposes_required_runtime_endpoints(monkeypatch):
    paths = []

    def fake_urlopen(request, timeout):
        paths.append(request.full_url)
        return _Response()

    monkeypatch.setattr(
        "src.discovery.hermes_runtime_client.urlopen",
        fake_urlopen,
    )

    client = HermesRuntimeClient(
        HermesRuntimeConfig(
            base_url="http://hermes-agent:9119",
            token="token",
        )
    )

    client.status()
    client.profiles()
    client.active_profile()

    assert paths == [
        "http://hermes-agent:9119/api/status",
        "http://hermes-agent:9119/api/profiles",
        "http://hermes-agent:9119/api/profiles/active",
    ]


def test_from_environment_requires_url_and_token(monkeypatch):
    monkeypatch.delenv("HERMES_RUNTIME_URL", raising=False)
    monkeypatch.delenv("HERMES_RUNTIME_TOKEN", raising=False)

    assert HermesRuntimeClient.from_environment() is None


def test_from_environment_builds_authenticated_client(monkeypatch):
    monkeypatch.setenv("HERMES_RUNTIME_URL", "http://hermes-agent:9119")
    monkeypatch.setenv("HERMES_RUNTIME_TOKEN", "test-token")

    client = HermesRuntimeClient.from_environment()

    assert client is not None
    assert client.config.base_url == "http://hermes-agent:9119"
    assert client.config.token == "test-token"


def test_http_error_is_normalized(monkeypatch):
    def fake_urlopen(request, timeout):
        raise HTTPError(
            request.full_url,
            401,
            "Unauthorized",
            {},
            None,
        )

    monkeypatch.setattr(
        "src.discovery.hermes_runtime_client.urlopen",
        fake_urlopen,
    )

    client = HermesRuntimeClient(
        HermesRuntimeConfig(
            base_url="http://hermes-agent:9119",
            token="bad-token",
        )
    )

    with pytest.raises(RuntimeError, match="HTTP 401"):
        client.status()


def test_token_is_not_part_of_response_data(monkeypatch):
    def fake_urlopen(request, timeout):
        return _Response()

    monkeypatch.setattr(
        "src.discovery.hermes_runtime_client.urlopen",
        fake_urlopen,
    )

    client = HermesRuntimeClient(
        HermesRuntimeConfig(
            base_url="http://hermes-agent:9119",
            token="secret-token",
        )
    )

    result = client.status()

    assert "secret-token" not in json.dumps(result)
