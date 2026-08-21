import sys, os
sys.path.append(os.path.join(os.getcwd(), "src"))

import pytest
from domain import privacy_filter as pf_module

# SimpleRegexFilter should redact emails and phone numbers.

def test_email_redaction():
    filt = pf_module.SimpleRegexFilter()
    content = {"text": "contact me at user@example.com or +1 555-123-4567"}
    result = filt.filter(content)
    # email and phone should be redacted
    assert "[REDACTED]" in result.sanitized_content
    assert len(result.masked_fields) >= 2
    assert any("@" in pat for pat in result.masked_fields)

# If there's nothing to mask, the original text is untouched.

def test_no_match():
    filt = pf_module.SimpleRegexFilter()
    content = {"text": "Hello world"}
    result = filt.filter(content)
    assert result.sanitized_content == "Hello world"
    assert result.masked_fields == []
