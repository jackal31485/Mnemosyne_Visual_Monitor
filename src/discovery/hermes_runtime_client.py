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
    token: str
    timeout: float = 5.0


class HermesRuntimeClient:
    """Read-only authenticated HTTP client for Hermes-Agent runtime data."""

    def __init__(self, config: HermesRuntimeConfig):
        self.config = config

    @classmethod
    def from_environment(cls) -> Optional["HermesRuntimeClient"]:
        base_url = os.getenv("HERMES_RUNTIME_URL", "").strip()
        token = os.getenv("HERMES_RUNTIME_TOKEN", "").strip()

        if not base_url or not token:
            return None

        return cls(
            HermesRuntimeConfig(
                base_url=base_url,
                token=token,
            )
        )

    def _get_json(self, path: str) -> dict[str, Any]:
        url = self.config.base_url.rstrip("/") + path
        request = Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.config.token}",
            },
        )

        try:
            with urlopen(request, timeout=self.config.timeout) as response:
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
