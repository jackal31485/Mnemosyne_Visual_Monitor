from datetime import datetime

import pytest

from src.domain.temporal_aggregation import TemporalEvidenceGroup
from src.domain.temporal_contradiction import TemporalStateAssertion
from src.domain.temporal_precision import PrecisionInterval
from src.domain.temporal_state_timeline import build_state_timeline
from src.domain.temporal_transition_analysis import (
    TemporalTransitionAnalysis,
    TemporalTransitionFinding,
    analyze_state_timeline,
    analyze_state_timelines,
)


def assertion(
    evidence_id: int,
    state: str,
    start: str,
    end: str,
    *,
    subject_id: str = "device-1",
) -> TemporalStateAssertion:
    return TemporalStateAssertion(
        evidence_id=evidence_id,
        subject_type="entity",
        subject_id=subject_id,
        state=state,
        interval=PrecisionInterval(
            evidence_id=evidence_id,
            start=datetime.fromisoformat(start),
            end=datetime.fromisoformat(end),
            precision="day",
        ),
    )


def timeline(*assertions_: TemporalStateAssertion):
    group = TemporalEvidenceGroup(
        subject_type="entity",
        subject_id=assertions_[0].subject_id,
        assertions=tuple(assertions_),
    )
    return build_state_timeline(group)


def test_empty_timeline_has_no_findings():
    result = analyze_state_timeline(
        timeline(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            )
        )
    )

    assert result.findings == ()
    assert result.transition_count == 0


def test_changed_state_is_identified():
    result = analyze_state_timeline(
        timeline(
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

    assert result.transition_count == 1
    assert result.changed_transition_count == 1
    assert result.unchanged_transition_count == 0


def test_same_state_is_not_a_state_change():
    result = analyze_state_timeline(
        timeline(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            ),
            assertion(
                2,
                "active",
                "2026-01-02T00:00:00",
                "2026-01-02T23:59:59",
            ),
        )
    )

    assert result.transition_count == 1
    assert result.changed_transition_count == 0
    assert result.unchanged_transition_count == 1


def test_transition_relation_is_preserved():
    result = analyze_state_timeline(
        timeline(
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

    finding = result.findings[0]

    assert finding.relation == "before"
    assert finding.certainty == "definite"


def test_indeterminate_transition_remains_indeterminate():
    result = analyze_state_timeline(
        timeline(
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

    finding = result.findings[0]

    assert finding.relation == "overlaps"
    assert finding.certainty == "indeterminate"
    assert finding.state_changed is True
    assert result.indeterminate_transition_count == 1


def test_evidence_ids_are_preserved():
    result = analyze_state_timeline(
        timeline(
            assertion(
                10,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            ),
            assertion(
                20,
                "inactive",
                "2026-01-02T00:00:00",
                "2026-01-02T23:59:59",
            ),
        )
    )

    finding = result.findings[0]

    assert finding.from_evidence_id == 10
    assert finding.to_evidence_id == 20
    assert result.changed_evidence_ids == ((10, 20),)


def test_multiple_transitions_are_preserved_in_order():
    result = analyze_state_timeline(
        timeline(
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

    assert result.transition_count == 2
    assert result.changed_transition_count == 2
    assert [
        (finding.from_evidence_id, finding.to_evidence_id)
        for finding in result.findings
    ] == [(1, 2), (2, 3)]


def test_mixed_changed_and_unchanged_transitions():
    result = analyze_state_timeline(
        timeline(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            ),
            assertion(
                2,
                "active",
                "2026-01-02T00:00:00",
                "2026-01-02T23:59:59",
            ),
            assertion(
                3,
                "inactive",
                "2026-01-03T00:00:00",
                "2026-01-03T23:59:59",
            ),
        )
    )

    assert result.transition_count == 2
    assert result.changed_transition_count == 1
    assert result.unchanged_transition_count == 1


def test_definite_and_indeterminate_counts_are_separate():
    result = analyze_state_timeline(
        timeline(
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
                "2026-01-02T12:00:00",
                "2026-01-03T23:59:59",
            ),
        )
    )

    assert result.definite_transition_count == 1
    assert result.indeterminate_transition_count == 1


def test_changed_evidence_ids_exclude_unchanged_states():
    result = analyze_state_timeline(
        timeline(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            ),
            assertion(
                2,
                "active",
                "2026-01-02T00:00:00",
                "2026-01-02T23:59:59",
            ),
            assertion(
                3,
                "inactive",
                "2026-01-03T00:00:00",
                "2026-01-03T23:59:59",
            ),
        )
    )

    assert result.changed_evidence_ids == ((2, 3),)


def test_multiple_subjects_are_sorted_deterministically():
    timeline_b = timeline(
        assertion(
            2,
            "inactive",
            "2026-01-01T00:00:00",
            "2026-01-01T23:59:59",
            subject_id="device-b",
        )
    )
    timeline_a = timeline(
        assertion(
            1,
            "active",
            "2026-01-01T00:00:00",
            "2026-01-01T23:59:59",
            subject_id="device-a",
        )
    )

    results = analyze_state_timelines([timeline_b, timeline_a])

    assert [result.subject_id for result in results] == [
        "device-a",
        "device-b",
    ]


def test_empty_collection_is_supported():
    assert analyze_state_timelines([]) == ()


def test_invalid_timeline_is_rejected():
    with pytest.raises(TypeError):
        analyze_state_timeline(object())  # type: ignore[arg-type]


def test_invalid_collection_member_is_rejected():
    with pytest.raises(TypeError):
        analyze_state_timelines([object()])  # type: ignore[list-item]


def test_finding_is_immutable():
    finding = TemporalTransitionFinding(
        from_evidence_id=1,
        to_evidence_id=2,
        from_state="active",
        to_state="inactive",
        relation="before",
        certainty="definite",
        state_changed=True,
    )

    with pytest.raises(AttributeError):
        finding.state_changed = False  # type: ignore[misc]


def test_analysis_is_immutable():
    result = analyze_state_timeline(
        timeline(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            )
        )
    )

    with pytest.raises(AttributeError):
        result.subject_id = "other"  # type: ignore[misc]


def test_analysis_preserves_subject_identity():
    result = analyze_state_timeline(
        timeline(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            )
        )
    )

    assert result.subject_type == "entity"
    assert result.subject_id == "device-1"
