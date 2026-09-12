# Phase 11 — Temporal Intelligence

**Status:** PLANNED
**Previous phase:** Phase 10 — Entity & Relationship Intelligence
**Next phase:** TBD

## Purpose

Extend Mnemosyne's entity and relationship intelligence with temporal
understanding.

The objective is to move from:

**Memory → Retrieval → Entities → Relationships**

toward:

**Memory → Retrieval → Entities → Relationships → Temporal Understanding**

## Initial scope

Phase 11 should investigate:

- temporal evidence attached to memories, entities, and relationships
- event and state-change extraction
- chronology and temporal ordering
- valid-from / valid-to semantics where evidence supports them
- temporal confidence
- historical entity state
- relationship state across time
- time-aware retrieval and reranking
- temporal graph projection
- contradiction handling across different time periods

## Governance constraints

Phase 11 must preserve:

- source-memory immutability
- provenance
- promotion/revocation enforcement
- qualified profile identity
- explicit evidence
- no fabricated dates
- no silent historical rewriting
- deterministic rebuildability
- separation between observed evidence and inferred temporal state

## Implementation principle

Temporal intelligence must be introduced incrementally and must remain
compatible with the Phase 8 hybrid retrieval architecture and the Phase 10
entity/relationship layer.

Detailed implementation work begins only after a Phase 11 specification
and audit plan are approved.
