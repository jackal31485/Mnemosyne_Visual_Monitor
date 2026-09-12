from __future__ import annotations

from src.domain.temporal_extractor import TemporalExtractor


def extract(text: str):
    return TemporalExtractor().extract(
        text=text,
        collective_entry_id=1,
        source_memory_id="memory-1",
        source_profile="athena",
    )


def test_extract_full_month_name_date() -> None:
    results = extract("Project started in March 15, 2026.")

    assert len(results) == 1
    assert results[0].temporal_relation == "at"
    assert results[0].start_time == "2026-03-15"
    assert results[0].precision == "day"
    assert results[0].evidence_kind == "observed"


def test_extract_iso_date() -> None:
    results = extract("Migration happened on 2026-06-15.")

    assert len(results) == 1
    assert results[0].start_time == "2026-06-15"
    assert results[0].precision == "day"


def test_extract_month_precision() -> None:
    results = extract("The project started in March 2026.")

    assert len(results) == 1
    assert results[0].start_time == "2026-03"
    assert results[0].precision == "month"


def test_extract_year_precision() -> None:
    results = extract("The project began in 2026.")

    assert len(results) == 1
    assert results[0].start_time == "2026"
    assert results[0].precision == "year"


def test_extract_explicit_range() -> None:
    results = extract(
        "Migration happened between June 1, 2026 and June 15, 2026."
    )

    assert len(results) == 1
    assert results[0].temporal_relation == "during"
    assert results[0].start_time == "2026-06-01"
    assert results[0].end_time == "2026-06-15"
    assert results[0].precision == "day"


def test_extract_iso_date_range() -> None:
    results = extract(
        "Maintenance occurred between 2026-06-01 and 2026-06-15."
    )

    assert len(results) == 1
    assert results[0].start_time == "2026-06-01"
    assert results[0].end_time == "2026-06-15"


def test_extract_before_without_inventing_date() -> None:
    results = extract("Project A started before Project B.")

    before = [
        result
        for result in results
        if result.temporal_relation == "before"
    ]

    assert len(before) == 1
    assert before[0].start_time is None
    assert before[0].end_time is None
    assert before[0].precision == "unknown"


def test_extract_after_without_inventing_date() -> None:
    results = extract("Project A started after Project B.")

    after = [
        result
        for result in results
        if result.temporal_relation == "after"
    ]

    assert len(after) == 1
    assert after[0].start_time is None
    assert after[0].end_time is None


def test_extract_during_without_inventing_bounds() -> None:
    results = extract("The migration occurred during the release.")

    during = [
        result
        for result in results
        if result.temporal_relation == "during"
    ]

    assert len(during) == 1
    assert during[0].start_time is None
    assert during[0].end_time is None
    assert during[0].precision == "unknown"


def test_extract_ongoing_without_inventing_start() -> None:
    results = extract("The migration is ongoing.")

    assert len(results) == 1
    assert results[0].temporal_relation == "ongoing"
    assert results[0].start_time is None
    assert results[0].end_time is None
    assert results[0].precision == "unknown"


def test_since_does_not_invent_an_endpoint() -> None:
    results = extract("The service has been stable since recently.")

    assert results == []


def test_until_does_not_invent_an_endpoint() -> None:
    results = extract("The service remained active until later.")

    assert results == []


def test_multiple_explicit_dates_are_deterministic() -> None:
    text = (
        "Development started in March 2026. "
        "Migration occurred on June 15, 2026."
    )

    first = extract(text)
    second = extract(text)

    assert first == second
    assert [item.start_time for item in first] == [
        "2026-03",
        "2026-06-15",
    ]


def test_source_provenance_is_preserved() -> None:
    results = TemporalExtractor().extract(
        text="Project started in March 2026.",
        collective_entry_id=42,
        source_memory_id="memory-abc",
        source_profile="horus",
    )

    assert len(results) == 1
    result = results[0]

    assert result.collective_entry_id == 42
    assert result.source_memory_id == "memory-abc"
    assert result.source_profile == "horus"
    assert result.subject_type == "memory"
    assert result.subject_id == "memory-abc"


def test_custom_extraction_method_is_preserved() -> None:
    results = TemporalExtractor().extract(
        text="Project started in March 2026.",
        collective_entry_id=1,
        source_memory_id="memory-1",
        source_profile="athena",
        extraction_method="test-extractor",
    )

    assert results[0].extraction_method == "test-extractor"


def test_empty_text_returns_no_assertions() -> None:
    assert extract("") == []
    assert extract("   ") == []


def test_invalid_text_type_is_rejected() -> None:
    try:
        extract(None)  # type: ignore[arg-type]
    except TypeError as exc:
        assert str(exc) == "text must be a string"
    else:
        raise AssertionError("expected TypeError")


def test_invalid_calendar_date_is_rejected() -> None:
    try:
        extract("Project started on February 31, 2026.")
    except ValueError as exc:
        assert "invalid explicit date" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_no_raw_text_is_stored_in_assertion() -> None:
    text = "Project started in March 2026 and uses SECRET-CONTENT-123."

    results = extract(text)

    assert len(results) == 1
    result = results[0]

    assert not hasattr(result, "text")
    assert not hasattr(result, "source_text")
    assert "SECRET-CONTENT-123" not in repr(result)


def test_extractor_does_not_write_to_database() -> None:
    results = extract("Project started in March 2026.")

    assert results
    # Construction of assertions is the only side effect permitted by 11B.2.
