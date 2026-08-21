# identity_provider.py
from __future__ import annotations
import os
from typing import Dict

class IdentityProvider:
    """Minimal in‑memory provider for Phase 2.
    Tokens are simple strings 'token-<profile>' mapping to profile names."""
    def __init__(self):
        self._tokens: Dict[str, str] = {}

    def register(self, profile: str):
        token = f"token-{profile}"
        self._tokens[token] = profile
        return token

    def validate_token(self, token: str) -> str:
        if token not in self._tokens:
            raise PermissionError("Invalid token")
        return self._tokens[token]
