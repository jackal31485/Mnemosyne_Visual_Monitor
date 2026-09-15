# Phase 11C.11 — Temporal History Consensus Analysis

## Purpose

Phase 11C.11 analyzes multiple independent temporal state histories for the
same subject.

It identifies positional consensus, disagreement, incomplete observations,
and temporal uncertainty.

Consensus is descriptive only. It is not a truth-selection mechanism.

## Inputs

One or more `TemporalStateHistory` instances.

All histories must describe the same:

- `subject_type`
- `subject_id`

An empty collection is invalid.

## Positional analysis

Histories are compared by observation position.

For each position:

- observations present in every history are complete;
- a single distinct state represents consensus;
- multiple distinct states represent disagreement;
- observations missing from one or more histories are incomplete.

No chronological reconstruction is performed.

## Consensus

`TemporalConsensusPosition` records:

- positional index
- distinct states observed
- number of histories supporting the most common state
- total history count

The most-supported state is not promoted to truth.

All observed states remain represented.

## Incomplete observations

An incomplete position occurs when fewer than all supplied histories contain
an observation at that position.

Incomplete positions are reported separately from disagreement.

An incomplete position may still have unanimous agreement among the histories
that contain an observation.

## Ratios

For non-empty comparisons:

```text
consensus_ratio =
    consensus_position_count / comparison_count

disagreement_ratio =
    disagreement_position_count / comparison_count
Empty positional comparisons use zero for both ratios.
Temporal uncertainty
Temporal uncertainty is preserved if any input history reports an indeterminate
transition.
Uncertainty does not become disagreement or contradiction by itself.
Multiple subject groups
analyze_history_consensus_groups() accepts histories for multiple subjects.
Results are grouped by:
1. subject type
2. subject ID
and returned deterministically in that order.
Immutability
All result objects are frozen dataclasses.
Input histories are never modified.
Governance
This phase is a read-only derived analysis over existing temporal evidence.
No evidence is created, modified, revoked, or persisted.
Non-goals
This phase does not:
- choose the correct state
- resolve contradictions
- perform voting-based truth selection
- merge histories
- infer missing states
- infer chronology
- infer causality
- alter temporal evidence
- modify retrieval
- modify UI
- perform learning
- make governance decisions
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
 ↓
11C.11 History consensus analysis
