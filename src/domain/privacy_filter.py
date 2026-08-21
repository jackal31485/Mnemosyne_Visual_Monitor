# privacy_filter.py
"""
Privacy filtering interface and a simple regex‑based implementation.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Protocol
from .models import PrivacyResult

class PrivacyFilter(Protocol):
    """Protocol used by the Mediation Plane to mask PII from a memory payload.

    The ``filter`` method receives a JSON‑serializable dictionary (typically a
    representation of a Mnemosyne memory) and must return a :class:`PrivacyResult`
    containing a list of regex patterns that were masked and the sanitized content.
    """

    def filter(self, content: Dict[str, Any]) -> PrivacyResult:
        ...

class SimpleRegexFilter:
    """Experimental privacy filter. Masks any sequences that looks like an email or phone number."""

    def __init__(self) -> None:
        self.email_pat = re.compile(r"[\w.-]+@[\w.-]+")
        self.phone_pat = re.compile(r"(?:\+?1[-\.\s]?)?(?:\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4})")

    def filter(self, content: Dict[str, Any]) -> PrivacyResult:
        text = str(content.get("text", ""))
        masked_fields: list[str] = []
        sanitized = text
        for pat in (self.email_pat, self.phone_pat):
            matches = list(pat.finditer(text))
            if matches:
                masked_fields.append(f"{pat.pattern}")
                # replace each match with "[REDACTED]"
                for m in matches:
                    start, end = m.span()
                    sanitized = sanitized[:start] + "[REDACTED]" + sanitized[end:]
        return PrivacyResult(masked_fields=masked_fields, sanitized_content=sanitized)
