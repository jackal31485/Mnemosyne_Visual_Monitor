# Phase 11B — Temporal Event & State-Change Extraction

**Status:** IN PROGRESS — 11B.1 EXTRACTION CONTRACT
**Phase:** 11 — Temporal Intelligence
**Previous stage:** Phase 11A — Temporal Evidence & Temporal State Foundation

## Objective

Introduce a typed temporal-assertion contract that separates temporal
extraction from temporal-evidence persistence.

Phase 11B begins with the contract only. Actual natural-language extraction
is introduced in later 11B stages.

The boundary is:

**governed source memory → temporal extractor → temporal assertion → governed temporal evidence**

The `TemporalAssertion` value object represents a temporal claim produced by
an extraction or reasoning component. It does not access SQLite, read source
memories, or perform extraction itself.

## 11B.1 contract

`TemporalAssertion` must contain sufficient information for a later consumer
to persist the assertion through `TemporalEvidenceDAO`.

Required provenance:

- collective entry ID;
- source memory ID;
- source profile;
- extraction method.

Required temporal semantics:

- subject type and ID;
- temporal relation;
- precision.

Optional temporal semantics:

- object type and ID;
- start bound;
- end bound;
- confidence.

Evidence kind is explicit and defaults to `observed`.

## Supported vocabulary

The contract uses the Phase 11A vocabulary:

### Subject/object types

- `memory`
- `entity`
- `relationship`

### Temporal relations

- `at`
- `before`
- `after`
- `during`
- `overlaps`
- `meets`
- `starts`
- `ends`
- `ongoing`

### Precision

- `unknown`
- `year`
- `month`
- `day`
- `hour`
- `minute`
- `second`

### Evidence kind

- `observed`
- `inferred`

11B extraction stages initially produce `observed` assertions when the
temporal information is directly supported by the source memory.

## Validation

The assertion contract rejects:

- unsupported subject/object types;
- missing subject IDs;
- unsupported temporal relations;
- unsupported precision values;
- unsupported evidence kinds;
- missing extraction method;
- missing source memory ID;
- missing source profile;
- non-positive collective entry IDs;
- confidence outside the inclusive range 0.0–1.0;
- only one half of an object reference;
- `unknown` precision with an explicit temporal bound;
- an end bound earlier than a start bound.

Object type and object ID must always be supplied together.

Temporal bounds remain optional. A single supported boundary must not cause
the contract to invent the missing boundary.

## Immutability

`TemporalAssertion` is an immutable value object.

Extraction stages should construct assertions and pass them to persistence
code. They must not mutate an assertion after creation.

## Persistence boundary

`TemporalAssertion` contains no database connection, SQL, DAO reference, or
raw source-memory content.

Persistence remains the responsibility of:

`TemporalEvidenceDAO`

The DAO remains the authoritative Phase 11A storage boundary.

## Deliberate non-goals for 11B.1

11B.1 does not implement:

- natural-language date extraction;
- temporal phrase parsing;
- relative-date resolution;
- chronology inference;
- state reconstruction;
- contradiction detection;
- temporal reranking;
- retrieval changes;
- source-memory mutation;
- collective-governance decisions;
- Browser/UI changes.

Those capabilities must consume this contract rather than bypass it.

## Next stage

**11B.2 — Explicit Temporal Extraction**

11B.2 should introduce deterministic extraction of explicitly stated temporal
information and produce `TemporalAssertion` objects without directly
persisting them.
