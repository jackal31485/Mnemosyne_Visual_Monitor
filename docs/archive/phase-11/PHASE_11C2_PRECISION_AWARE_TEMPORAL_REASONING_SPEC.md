# Phase 11C.2 — Precision-Aware Temporal Reasoning

**Status:** IMPLEMENTATION

## Purpose

Extend temporal reasoning so explicit temporal precision is treated as
semantic information rather than discarded during interval comparison.

## Precision Semantics

Supported precision levels:

- `year`
- `month`
- `day`
- `hour`
- `minute`
- `second`

An assertion such as:

```text
2024
with year precision represents the semantic interval:
2024-01-01 00:00:00
through
2024-12-31 23:59:59.999999
It does not claim that the event occurred on January 1.
Likewise, month and day precision expand only to the boundaries of their
declared precision.
Certainty
Temporal comparison returns both:
1. a relationship;
2. a certainty classification.
definite means the relationship follows from the semantic bounds.
indeterminate means the available precision does not justify a stronger
chronological claim.
Important Boundary
The semantic interval is a reasoning representation. It does not modify
the original evidence and does not invent an event timestamp.
Original precision and provenance remain unchanged.
Unknown Precision
Evidence with unknown precision is excluded from precision-aware
comparison because there is insufficient temporal information.
Non-Goals
This phase does not:
- extract temporal information;
- infer missing dates;
- alter governed evidence;
- detect contradictions;
- resolve entities;
- persist derived relationships;
- modify retrieval;
- modify the browser UI;
- use an LLM.
  MD
