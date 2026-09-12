# Phase 11C.15 — Temporal Trajectory Consensus

## Purpose

Phase 11C.15 adds deterministic descriptive consensus analysis across
temporal trajectory classifications for the same subject.

It describes whether multiple trajectory classifications agree or
disagree without selecting a truthful or authoritative trajectory.

## Scope

C.15 provides:

- trajectory classification support counts;
- trajectory count;
- distinct trajectory-kind count;
- consensus and disagreement status;
- descriptive support ratios;
- temporal-uncertainty propagation;
- incomplete-history propagation;
- deterministic grouped analysis.

## Semantics

A single trajectory kind across all supplied trajectories is consensus.

Multiple trajectory kinds constitute disagreement.

A majority trajectory kind is reported descriptively but is **not**
promoted to truth or authority.

For example:

```text
REVERSAL
REVERSAL
TRANSITION
produces:
REVERSAL: 2
TRANSITION: 1
disagreement: true
consensus: false
The majority classification remains descriptive evidence only.
Non-goals
C.15 does not:
- select a truthful trajectory;
- rank evidence sources;
- resolve provenance conflicts;
- infer missing states;
- modify temporal evidence;
- persist data;
- perform entity resolution;
- override governance;
- replace temporal state consensus.
Determinism
Trajectory kinds preserve first-seen order within a consensus result.
Grouped results are returned in deterministic subject-key order.
Architecture
Temporal Evidence
    ↓
Temporal State History
    ↓
History Comparison / Consensus / Synthesis
    ↓
Temporal Trajectory
    ↓
Temporal Trajectory Comparison
    ↓
Temporal Trajectory Consensus
The layer remains compatible with Mnemosyne's evidence-first,
provenance-preserving architecture.
