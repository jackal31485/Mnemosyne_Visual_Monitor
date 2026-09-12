# Phase 11C.8 — Temporal State History Specification

## Purpose

Phase 11C.8 provides a deterministic summary of the temporal state history
represented by a Phase 11C.6 timeline and analyzed by Phase 11C.7.

It provides a compact analytical view without replacing or modifying the
underlying temporal evidence.

## Responsibilities

The history layer exposes:

- subject identity;
- ordered evidence IDs;
- ordered observed states;
- initial state;
- final state;
- observation count;
- transition count;
- changed transition count;
- unchanged transition count;
- definite transition count;
- indeterminate transition count;
- distinct state count;
- whether any state change exists;
- whether temporal uncertainty exists.

## Semantics

The initial state is the state of the earliest timeline entry.

The final state is the state of the latest timeline entry.

A state change occurs only when adjacent explicit state strings differ.

Repeated states remain part of the history and are counted as unchanged
transitions.

Temporal certainty is inherited from the existing transition analysis.

## Evidence Preservation

Every timeline evidence identifier is retained in order.

No evidence is merged, removed, rewritten, or revoked.

The history is a derived summary rather than an authoritative replacement
for temporal evidence.

## Determinism

History ordering is inherited from the temporal state timeline.

Multiple subjects are ordered by:

1. subject type;
2. subject ID.

No model-based or probabilistic ordering is introduced.

## Non-Goals

This phase does not:

- determine the correct state;
- resolve contradictions;
- infer causality;
- infer missing temporal bounds;
- infer states not explicitly represented;
- merge evidence;
- persist history;
- modify retrieval;
- modify the UI.

## Governance

The history summary is read-only analytical output over already governed
temporal assertions.

Evidence provenance and temporal certainty remain unchanged.
