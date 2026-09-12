# Phase 11B.4 — Temporal Evidence Promotion

**Status:** IMPLEMENTATION

## Purpose

Connect the immutable temporal extraction contracts to the governed
`temporal_evidence` persistence boundary.

## Design

`TemporalPromotionService` accepts already-extracted assertions and delegates
persistence to the existing temporal-evidence DAO contract.

It does not:

- parse source text;
- infer chronology;
- resolve entities;
- invent temporal bounds;
- decide truth;
- alter source memories;
- modify retrieval;
- modify the Browser.

## Temporal assertions

`TemporalAssertion` fields are forwarded directly to the governed DAO.

No temporal information is added or rewritten.

## State-change assertions

`TemporalChangeAssertion` represents an explicit change in state, but the
current extraction contract deliberately does not provide temporal bounds.

Therefore promotion records the assertion as observed temporal evidence with:

- `temporal_relation="during"`;
- `precision="unknown"`;
- no invented `start_time`;
- no invented `end_time`.

The previous and new state remain properties of the extraction assertion and
are not silently converted into inferred chronology.

A later Phase 11 stage may introduce a dedicated governed representation for
state transitions if the evidence model requires it.

## Provenance

Every promoted assertion retains:

- collective entry ID;
- source memory ID;
- source profile;
- extraction method;
- evidence kind;
- confidence where available.

## Governance boundary

The service itself does not authorize an assertion or override collective
lifecycle state. The supplied DAO remains the governed persistence boundary.

## Non-goals

This stage does not implement:

- temporal interval algebra;
- temporal conflict detection;
- historical reconstruction;
- temporal retrieval;
- timeline UI;
- cross-profile inference.
