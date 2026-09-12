# Phase 11C.1 — Temporal Interval Reasoning

**Status:** IMPLEMENTATION

## Purpose

Provide a deterministic reasoning layer over already-governed temporal
evidence.

This phase does not extract temporal information from source text and does
not persist derived relationships.

## Input

The reasoning layer consumes `TemporalEvidence` records containing explicit
temporal bounds.

Evidence with:

- no start time;
- unknown precision;

is excluded from interval reasoning.

Missing endpoints are never invented.

## Relationships

The implementation supports deterministic interval relationships:

- `before`
- `after`
- `meets`
- `overlaps`
- `during`
- `contains`
- `starts`
- `started_by`
- `ends`
- `ended_by`
- `at`

## Architecture

```text
governed temporal evidence
          |
          v
    interval normalization
          |
          v
   deterministic comparison
          |
          v
 temporal relationship objects
The relationship objects are immutable and contain only evidence IDs and
the derived relationship.
Non-Goals
This phase does not:
- extract dates from text;
- infer missing dates;
- resolve entities;
- detect contradictions;
- persist derived relationships;
- alter source memories;
- modify retrieval;
- modify the browser UI;
- use an LLM;
- perform probabilistic temporal reasoning.
Important Boundary
The reasoning engine may derive a relationship only when the existing
evidence provides sufficient explicit temporal bounds.
It must never turn an unknown temporal value into a guessed chronology.
