# Phase 11A — Temporal Evidence & Temporal State Foundation

**Status:** IMPLEMENTED — Phase 11A foundation
**Phase:** 11 — Temporal Intelligence
**Previous phase:** Phase 10 — Entity & Relationship Intelligence

## Objective

Establish a governed, durable temporal-evidence layer before introducing
temporal extraction, chronology inference, historical state reconstruction, or
temporal retrieval changes.

The Phase 11A boundary is intentionally narrow:

**source memory → temporal assertion → governed temporal evidence**

It does not infer dates, rewrite historical state, or alter source memories.

## Temporal dimensions

Mnemosyne must keep these dimensions distinct:

| Dimension | Meaning |
|---|---|
| Event time | When the remembered event/fact occurred |
| Recording time | When the source memory was recorded |
| Proposal time | When the memory entered collective governance |
| Validation time | When collective validation occurred |
| Derived-state time | When entity/relationship intelligence was derived or updated |
| Validity interval | The period during which a fact or relationship is asserted to hold |

Existing `TemporalSearcher` recording-time and event-date behavior remains
backward compatible. Phase 11A does not replace it.

## Temporal evidence

`temporal_evidence` stores derived assertions and provenance metadata only.

It supports:

- a subject of type `memory`, `entity`, or `relationship`;
- an optional temporal object of the same governed subject types;
- a controlled temporal relation;
- optional start/end bounds;
- explicit temporal precision;
- confidence;
- observed vs inferred evidence kind;
- extraction method;
- source memory/profile;
- collective entry reference.

The table deliberately contains **no raw memory content**.

### Initial temporal relation vocabulary

- `at`
- `before`
- `after`
- `during`
- `overlaps`
- `meets`
- `starts`
- `ends`
- `ongoing`

The vocabulary is extensible. It is not intended to become a universal
temporal ontology in this stage.

## Precision

Initial precision values:

- `unknown`
- `year`
- `month`
- `day`
- `hour`
- `minute`
- `second`

An `unknown` precision assertion cannot carry an explicit temporal bound.

This prevents an unknown or vague source statement from being represented as
an exact date.

The model intentionally does not invent an endpoint when only one boundary
is supported.

## Observed vs inferred

Temporal evidence has an explicit `evidence_kind`:

- `observed` — supported directly by source evidence;
- `inferred` — derived by a later reasoning process.

These values are never silently interchangeable.

For example, a source statement that explicitly says an event occurred before
another event may produce observed temporal evidence. A later chronology
algorithm deriving an additional ordering must produce inferred evidence.

## Governance

Every temporal evidence record remains tied to:

- collective entry;
- source memory;
- qualified source profile;
- extraction method;
- confidence.

Temporal evidence therefore inherits the project's existing governance
boundary.

Consumers must continue to enforce:

- promoted entries only;
- non-revoked entries only;
- source-memory immutability;
- provenance;
- qualified profile identity.

The temporal DAO itself stores the evidence contract; authorization remains
the responsibility of retrieval/reasoning consumers, consistent with the
existing entity and relationship architecture.

## Determinism

Temporal evidence is derived data and must be rebuildable.

Duplicate logical evidence is prevented by a deterministic uniqueness
constraint. Listing order is deterministic.

The Phase 11 rebuild pipeline must later be able to regenerate temporal
evidence from authoritative collective memories without mutating those
memories.

## Deliberate non-goals for 11A

11A does **not** implement:

- natural-language temporal extraction;
- chronology inference;
- interval algebra reasoning;
- recurrence detection;
- historical entity state reconstruction;
- historical relationship state reconstruction;
- contradiction detection;
- temporal reranking changes;
- temporal graph visualization;
- Browser temporal controls.

Those belong to subsequent Phase 11 stages and should consume this foundation
rather than bypass it.

## Next stage

The next implementation stage should be **11B — Temporal Event and State-Change
Extraction**.

That stage should read governed source-memory content through the existing
read-only gateway, produce explicit temporal assertions, and persist only
derived temporal evidence through `TemporalEvidenceDAO`.

No raw source-memory text should be copied into the temporal evidence table.
