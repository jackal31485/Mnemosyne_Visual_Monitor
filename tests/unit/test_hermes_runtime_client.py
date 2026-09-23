from __future__ import annotations

import json
from urllib.error import HTTPError

import pytest

from src.discovery.hermes_runtime_client import (
    HermesRuntimeClient,
    HermesRuntimeConfig,
)


class _Headers:
    def __init__(self, cookies=None):
        self._cookies = cookies or []

    def get_all(self, name):
        if name.lower() == "set-cookie":
            return self._cookies
        return []


class _Response:
    status = 200

    def __init__(self, body=None, cookies=None):
        self._body = body or {"ok": True}
        self.headers = _Headers(cookies)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._body).encode("utf-8")


def test_client_logs_in_and_sends_session_cookie(monkeypatch):
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(
            {
                "method": request.method,
                "url": request.full_url,
                "authorization": request.get_header("Authorization"),
                "cookie": request.get_header("Cookie"),
                "content_type": request.get_header("Content-type"),
                "timeout": timeout,
                "body": (
                    request.data.decode("utf-8")
                    if request.data is not None
                    else None
                ),
            }
        )

        if request.full_url.endswith("/auth/password-login"):
            return _Response(
                {"ok": True, "next": "/"},
                [
                    "hermes_session_at=access-cookie; Path=/; HttpOnly",
                    "hermes_session_rt=refresh-cookie; Path=/; HttpOnly",
                ],
            )

        return _Response()

    monkeypatch.setattr(
        "src.discovery.hermes_runtime_client.urlopen",
        fake_urlopen,
    )

    client = HermesRuntimeClient(
        HermesRuntimeConfig(
            base_url="http://hermes-agent:9119/",
            username="test-user",
            password="secret-password",
            timeout=7.5,
        )
    )

    assert client.status() == {"ok": True}

    assert requests == [
        {
            "method": "POST",
            "url": "http://hermes-agent:9119/auth/password-login",
            "authorization": None,
            "cookie": None,
            "content_type": "application/json",
            "timeout": 7.5,
            "body": json.dumps(
                {
                    "provider": "basic",
                    "username": "test-user",
                    "password": "secret-password",
                }
            ),
        },
        {
            "method": "GET",
            "url": "http://hermes-agent:9119/api/status",
            "authorization": None,
            "cookie": (
                "hermes_session_at=access-cookie; "
                "hermes_session_rt=refresh-cookie"
            ),
            "content_type": None,
            "timeout": 7.5,
            "body": None,
        },
    ]


def test_client_reuses_session_without_relogin(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)

        if request.full_url.endswith("/auth/password-login"):
            return _Response(
                {"ok": True},
                ["hermes_session_at=access-cookie; Path=/"],
            )

        return _Response()

    monkeypatch.setattr(
        "src.discovery.hermes_runtime_client.urlopen",
        fake_urlopen,
    )

    client = HermesRuntimeClient(
        HermesRuntimeConfig(
            base_url="http://hermes-agent:9119",
            username="test-user",
            password="secret-password",
        )
    )

    client.status()
    client.profiles()
    client.active_profile()

    assert calls == [
        "http://hermes-agent:9119/auth/password-login",
        "http://hermes-agent:9119/api/status",
        "http://hermes-agent:9119/api/profiles",
        "http://hermes-agent:9119/api/profiles/active",
    ]


def test_client_exposes_required_runtime_endpoints(monkeypatch):
    paths = []

    def fake_urlopen(request, timeout):
        paths.append(request.full_url)

        if request.full_url.endswith("/auth/password-login"):
            return _Response(
                {"ok": True},
                ["hermes_session_at=access-cookie; Path=/"],
            )

        return _Response()

    monkeypatch.setattr(
        "src.discovery.hermes_runtime_client.urlopen",
        fake_urlopen,
    )

    client = HermesRuntimeClient(
        HermesRuntimeConfig(
            base_url="http://hermes-agent:9119",
            username="user",
            password="password",
        )
    )

    client.status()
    client.profiles()
    client.active_profile()

    assert paths == [
        "http://hermes-agent:9119/auth/password-login",
        "http://hermes-agent:9119/api/status",
        "http://hermes-agent:9119/api/profiles",
        "http://hermes-agent:9119/api/profiles/active",
    ]


def test_from_environment_requires_url_username_and_password(monkeypatch):
    monkeypatch.delenv("HERMES_RUNTIME_URL", raising=False)
    monkeypatch.delenv("HERMES_RUNTIME_USERNAME", raising=False)
    monkeypatch.delenv("HERMES_RUNTIME_PASSWORD", raising=False)

    assert HermesRuntimeClient.from_environment() is None


def test_from_environment_builds_authenticated_client(monkeypatch):
    monkeypatch.setenv("HERMES_RUNTIME_URL", "http://hermes-agent:9119")
    monkeypatch.setenv("HERMES_RUNTIME_USERNAME", "test-user")
    monkeypatch.setenv("HERMES_RUNTIME_PASSWORD", "test-password")

    client = HermesRuntimeClient.from_environment()

    assert client is not None
    assert client.config.base_url == "http://hermes-agent:9119"
    assert client.config.username == "test-user"
    assert client.config.password == "test-password"


def test_http_error_is_normalized(monkeypatch):
    def fake_urlopen(request, timeout):
        if request.full_url.endswith("/auth/password-login"):
            raise HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                {},
                None,
            )

        return _Response()

    monkeypatch.setattr(
        "src.discovery.hermes_runtime_client.urlopen",
        fake_urlopen,
    )

    client = HermesRuntimeClient(
        HermesRuntimeConfig(
            base_url="http://hermes-agent:9119",
            username="bad-user",
            password="bad-password",
        )
    )

    with pytest.raises(RuntimeError, match="login returned HTTP 401"):
        client.status()


def test_credentials_are_not_part_of_response_data(monkeypatch):
    def fake_urlopen(request, timeout):
        if request.full_url.endswith("/auth/password-login"):
            return _Response(
                {"ok": True},
                ["hermes_session_at=secret-cookie; Path=/"],
            )

        return _Response()

    monkeypatch.setattr(
        "src.discovery.hermes_runtime_client.urlopen",
        fake_urlopen,
    )

    client = HermesRuntimeClient(
        HermesRuntimeConfig(
            base_url="http://hermes-agent:9119",
            username="secret-user",
            password="secret-password",
        )
    )

    result = client.status()

    assert "secret-user" not in json.dumps(result)
    assert "secret-password" not in json.dumps(result)
    assert "secret-cookie" not in json.dumps(result)
