# Phase 11C.14 — Temporal Trajectory Comparison

## Purpose

Phase 11C.14 adds deterministic comparison of temporal trajectory
classifications produced by Phase 11C.13.

The comparison layer describes whether two trajectories agree or differ
without selecting either trajectory as authoritative.

## Scope

C.14 compares:

- trajectory classification;
- observation counts;
- distinct-state counts;
- transition counts;
- reversal counts;
- oscillation counts;
- temporal uncertainty;
- incomplete-history state;
- temporal divergence flags.

The comparison is descriptive only.

## Non-goals

C.14 does not:

- select a truthful trajectory;
- rank sources;
- infer missing states;
- modify temporal evidence;
- persist new temporal evidence;
- perform entity resolution;
- override provenance or governance;
- infer causality.

## Model

`TemporalTrajectoryComparison` contains both sides of the comparison and
explicit divergence flags for each compared dimension.

The following are distinct concepts:

- **kind divergence** — the trajectories receive different classifications;
- **metric divergence** — their observed structural counts differ;
- **uncertainty divergence** — only one trajectory carries temporal
  uncertainty;
- **incompleteness divergence** — only one trajectory is incomplete;
- **divergence-flag difference** — only one trajectory was itself
  classified as divergent.

Two trajectories can therefore have the same kind while still differing
in their underlying structural metrics.

## Subject safety

Trajectories must describe the same `(subject_type, subject_id)`.

Comparing different subjects is rejected rather than silently producing a
meaningless comparison.

## Determinism

Group comparisons are processed in sorted subject-key order.

No probabilistic ranking or source preference is introduced.

## Relationship to earlier phases

C.14 consumes the output of C.13:

```text
Temporal Evidence
    ↓
Temporal State History
    ↓
History Comparison / Consensus / Synthesis
    ↓
Temporal Trajectory
    ↓
Temporal Trajectory Comparison
The layer remains compatible with Mnemosyne's evidence-first and
governance-preserving architecture.
