# Phase 11C.9 — Temporal History Comparison

## Purpose

Phase 11C.9 compares two independently derived temporal state histories for
the same subject.

The comparison is analytical and read-only. It identifies positional state
agreement, state divergence, and observations that exist only on one side.

It does not determine which history is correct.

## Inputs

The comparison accepts two `TemporalStateHistory` instances.

Both histories must describe the same:

- `subject_type`
- `subject_id`

Otherwise comparison fails with `ValueError`.

## Outputs

`TemporalHistoryComparison` contains:

- subject identity
- left evidence IDs
- right evidence IDs
- matching state observations
- divergent state observations
- left-only observations
- right-only observations
- temporal uncertainty
- comparison count

### Matching observations

A matching observation has the same state at the same positional index.

The evidence IDs from both histories are retained:

```text
(left_evidence_id, right_evidence_id, state)
Divergent observations
A divergent observation contains the state from each side:
(left_evidence_id, right_evidence_id, left_state, right_state)
If one history has no corresponding observation, its evidence ID and state are
represented as None.
Ordering
Observations are compared positionally according to the existing history
ordering.
No chronology is reconstructed.
Additional observations on either side are retained in their original order.
Multiple history-pair comparisons are deterministically ordered by:
1. subject type
2. subject ID
Temporal uncertainty
Temporal uncertainty is preserved from either input history.
If either history reports an indeterminate transition, the resulting comparison
reports temporal_uncertainty=True.
Uncertainty is never converted into contradiction.
Immutability
The comparison result is an immutable frozen dataclass.
Input histories are never modified.
Non-goals
This phase does not:
- select a correct history
- reconcile conflicting states
- resolve contradictions
- infer chronology
- infer missing observations
- merge histories
- modify temporal evidence
- persist comparison results
- alter retrieval
- alter UI behavior
- establish causality
Governance
The comparison is a derived analytical view over existing governed temporal
evidence.
It introduces no new persistence or governance decisions.
Determinism
For identical input histories, comparison output is identical.
No external state, timestamps, randomness, or database access is used.
Relationship to previous phases
11A  Temporal evidence foundation
 ↓
11B  Temporal extraction and promotion
 ↓
11C.1 Interval reasoning
 ↓
11C.2 Precision-aware reasoning
 ↓
11C.3 Consistency analysis
 ↓
11C.4 Semantic contradiction detection
 ↓
11C.5 Evidence aggregation
 ↓
11C.6 State timelines
 ↓
11C.7 State transition analysis
 ↓
11C.8 State history
 ↓
11C.9 History comparison
