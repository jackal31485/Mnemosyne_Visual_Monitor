from datetime import datetime

import pytest

from src.domain.temporal_aggregation import TemporalEvidenceGroup
from src.domain.temporal_contradiction import TemporalStateAssertion
from src.domain.temporal_precision import PrecisionInterval
from src.domain.temporal_state_history import (
    TemporalStateHistory,
    summarize_state_histories,
    summarize_state_history,
)
from src.domain.temporal_state_timeline import build_state_timeline


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
    return build_state_timeline(
        TemporalEvidenceGroup(
            subject_type="entity",
            subject_id=assertions_[0].subject_id,
            assertions=tuple(assertions_),
        )
    )


def test_single_observation_history():
    history = summarize_state_history(
        timeline(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            )
        )
    )

    assert history.observation_count == 1
    assert history.transition_count == 0
    assert history.initial_state == "active"
    assert history.final_state == "active"
    assert history.states == ("active",)


def test_history_preserves_evidence_ids():
    history = summarize_state_history(
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

    assert history.evidence_ids == (1, 2)


def test_initial_and_final_states():
    history = summarize_state_history(
        timeline(
            assertion(
                1,
                "active",
                "2026-01-01T00:00:00",
                "2026-01-01T23:59:59",
            ),
            assertion(
                2,
                "maintenance",
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

    assert history.initial_state == "active"
    assert history.final_state == "inactive"


def test_distinct_state_count():
    history = summarize_state_history(
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

    assert history.distinct_state_count == 2


def test_state_change_is_detected():
    history = summarize_state_history(
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

    assert history.has_state_change is True
    assert history.changed_transition_count == 1


def test_repeated_state_is_counted_as_unchanged_transition():
    history = summarize_state_history(
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

    assert history.changed_transition_count == 0
    assert history.unchanged_transition_count == 1


def test_definite_transition_count():
    history = summarize_state_history(
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

    assert history.definite_transition_count == 1
    assert history.indeterminate_transition_count == 0


def test_indeterminate_transition_is_preserved():
    history = summarize_state_history(
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

    assert history.indeterminate_transition_count == 1
    assert history.has_temporal_uncertainty is True


def test_no_temporal_uncertainty_for_definite_history():
    history = summarize_state_history(
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

    assert history.has_temporal_uncertainty is False


def test_multiple_observations_have_n_minus_one_transitions():
    history = summarize_state_history(
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

    assert history.observation_count == 3
    assert history.transition_count == 2


def test_empty_collection_of_timelines():
    assert summarize_state_histories([]) == ()


def test_multiple_histories_are_sorted_deterministically():
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

    histories = summarize_state_histories([timeline_b, timeline_a])

    assert [history.subject_id for history in histories] == [
        "device-a",
        "device-b",
    ]


def test_invalid_timeline_is_rejected():
    with pytest.raises(TypeError):
        summarize_state_history(object())  # type: ignore[arg-type]


def test_invalid_collection_member_is_rejected():
    with pytest.raises(TypeError):
        summarize_state_histories([object()])  # type: ignore[list-item]


def test_history_is_immutable():
    history = summarize_state_history(
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
        history.final_state = "inactive"  # type: ignore[misc]


def test_empty_history_validation():
    history = TemporalStateHistory(
        subject_type="entity",
        subject_id="device-1",
        evidence_ids=(),
        states=(),
        initial_state=None,
        final_state=None,
        observation_count=0,
        transition_count=0,
        changed_transition_count=0,
        unchanged_transition_count=0,
        definite_transition_count=0,
        indeterminate_transition_count=0,
    )

    assert history.distinct_state_count == 0
    assert history.has_state_change is False
    assert history.has_temporal_uncertainty is False
