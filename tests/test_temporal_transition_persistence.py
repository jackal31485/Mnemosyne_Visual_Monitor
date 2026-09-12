from __future__ import annotations

from src.domain.temporal_change_points import TemporalStableRun
from src.domain.temporal_transition_persistence import analyze_transition_persistence


def test_transition_persistence_preserves_runs():
    result = analyze_transition_persistence(
        "person", "subject-1",
        [TemporalStableRun(0, 1, "active"), TemporalStableRun(2, 4, "inactive")],
    )
    assert result.run_count == 2
    assert result.longest_persistence == 3
    assert result.repeated_state_run_count == 2
    assert result.has_persistence


def test_empty_runs_are_descriptive_and_safe():
    result = analyze_transition_persistence("person", "subject-1", [])
    assert result.run_count == 0
    assert result.longest_persistence == 0
    assert not result.has_persistence
