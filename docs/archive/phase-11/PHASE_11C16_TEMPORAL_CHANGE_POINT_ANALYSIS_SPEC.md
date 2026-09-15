# Phase 11C.16 — Temporal Change-Point Analysis

## Purpose

Phase 11C.16 identifies meaningful state changes and stable runs within an
observed temporal trajectory.

The layer distinguishes observations from actual state changes.

For example:

```text
active → inactive → active → active
contains four observations but only two state changes.
Scope
C.16 provides:
- ordered change-point positions;
- previous and next state at each change point;
- contiguous stable runs;
- stable-run lengths;
- longest stable run;
- deterministic analysis.
A change point occurs only when adjacent observed states differ.
API
TemporalChangePoint
Represents one state change.
Fields:
- index;
- previous_state;
- next_state.
The index identifies the observation containing the new state.
TemporalStableRun
Represents a contiguous sequence of identical states.
Fields:
- start_index;
- end_index;
- state.
TemporalChangePointAnalysis
Provides:
- subject identity;
- observation count;
- change-point count;
- change points;
- stable-run count;
- stable runs;
- longest stable run.
Semantics
An unchanged observation is not a state transition.
Therefore:
A → B → A → A
has:
4 observations
2 change points
3 stable runs
The final A → A observation extends the stable run rather than creating
another change point.
Non-goals
C.16 does not:
- infer missing states;
- infer dates;
- infer temporal bounds;
- select a truthful trajectory;
- modify temporal evidence;
- persist derived analysis;
- resolve provenance conflicts;
- perform entity resolution;
- override governance.
Input boundary
The trajectory supplies subject identity and observation count.
The state sequence is supplied explicitly to the analysis function. C.16
does not reconstruct or invent the sequence from trajectory metadata.
The supplied sequence must have the same length as the trajectory's
observation_count.
Determinism
Change points are returned in observation order.
Stable runs are returned in observation order.
Grouped analysis is returned in deterministic subject-key order.
Architecture
Temporal Evidence
       ↓
Temporal State History
       ↓
Temporal History Synthesis
       ↓
Temporal Trajectory Classification
       ↓
Temporal Trajectory Comparison
       ↓
Temporal Trajectory Consensus
       ↓
Temporal Change-Point Analysis
The layer remains descriptive and compatible with Mnemosyne's
evidence-first and governance-preserving architecture.
