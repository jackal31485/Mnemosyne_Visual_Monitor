from src.retrieval.multilingual_retrieval import (
    QueryScript,
    SemanticCapability,
    build_multilingual_profile,
    classify_query_script,
    normalize_multilingual_query,
)


def test_nfkc_normalization_preserves_query_meaning():
    query = "  Café\u00a0Mnemosyne  "

    assert normalize_multilingual_query(query) == "Café Mnemosyne"


def test_latin_script_is_semantically_supported():
    profile = build_multilingual_profile(
        "How did we fix the timeline API?"
    )

    assert profile.script is QueryScript.LATIN
    assert profile.semantic_capability is SemanticCapability.SUPPORTED
    assert profile.lexical_supported is True


def test_non_latin_script_is_lexical_only():
    profile = build_multilingual_profile("メモリの検索")

    assert profile.script is QueryScript.NON_LATIN
    assert profile.semantic_capability is SemanticCapability.UNSUPPORTED
    assert profile.lexical_supported is True
    assert "English-compatible only" in profile.semantic_reason


def test_mixed_script_is_explicitly_capability_limited():
    profile = build_multilingual_profile("Mnemosyne メモリ")

    assert profile.script is QueryScript.MIXED
    assert profile.semantic_capability is SemanticCapability.UNSUPPORTED
    assert profile.lexical_supported is True


def test_punctuation_and_numbers_do_not_create_mixed_script():
    assert classify_query_script("Phase 15: retrieval? 2026!") is QueryScript.LATIN


def test_non_letter_content_has_unknown_script():
    assert classify_query_script("12345 !?") is QueryScript.UNKNOWN


def test_normalization_is_deterministic():
    query = "  Mnemosyne\u3000retrieval  "

    first = build_multilingual_profile(query)
    second = build_multilingual_profile(query)

    assert first == second
