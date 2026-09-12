# Phase 11C.10 — Temporal History Divergence Analysis

## Purpose

Phase 11C.10 characterizes the differences identified by Phase 11C.9.

It converts a `TemporalHistoryComparison` into a compact, immutable analytical
summary describing agreement, divergence, asymmetric observations, and
temporal uncertainty.

It does not resolve disagreements.

## Inputs

The primary input is a `TemporalHistoryComparison`.

A convenience function also accepts two `TemporalStateHistory` instances and
performs comparison followed by divergence analysis.

## Outputs

`TemporalHistoryDivergence` contains:

- subject identity
- comparison count
- shared state count
- divergent state count
- left-only observation count
- right-only observation count
- first divergence index
- agreement ratio
- divergence ratio
- divergence flag
- asymmetric-observation flag
- temporal-uncertainty flag

## Agreement

Agreement ratio is:

```text
shared_state_count / comparison_count
for non-empty comparisons.
Empty comparisons have an agreement ratio of 0.0.
Divergence
Divergence ratio is:
divergent_state_count / comparison_count
for non-empty comparisons.
Empty comparisons have a divergence ratio of 0.0.
A divergence includes:
- different states at the same position
- an observation present only on the left
- an observation present only on the right
First divergence
first_divergence_index identifies the earliest positional observation at
which the two histories diverge.
It is None when the histories fully agree.
The index is positional, zero-based, and does not represent a reconstructed
chronological timestamp.
Asymmetric observations
An asymmetric comparison occurs when one history contains observations beyond
the length of the other history.
These observations are preserved and counted separately.
Temporal uncertainty
Temporal uncertainty is inherited from the input comparison.
If either source history contains an indeterminate transition, the resulting
analysis reports temporal uncertainty.
Temporal uncertainty does not itself constitute state divergence.
Convenience operation
compare_and_analyze_history_divergence() performs:
TemporalStateHistory
        ↓
compare_state_histories()
        ↓
TemporalHistoryComparison
        ↓
analyze_history_divergence()
        ↓
TemporalHistoryDivergence
Determinism
Multiple divergence analyses are ordered by:
1. subject type
2. subject ID
No randomness, external state, or database access is involved.
Immutability
The result is a frozen dataclass.
Input histories and comparisons are never modified.
Non-goals
This phase does not:
- select a correct history
- reconcile conflicting states
- resolve contradictions
- infer missing observations
- infer chronology
- infer causality
- merge histories
- modify temporal evidence
- persist analytical results
- alter retrieval
- alter UI behavior
- perform learning
- make governance decisions
Governance
This phase is a read-only analytical layer over already governed temporal
evidence.
No new evidence is created.
Relationship to previous phases
11A   Temporal evidence foundation
 ↓
11B   Temporal extraction and promotion
 ↓
11C.1 Interval reasoning
 ↓
11C.2 Precision-aware reasoning
 ↓
11C.3 Temporal consistency
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
 ↓
11C.10 History divergence analysis
