from __future__ import annotations

from datetime import datetime

import pytest

from src.domain.temporal_contradiction import (
    TemporalContradiction,
    TemporalStateAssertion,
)
from src.domain.temporal_precision import PrecisionInterval
from src.services.temporal_conflict_service import (
    TemporalConflictResult,
    TemporalConflictService,
)


def interval(
    evidence_id: int,
    start: datetime,
    end: datetime,
    precision: str = "day",
) -> PrecisionInterval:
    return PrecisionInterval(
        evidence_id=evidence_id,
        start=start,
        end=end,
        precision=precision,
    )


def assertion(
    evidence_id: int,
    subject_id: str,
    state: str,
    start: datetime,
    end: datetime,
    precision: str = "day",
) -> TemporalStateAssertion:
    return TemporalStateAssertion(
        evidence_id=evidence_id,
        subject_type="entity",
        subject_id=subject_id,
        state=state,
        interval=interval(
            evidence_id,
            start,
            end,
            precision,
        ),
    )


def test_service_returns_immutable_result() -> None:
    service = TemporalConflictService()

    result = service.detect(
        (
            assertion(
                1,
                "entity-1",
                "active",
                datetime(2024, 1, 10),
                datetime(2024, 1, 10, 23, 59, 59),
            ),
            assertion(
                2,
                "entity-1",
                "inactive",
                datetime(2024, 1, 10),
                datetime(2024, 1, 10, 23, 59, 59),
            ),
        )
    )

    assert isinstance(result, TemporalConflictResult)
    assert result.conflict_count == 1
    assert isinstance(result.contradictions[0], TemporalContradiction)


def test_service_delegates_to_canonical_contradiction_semantics() -> None:
    service = TemporalConflictService()

    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 31, 23, 59, 59),
        ),
        assertion(
            2,
            "entity-1",
            "inactive",
            datetime(2024, 1, 10),
            datetime(2024, 1, 20, 23, 59, 59),
        ),
    )

    result = service.detect(values)

    assert result.conflict_count == 1
    assert result.contradictions[0].relation == "contains"


def test_sequential_state_change_is_not_a_conflict() -> None:
    service = TemporalConflictService()

    result = service.detect(
        (
            assertion(
                1,
                "entity-1",
                "active",
                datetime(2024, 1, 1),
                datetime(2024, 1, 10, 23, 59, 59),
            ),
            assertion(
                2,
                "entity-1",
                "inactive",
                datetime(2024, 1, 11),
                datetime(2024, 1, 20, 23, 59, 59),
            ),
        )
    )

    assert result.contradictions == ()
    assert result.conflict_count == 0


def test_same_state_is_not_a_conflict() -> None:
    service = TemporalConflictService()

    result = service.detect(
        (
            assertion(
                1,
                "entity-1",
                "active",
                datetime(2024, 1, 10),
                datetime(2024, 1, 10, 23, 59, 59),
            ),
            assertion(
                2,
                "entity-1",
                "active",
                datetime(2024, 1, 10),
                datetime(2024, 1, 10, 23, 59, 59),
            ),
        )
    )

    assert result.contradictions == ()


def test_different_subjects_are_not_conflicts() -> None:
    service = TemporalConflictService()

    result = service.detect(
        (
            assertion(
                1,
                "entity-1",
                "active",
                datetime(2024, 1, 10),
                datetime(2024, 1, 10, 23, 59, 59),
            ),
            assertion(
                2,
                "entity-2",
                "inactive",
                datetime(2024, 1, 10),
                datetime(2024, 1, 10, 23, 59, 59),
            ),
        )
    )

    assert result.contradictions == ()


def test_indeterminate_overlap_is_not_a_conflict() -> None:
    service = TemporalConflictService()

    result = service.detect(
        (
            assertion(
                1,
                "entity-1",
                "active",
                datetime(2024, 1, 1),
                datetime(2024, 1, 10, 23, 59, 59),
                precision="day",
            ),
            assertion(
                2,
                "entity-1",
                "inactive",
                datetime(2024, 1, 5),
                datetime(2024, 1, 15, 23, 59, 59),
                precision="day",
            ),
        )
    )

    assert result.contradictions == ()


def test_empty_input_returns_empty_result() -> None:
    service = TemporalConflictService()

    result = service.detect(())

    assert result.contradictions == ()
    assert result.conflict_count == 0


def test_invalid_assertion_input_is_rejected() -> None:
    service = TemporalConflictService()

    with pytest.raises(TypeError):
        service.detect([object()])


def test_detect_many_preserves_group_order() -> None:
    service = TemporalConflictService()

    first_group = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 10),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
        assertion(
            2,
            "entity-1",
            "inactive",
            datetime(2024, 1, 10),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
    )

    second_group = (
        assertion(
            3,
            "entity-2",
            "active",
            datetime(2024, 1, 10),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
        assertion(
            4,
            "entity-2",
            "active",
            datetime(2024, 1, 10),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
    )

    results = service.detect_many((first_group, second_group))

    assert len(results) == 2
    assert results[0].conflict_count == 1
    assert results[1].conflict_count == 0


def test_detect_accepts_generators() -> None:
    service = TemporalConflictService()

    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 10),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
        assertion(
            2,
            "entity-1",
            "inactive",
            datetime(2024, 1, 10),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
    )

    result = service.detect(value for value in values)

    assert result.conflict_count == 1


def test_service_does_not_persist_conflicts(tmp_path) -> None:
    service = TemporalConflictService()

    result = service.detect(
        (
            assertion(
                1,
                "entity-1",
                "active",
                datetime(2024, 1, 10),
                datetime(2024, 1, 10, 23, 59, 59),
            ),
            assertion(
                2,
                "entity-1",
                "inactive",
                datetime(2024, 1, 10),
                datetime(2024, 1, 10, 23, 59, 59),
            ),
        )
    )

    assert result.conflict_count == 1
    assert list(tmp_path.iterdir()) == []


def test_service_does_not_create_a_second_conflict_model() -> None:
    service = TemporalConflictService()

    result = service.detect(
        (
            assertion(
                1,
                "entity-1",
                "active",
                datetime(2024, 1, 10),
                datetime(2024, 1, 10, 23, 59, 59),
            ),
            assertion(
                2,
                "entity-1",
                "inactive",
                datetime(2024, 1, 10),
                datetime(2024, 1, 10, 23, 59, 59),
            ),
        )
    )

    assert type(result.contradictions[0]).__module__ == (
        "src.domain.temporal_contradiction"
    )
