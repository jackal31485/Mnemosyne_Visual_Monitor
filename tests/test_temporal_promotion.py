from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.domain.temporal_assertion import TemporalAssertion
from src.domain.temporal_change import TemporalChangeAssertion
from src.domain.temporal_promotion import TemporalPromotionService


@dataclass
class RecordingWriter:
    calls: list[dict]

    def add(self, **kwargs):
        self.calls.append(kwargs)
        return {"id": len(self.calls), **kwargs}


def temporal_assertion() -> TemporalAssertion:
    return TemporalAssertion(
        collective_entry_id=21,
        subject_type="memory",
        subject_id="memory-21",
        temporal_relation="at",
        precision="day",
        extraction_method="explicit_temporal_v1",
        source_memory_id="memory-21",
        source_profile="athena",
        start_time="2026-03-15",
        confidence=0.91,
    )


def change_assertion() -> TemporalChangeAssertion:
    return TemporalChangeAssertion(
        collective_entry_id=22,
        subject_type="memory",
        subject_id="memory-22",
        change_type="state_change",
        previous_state="planned",
        new_state="active",
        extraction_method="explicit_state_change_v1",
        source_memory_id="memory-22",
        source_profile="horus",
    )


def test_temporal_assertion_is_translated_without_mutation() -> None:
    writer = RecordingWriter([])
    service = TemporalPromotionService(writer)
    assertion = temporal_assertion()

    result = service.promote(assertion)

    assert result.assertion_kind == "temporal"
    assert len(writer.calls) == 1

    call = writer.calls[0]

    assert call["collective_entry_id"] == 21
    assert call["subject_type"] == "memory"
    assert call["subject_id"] == "memory-21"
    assert call["temporal_relation"] == "at"
    assert call["precision"] == "day"
    assert call["start_time"] == "2026-03-15"
    assert call["confidence"] == 0.91
    assert call["source_memory_id"] == "memory-21"
    assert call["source_profile"] == "athena"


def test_change_assertion_preserves_provenance() -> None:
    writer = RecordingWriter([])
    service = TemporalPromotionService(writer)

    result = service.promote_change(change_assertion())

    assert result.assertion_kind == "state_change"

    call = writer.calls[0]

    assert call["collective_entry_id"] == 22
    assert call["subject_id"] == "memory-22"
    assert call["temporal_relation"] == "during"
    assert call["precision"] == "unknown"
    assert call["source_memory_id"] == "memory-22"
    assert call["source_profile"] == "horus"
    assert call["extraction_method"] == "explicit_state_change_v1"


def test_promotion_does_not_invent_state_change_dates() -> None:
    writer = RecordingWriter([])
    service = TemporalPromotionService(writer)

    service.promote_change(change_assertion())

    call = writer.calls[0]

    assert call["start_time"] is None
    assert call["end_time"] is None


def test_promote_many_preserves_order() -> None:
    writer = RecordingWriter([])
    service = TemporalPromotionService(writer)

    first = temporal_assertion()
    second = TemporalAssertion(
        collective_entry_id=23,
        subject_type="memory",
        subject_id="memory-23",
        temporal_relation="after",
        precision="unknown",
        extraction_method="explicit_temporal_v1",
        source_memory_id="memory-23",
        source_profile="odin",
    )

    results = service.promote_many([first, second])

    assert [r.evidence["id"] for r in results] == [1, 2]
    assert [c["collective_entry_id"] for c in writer.calls] == [21, 23]


def test_promote_changes_preserves_order() -> None:
    writer = RecordingWriter([])
    service = TemporalPromotionService(writer)

    first = change_assertion()
    second = TemporalChangeAssertion(
        collective_entry_id=24,
        subject_type="memory",
        subject_id="memory-24",
        change_type="activation",
        previous_state=None,
        new_state="ready",
        extraction_method="explicit_state_change_v1",
        source_memory_id="memory-24",
        source_profile="odin",
    )

    results = service.promote_changes([first, second])

    assert len(results) == 2
    assert [c["collective_entry_id"] for c in writer.calls] == [22, 24]


def test_wrong_temporal_assertion_type_is_rejected() -> None:
    writer = RecordingWriter([])
    service = TemporalPromotionService(writer)

    with pytest.raises(TypeError):
        service.promote("not-an-assertion")  # type: ignore[arg-type]


def test_wrong_change_assertion_type_is_rejected() -> None:
    writer = RecordingWriter([])
    service = TemporalPromotionService(writer)

    with pytest.raises(TypeError):
        service.promote_change("not-an-assertion")  # type: ignore[arg-type]


def test_promote_many_requires_list() -> None:
    writer = RecordingWriter([])
    service = TemporalPromotionService(writer)

    with pytest.raises(TypeError):
        service.promote_many(())  # type: ignore[arg-type]


def test_promote_changes_requires_list() -> None:
    writer = RecordingWriter([])
    service = TemporalPromotionService(writer)

    with pytest.raises(TypeError):
        service.promote_changes(())  # type: ignore[arg-type]
