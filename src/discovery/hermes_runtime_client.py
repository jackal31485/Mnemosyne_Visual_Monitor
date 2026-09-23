from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json
import os


@dataclass(frozen=True)
class HermesRuntimeConfig:
    base_url: str
    username: str
    password: str
    timeout: float = 5.0


class HermesRuntimeClient:
    """Read-only authenticated HTTP client for Hermes-Agent runtime data."""

    def __init__(self, config: HermesRuntimeConfig):
        self.config = config
        self._cookies: dict[str, str] = {}

    @classmethod
    def from_environment(cls) -> Optional["HermesRuntimeClient"]:
        base_url = os.getenv("HERMES_RUNTIME_URL", "").strip()
        username = os.getenv("HERMES_RUNTIME_USERNAME", "").strip()
        password = os.getenv("HERMES_RUNTIME_PASSWORD", "").strip()

        if not base_url or not username or not password:
            return None

        return cls(
            HermesRuntimeConfig(
                base_url=base_url,
                username=username,
                password=password,
            )
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ):
        request_headers = {
            "Accept": "application/json",
            **(headers or {}),
        }

        if self._cookies:
            request_headers["Cookie"] = "; ".join(
                f"{name}={value}"
                for name, value in self._cookies.items()
            )

        request = Request(
            self.config.base_url.rstrip("/") + path,
            data=data,
            method=method,
            headers=request_headers,
        )

        return urlopen(request, timeout=self.config.timeout)

    def _login(self) -> None:
        payload = json.dumps(
            {
                "provider": "basic",
                "username": self.config.username,
                "password": self.config.password,
            }
        ).encode("utf-8")

        try:
            with self._request(
                "POST",
                "/auth/password-login",
                data=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status != 200:
                    raise RuntimeError(
                        f"Hermes-Agent login returned HTTP {response.status}"
                    )

                for header in response.headers.get_all("Set-Cookie") or []:
                    cookie_pair = header.split(";", 1)[0]
                    if "=" not in cookie_pair:
                        continue
                    name, value = cookie_pair.split("=", 1)
                    if name.startswith("hermes_session_"):
                        self._cookies[name] = value

                if not self._cookies:
                    raise RuntimeError(
                        "Hermes-Agent login did not return a session cookie"
                    )

                response.read()

        except HTTPError as exc:
            raise RuntimeError(
                f"Hermes-Agent login returned HTTP {exc.code}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"Unable to reach Hermes-Agent: {exc.reason}"
            ) from exc

    def _get_json(self, path: str) -> dict[str, Any]:
        if not self._cookies:
            self._login()

        try:
            with self._request("GET", path) as response:
                if response.status != 200:
                    raise RuntimeError(
                        f"Hermes-Agent returned HTTP {response.status}"
                    )

                data = json.loads(response.read().decode("utf-8"))

        except HTTPError as exc:
            raise RuntimeError(
                f"Hermes-Agent returned HTTP {exc.code}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"Unable to reach Hermes-Agent: {exc.reason}"
            ) from exc

        if not isinstance(data, dict):
            raise TypeError("Hermes-Agent response must be a JSON object")

        return data

    def status(self) -> dict[str, Any]:
        return self._get_json("/api/status")

    def profiles(self) -> dict[str, Any]:
        return self._get_json("/api/profiles")

    def active_profile(self) -> dict[str, Any]:
        return self._get_json("/api/profiles/active")
