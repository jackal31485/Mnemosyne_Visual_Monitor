from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.domain.temporal_assertion import TemporalAssertion
from src.domain.temporal_change import TemporalChangeAssertion
from src.domain.temporal_pipeline import (
    TemporalExtractionPromotionPipeline,
)
from src.domain.temporal_promotion import (
    TemporalPromotionResult,
)


@dataclass
class FakeTemporalExtractor:
    calls: list[tuple[str, dict]]

    def extract(self, text: str, **kwargs):
        self.calls.append((text, kwargs))
        return [
            TemporalAssertion(
                collective_entry_id=kwargs["collective_entry_id"],
                subject_type="memory",
                subject_id=kwargs["source_memory_id"],
                temporal_relation="at",
                precision="day",
                extraction_method="test_temporal",
                source_memory_id=kwargs["source_memory_id"],
                source_profile=kwargs["source_profile"],
                start_time="2026-09-12",
            )
        ]


@dataclass
class FakeChangeExtractor:
    calls: list[tuple[str, dict]]

    def extract(self, text: str, **kwargs):
        self.calls.append((text, kwargs))
        return [
            TemporalChangeAssertion(
                collective_entry_id=kwargs["collective_entry_id"],
                subject_type="memory",
                subject_id=kwargs["source_memory_id"],
                change_type="state_change",
                previous_state="old",
                new_state="new",
                extraction_method="test_change",
                source_memory_id=kwargs["source_memory_id"],
                source_profile=kwargs["source_profile"],
            )
        ]


class FakePromotionService:
    def __init__(self):
        self.temporal_calls = []
        self.change_calls = []

    def promote_many(self, assertions):
        assertions = list(assertions)
        self.temporal_calls.append(assertions)
        return [
            TemporalPromotionResult(
                evidence=object(),
                assertion_kind="temporal",
            )
            for _ in assertions
        ]

    def promote_changes(self, assertions):
        assertions = list(assertions)
        self.change_calls.append(assertions)
        return [
            TemporalPromotionResult(
                evidence=object(),
                assertion_kind="state_change",
            )
            for _ in assertions
        ]


def test_pipeline_extracts_and_promotes_both_assertion_types():
    temporal_extractor = FakeTemporalExtractor([])
    change_extractor = FakeChangeExtractor([])
    promotion_service = FakePromotionService()

    pipeline = TemporalExtractionPromotionPipeline(
        temporal_extractor=temporal_extractor,
        change_extractor=change_extractor,
        promotion_service=promotion_service,
    )

    result = pipeline.process(
        "The event happened on September 12, 2026 and changed from old to new.",
        collective_entry_id=42,
        source_memory_id="memory-42",
        source_profile="athena",
    )

    assert result.total_assertions == 2
    assert result.total_evidence == 2
    assert len(result.temporal_assertions) == 1
    assert len(result.change_assertions) == 1
    assert len(result.temporal_evidence) == 1
    assert len(result.change_evidence) == 1


def test_pipeline_preserves_caller_context_for_both_extractors():
    temporal_extractor = FakeTemporalExtractor([])
    change_extractor = FakeChangeExtractor([])
    promotion_service = FakePromotionService()

    pipeline = TemporalExtractionPromotionPipeline(
        temporal_extractor=temporal_extractor,
        change_extractor=change_extractor,
        promotion_service=promotion_service,
    )

    pipeline.process(
        "Example text.",
        collective_entry_id=77,
        source_memory_id="memory-77",
        source_profile="horus",
    )

    expected = {
        "collective_entry_id": 77,
        "source_memory_id": "memory-77",
        "source_profile": "horus",
    }

    assert temporal_extractor.calls[0][1] == expected
    assert change_extractor.calls[0][1] == expected


def test_pipeline_preserves_assertion_order():
    temporal_extractor = FakeTemporalExtractor([])
    change_extractor = FakeChangeExtractor([])
    promotion_service = FakePromotionService()

    pipeline = TemporalExtractionPromotionPipeline(
        temporal_extractor=temporal_extractor,
        change_extractor=change_extractor,
        promotion_service=promotion_service,
    )

    result = pipeline.process(
        "Example text.",
        collective_entry_id=1,
        source_memory_id="memory-1",
        source_profile="odin",
    )

    assert (
        promotion_service.temporal_calls[0]
        == list(result.temporal_assertions)
    )
    assert (
        promotion_service.change_calls[0]
        == list(result.change_assertions)
    )


def test_pipeline_handles_no_temporal_matches():
    class EmptyTemporalExtractor:
        def extract(self, text: str, **kwargs):
            return []

    class EmptyChangeExtractor:
        def extract(self, text: str, **kwargs):
            return []

    promotion_service = FakePromotionService()

    pipeline = TemporalExtractionPromotionPipeline(
        temporal_extractor=EmptyTemporalExtractor(),
        change_extractor=EmptyChangeExtractor(),
        promotion_service=promotion_service,
    )

    result = pipeline.process(
        "Nothing temporal here.",
        collective_entry_id=1,
        source_memory_id="memory-1",
        source_profile="thoth",
    )

    assert result.total_assertions == 0
    assert result.total_evidence == 0
    assert promotion_service.temporal_calls == [[]]
    assert promotion_service.change_calls == [[]]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("collective_entry_id", "not-an-int"),
        ("source_memory_id", 123),
        ("source_profile", 123),
    ],
)
def test_pipeline_rejects_invalid_context(field, value):
    promotion_service = FakePromotionService()
    pipeline = TemporalExtractionPromotionPipeline(
        temporal_extractor=FakeTemporalExtractor([]),
        change_extractor=FakeChangeExtractor([]),
        promotion_service=promotion_service,
    )

    kwargs = {
        "collective_entry_id": 1,
        "source_memory_id": "memory-1",
        "source_profile": "athena",
    }
    kwargs[field] = value

    with pytest.raises(TypeError):
        pipeline.process("Example.", **kwargs)
