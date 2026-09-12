# Phase 11B.3 — Explicit State-Change Extraction

**Status:** IMPLEMENTED — Phase 11B.3

## Purpose

Add a deterministic extraction layer for explicit state changes expressed in
source-memory text.

This stage extends Phase 11B temporal extraction from explicit calendar
expressions and temporal relation phrases into explicit state transitions.

## Supported forms

Examples include:

- `changed from X to Y`
- `was X, then became Y`
- `became Y`
- `was replaced by Y`

The extractor produces immutable `TemporalChangeAssertion` objects.

## Provenance

Every assertion retains:

- collective entry ID;
- source memory ID;
- source profile;
- extraction method;
- explicit previous state when present;
- explicit new state.

## Non-goals

This stage does not:

- persist assertions;
- modify `temporal_evidence`;
- resolve entities;
- infer relationships;
- infer chronology;
- decide whether a change is true;
- determine that one memory supersedes another;
- modify retrieval;
- modify the Browser;
- mutate source memory.

Ambiguous statements must not be converted into inferred state changes.

## Relationship to earlier stages

Phase 11A established governed temporal evidence storage.

Phase 11B.1 established the immutable temporal assertion contract.

Phase 11B.2 established deterministic extraction of explicit calendar and
temporal relation expressions.

Phase 11B.3 adds explicit state-change extraction while remaining outside
persistence and governance.

The next stage can connect validated temporal assertions to governed temporal
evidence without changing the extraction contract.
