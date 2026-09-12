# Phase 11C.7 — Temporal State Transition Analysis Specification

## Purpose

Phase 11C.7 provides deterministic analysis of the transitions already
represented by the Phase 11C.6 temporal state timeline.

It identifies whether adjacent state assertions represent an actual state
change and preserves the temporal relation and certainty established by the
existing temporal reasoning layer.

## Responsibilities

The transition-analysis layer:

1. accepts an existing `TemporalStateTimeline`;
2. preserves every transition and its evidence identifiers;
3. identifies whether the adjacent states differ;
4. preserves temporal relation and certainty;
5. provides deterministic transition counts;
6. identifies evidence pairs associated with actual state changes.

## State Change Semantics

A state change is identified only when:

`from_state != to_state`

This is a structural comparison of explicit state strings.

The analysis does not determine whether either state is correct.

Repeated states are retained as unchanged transitions rather than discarded.

## Temporal Certainty

The analysis does not recalculate temporal relationships.

It preserves the relation and certainty supplied by Phase 11C.6.

Therefore:

- `before` / `definite` remains definite;
- `meets` / `definite` remains definite;
- `overlaps` / `indeterminate` remains indeterminate.

Indeterminate temporal relationships are never promoted to definite transitions.

## Evidence Preservation

Every transition retains:

- source evidence ID;
- destination evidence ID;
- source state;
- destination state;
- temporal relation;
- temporal certainty.

No evidence is merged, deleted, revoked, or rewritten.

## Determinism

Transition ordering is inherited from the temporal state timeline.

Multiple timelines are ordered by:

1. subject type;
2. subject ID.

The same input evidence therefore produces the same analysis regardless of
input iteration order.

## Non-Goals

This phase does not:

- infer causality;
- determine why a state changed;
- determine which state is authoritative;
- resolve contradictions;
- merge evidence;
- infer missing temporal bounds;
- perform NLP;
- persist analysis results;
- modify retrieval;
- modify the UI.

## Governance

Transition analysis is a read-only analytical view over governed temporal
state assertions.

No new evidence authority is created by this analysis.
