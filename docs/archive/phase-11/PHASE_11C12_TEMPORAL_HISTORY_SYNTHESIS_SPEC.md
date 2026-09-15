# Phase 11C.12 — Temporal History Synthesis

## Purpose

C.12 provides a deterministic descriptive synthesis of multiple temporal
histories for the same subject.

It combines the information established by:

- C.8 temporal state history
- C.9 history comparison
- C.10 history divergence
- C.11 history consensus

The result is a higher-level summary while preserving uncertainty and
disagreement.

## Synthesis dimensions

A synthesis records:

- subject identity
- number of histories
- total observations
- distinct observed states
- initial states
- final states
- positions where histories fully agree
- positions where histories diverge
- positions where histories are incomplete
- consensus ratio
- disagreement ratio
- observation coverage
- temporal uncertainty

## Consensus semantics

A state is included in `consensus_states` only when every supplied history
contains that same state at the corresponding position.

A majority state is not promoted to truth.

Therefore:

> consensus describes agreement among histories; it does not establish
> objective truth.

## Incomplete histories

A position missing from one or more histories is classified as incomplete,
not as disagreement.

This distinction is preserved because absence of an observation is not
evidence of a contradictory observation.

## Uncertainty

Temporal uncertainty from the underlying histories is propagated unchanged.

Synthesis also exposes `is_uncertain`, which is true when:

- temporal uncertainty exists;
- histories diverge; or
- histories are incomplete.

## Stability

`is_stable` is true only when:

- there is no divergence;
- there are no incomplete positions; and
- every compared position has consensus.

This is descriptive stability, not truth validation.

## Determinism

For identical inputs, synthesis produces identical output.

Grouped synthesis sorts subjects by:

1. subject type
2. subject ID

No timestamps, database state, randomness, or iteration-order-dependent
decisions are introduced.

## Provenance

C.12 does not discard the underlying evidence IDs. The source
`TemporalStateHistory` objects remain the authoritative provenance chain.

## Non-goals

C.12 does not:

- select a canonical truth;
- resolve contradictions;
- mutate evidence;
- create memories;
- write to collective.db;
- revoke evidence;
- perform entity resolution;
- perform retrieval;
- perform temporal extraction;
- update Hermes profiles;
- modify the UI.

## Architectural role

```text
Temporal Evidence
       |
       v
State Timeline
       |
       v
State History
       |
       +--> History Comparison
       |
       +--> History Divergence
       |
       +--> History Consensus
       |
       v
History Synthesis
C.12 remains an analysis layer. Any future learning or memory-update layer
must explicitly consume this analysis and retain its provenance.
