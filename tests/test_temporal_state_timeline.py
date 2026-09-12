from datetime import datetime

import pytest

from src.domain.temporal_aggregation import TemporalEvidenceGroup
from src.domain.temporal_contradiction import TemporalStateAssertion
from src.domain.temporal_precision import PrecisionInterval
from src.domain.temporal_state_timeline import (
    TemporalStateTimeline,
    TemporalStateTransition,
    TemporalTimelineEntry,
    build_state_timeline,
    build_state_timelines,
)


def assertion(
    evidence_id: int,
    state: str,
    start: str,
    end: str,
    *,
    subject_type: str = "entity",
    subject_id: str = "device-1",
) -> TemporalStateAssertion:
    return TemporalStateAssertion(
        evidence_id=evidence_id,
        subject_type=subject_type,
        subject_id=subject_id,
        state=state,
        interval=PrecisionInterval(
            evidence_id=evidence_id,
            start=datetime.fromisoformat(start),
            end=datetime.fromisoformat(end),
            precision="day",
        ),
    )


def group(*assertions_: TemporalStateAssertion) -> TemporalEvidenceGroup:
    return TemporalEvidenceGroup(
        subject_type=assertions_[0].subject_type,
        subject_id=assertions_[0].subject_id,
        assertions=tuple(assertions_),
    )


def test_timeline_preserves_subject():
    timeline = build_state_timeline(
        group(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            )
        )
    )

    assert timeline.subject_type == "entity"
    assert timeline.subject_id == "device-1"


def test_timeline_creates_entries():
    timeline = build_state_timeline(
        group(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            )
        )
    )

    assert timeline.entries == (
        TemporalTimelineEntry(
            evidence_id=1,
            subject_type="entity",
            subject_id="device-1",
            state="active",
            start=datetime.fromisoformat("2026-01-01T00:00:00"),
            end=datetime.fromisoformat("2026-01-01T23:59:59"),
        ),
    )


def test_entries_are_chronologically_ordered():
    timeline = build_state_timeline(
        group(
            assertion(
                2,
                "inactive",
                "2026-02-01T00:00:00",
                "2026-02-01T23:59:59",
            ),
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            ),
        )
    )

    assert [entry.evidence_id for entry in timeline.entries] == [1, 2]


def test_equal_times_use_evidence_id_as_tiebreaker():
    timeline = build_state_timeline(
        group(
            assertion(
                2,
                "inactive",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            ),
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            ),
        )
    )

    assert [entry.evidence_id for entry in timeline.entries] == [1, 2]


def test_adjacent_entries_create_transition():
    timeline = build_state_timeline(
        group(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            ),
            assertion(
                2,
                "inactive",
                "2026-01-02T00:00:00",
                "2026-01-02T23:59:59",
            ),
        )
    )

    assert len(timeline.transitions) == 1
    transition = timeline.transitions[0]

    assert transition.from_evidence_id == 1
    assert transition.to_evidence_id == 2
    assert transition.from_state == "active"
    assert transition.to_state == "inactive"


def test_transition_preserves_temporal_relation():
    timeline = build_state_timeline(
        group(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            ),
            assertion(
                2,
                "inactive",
                "2026-01-02T00:00:00",
                "2026-01-02T23:59:59",
            ),
        )
    )

    assert timeline.transitions[0].relation == "before"
    assert timeline.transitions[0].certainty == "definite"


def test_transition_can_be_indeterminate():
    timeline = build_state_timeline(
        group(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-03T23:59:59",
            ),
            assertion(
                2,
                "inactive",
                "2026-01-03T00:00:00",
                "2026-01-05T23:59:59",
            ),
        )
    )

    assert timeline.transitions[0].relation == "overlaps"
    assert timeline.transitions[0].certainty == "indeterminate"


def test_single_entry_has_no_transitions():
    timeline = build_state_timeline(
        group(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            )
        )
    )

    assert timeline.transitions == ()


def test_two_entries_create_one_transition():
    timeline = build_state_timeline(
        group(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            ),
            assertion(
                2,
                "inactive",
                "2026-01-02T00:00:00",
                "2026-01-02T23:59:59",
            ),
        )
    )

    assert len(timeline.transitions) == 1


def test_three_entries_create_two_transitions():
    timeline = build_state_timeline(
        group(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            ),
            assertion(
                2,
                "inactive",
                "2026-01-02T00:00:00",
                "2026-01-02T23:59:59",
            ),
            assertion(
                3,
                "maintenance",
                "2026-01-03T00:00:00",
                "2026-01-03T23:59:59",
            ),
        )
    )

    assert len(timeline.transitions) == 2


def test_build_state_timelines_is_deterministic():
    groups = [
        group(
            assertion(
                2,
                "inactive",
                "2026-02-01T00:00:00",
                "2026-02-01T23:59:59",
                subject_id="device-2",
            )
        ),
        group(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
                subject_id="device-1",
            )
        ),
    ]

    timelines = build_state_timelines(groups)

    assert [timeline.subject_id for timeline in timelines] == [
        "device-1",
        "device-2",
    ]


def test_build_state_timelines_accepts_empty_input():
    assert build_state_timelines([]) == ()


def test_invalid_group_type_is_rejected():
    with pytest.raises(TypeError):
        build_state_timeline(object())  # type: ignore[arg-type]


def test_invalid_group_collection_member_is_rejected():
    with pytest.raises(TypeError):
        build_state_timelines([object()])  # type: ignore[list-item]


def test_timeline_is_immutable():
    timeline = build_state_timeline(
        group(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            )
        )
    )

    with pytest.raises(AttributeError):
        timeline.subject_id = "other"  # type: ignore[misc]


def test_transition_is_immutable():
    transition = TemporalStateTransition(
        subject_type="entity",
        subject_id="device-1",
        from_evidence_id=1,
        to_evidence_id=2,
        from_state="active",
        to_state="inactive",
        relation="before",
        certainty="definite",
    )

    with pytest.raises(AttributeError):
        transition.relation = "after"  # type: ignore[misc]


def test_entries_preserve_all_evidence_ids():
    timeline = build_state_timeline(
        group(
            assertion(
                3,
                "maintenance",
                "2026-03-01T00:00:00",
                "2026-03-01T23:59:59",
            ),
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            ),
            assertion(
                2,
                "inactive",
                "2026-02-01T00:00:00",
                "2026-02-01T23:59:59",
            ),
        )
    )

    assert [entry.evidence_id for entry in timeline.entries] == [1, 2, 3]
