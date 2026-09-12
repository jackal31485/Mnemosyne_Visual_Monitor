# Phase 11C.6 — Temporal State Timeline Specification

## Purpose

Phase 11C.6 provides a deterministic domain representation of the temporal
sequence of state assertions for a single subject.

It builds on Phase 11C.5 evidence aggregation and Phase 11C.2 precision-aware
temporal reasoning.

## Responsibilities

The timeline layer:

1. accepts a governed `TemporalEvidenceGroup`;
2. orders state assertions chronologically;
3. preserves every source evidence identifier;
4. represents each assertion as a timeline entry;
5. compares adjacent entries using existing precision-aware reasoning;
6. represents transitions with their temporal relation and certainty;
7. remains deterministic and immutable.

## Transition Semantics

A transition does not assert causality.

For adjacent assertions, the transition records the relationship already
established by the precision-aware temporal reasoning layer.

Examples include:

- `before` / `definite`
- `after` / `definite`
- `meets` / `definite`
- `overlaps` / `indeterminate`
- `at` / `definite`

An indeterminate relationship must remain indeterminate.

## Evidence Preservation

Timeline construction never merges or deletes evidence.

Every input assertion remains represented by its evidence identifier.

The timeline is therefore a derived analytical view rather than a replacement
for the underlying evidence.

## Determinism

Ordering is:

1. temporal start;
2. temporal end;
3. evidence ID.

Multiple subjects are ordered by:

1. subject type;
2. subject ID.

The same evidence therefore produces the same timeline regardless of input
iteration order.

## Non-Goals

This phase does not:

- persist timelines;
- modify temporal evidence;
- revoke evidence;
- resolve contradictory states;
- infer missing dates;
- infer causality;
- infer state transitions from natural language;
- merge assertions;
- rank evidence;
- modify retrieval;
- modify the UI.

## Governance

The timeline is a read-only analytical representation over already governed
temporal state assertions.

Existing provenance, evidence IDs, subject identity, precision and certainty
remain intact.

No new authority is created by timeline construction.
