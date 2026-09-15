# Phase 10 — Entity & Relationship Intelligence

**Status:** COMPLETE — 2026-09-11
**Completed:** 2026-09-11
**Previous phase:** Phase 9 — Browser-Facing Hybrid Retrieval Integration
**Next phase:** Phase 11 — Temporal Intelligence

## Objective

Build a governed entity and relationship intelligence layer on top of
Mnemosyne's existing collective memory, graph, provenance, and hybrid
retrieval infrastructure.

Phase 10 teaches Mnemosyne what memories are about and how the things within
those memories relate to one another.

The intended progression is:

**Memory → Retrieval → Entities → Relationships → Understanding**

Phase 10 must preserve existing profile isolation, provenance, lifecycle,
promotion, revocation, retrieval authorization, and source-memory boundaries.


## 10A — Entity Data Model

Establish the canonical representation for entities.

A conceptual entity includes:

- entity ID
- canonical name
- entity type
- aliases
- description
- confidence
- lifecycle state
- created timestamp
- updated timestamp

The entity itself must not be treated as unquestionable ground truth.

Entity evidence should retain:

- entity ID
- collective entry ID
- source memory ID
- source profile
- original mention
- confidence
- extraction timestamp

This allows Mnemosyne to answer why it believes mentions refer to an entity
without losing the underlying evidence.

### Initial entity types

Start with:

- Person
- Agent/Profile
- Project
- File
- Technology
- Organization
- Location
- Concept
- Other

The type system must remain extensible.


## 10B — Entity Extraction

Build the first extraction pipeline from existing collective memories.

```text
Collective Memory
       |
       v
Entity Extraction
       |
       +-- entity mentions
       +-- entity types
       +-- confidence
       |
       v
Evidence Records

The extraction layer should be local and replaceable.

Potential strategies include:

deterministic/rule-based extraction
local NLP tooling
local LLM extraction
hybrid extraction

The first implementation should favor free, local, deterministic or
reproducible behavior where practical.

Phase 10 must not hard-wire Mnemosyne to a single external model or provider.

## 10C — Entity Evidence & Provenance

Every extracted entity must retain a traceable relationship to its source
evidence.

Evidence should preserve:

source profile identity
source memory identity
collective entry identity
original mention
extraction method
confidence
extraction timestamp

Entity intelligence is derived data and must remain auditable.

The system must distinguish an entity from the evidence supporting that entity.

## 10D — Entity Resolution

Build a governed entity-resolution pipeline.

Different mentions may refer to the same entity:

Mnemosyne Visual Monitor
Mnemosyne
Visual Monitor
the Mnemosyne project

The resolution process should be:

Mention
   |
   v
Candidate Entities
   |
   v
Similarity / Rules / Context
   |
   v
Resolution Decision
   |
   +-- same entity
   +-- new entity
   +-- ambiguous

Resolution should consider:

normalized names
aliases
entity type
contextual similarity
existing relationships
source evidence
profile identity where applicable
Governance rule

No silent entity merging.

If confidence is insufficient, ambiguous is a valid outcome.

Resolution records should retain:

original mention
proposed canonical entity
confidence
evidence
resolution method
decision/lifecycle state

Profile identity must not be flattened during entity resolution.

For example, a qualified identity such as:

agent-id:athena

must remain distinguishable from an unrelated entity merely named Athena.

## 10E — Relationship Model

Introduce a governed relationship representation.

A conceptual relationship includes:

relationship ID
subject entity ID
predicate
object entity ID
confidence
lifecycle/status
created timestamp
updated timestamp

Relationship evidence should retain:

relationship ID
collective entry ID
source memory ID
source profile
evidence text or reference
confidence
extraction timestamp

Example:

Mnemosyne Visual Monitor
        |
        +-- uses --------> FastAPI
        +-- contains ----> Hybrid Retrieval
        +-- developed_by -> Hermes
        +-- has_profile -> Athena

Relationships must remain traceable to evidence.

## 10F — Relationship Extraction

Implement relationship extraction and classification.

Initial relationship vocabulary may include:

uses
contains
part_of
depends_on
created_by
maintained_by
associated_with
related_to
derived_from
has_profile
mentions

The ontology should remain extensible.

Phase 10 should not attempt to create a perfect universal ontology.

Explicit vs inferred relationships

Mnemosyne must distinguish explicit evidence from inference.

Explicit:

Mnemosyne uses FastAPI.

Inferred:

Mnemosyne probably uses FastAPI because a memory discusses a FastAPI route.

These must not automatically receive identical lifecycle or confidence treatment.


## 10G — Graph Enrichment

Extend the existing collective graph with entity and relationship intelligence.

The existing memory-oriented graph can evolve toward:

```text
Memory
   |
   +-- mentions --> Entity
                       |
                       +-- related_to --> Entity
   |
   +-- supports --> Relationship
```

This enables graph traversal based on entities rather than relying entirely
on memory-to-memory similarity.

For example:

```text
Browser
   |
   v
Mnemosyne
   |
   v
Athena
   |
   v
Supporting memories
```

Graph enrichment must preserve:

- source provenance
- qualified profile identity
- lifecycle
- revocation
- evidence
- distinction between explicit and inferred relationships

## 10H — Entity-Aware Hybrid Retrieval

Phase 8 established:

BM25
  +
Semantic
  +
Graph
  +
Temporal
  |
  v
RRF
  |
  v
CrossEncoder

Phase 10 may add entity-aware candidate expansion or ranking:

Query
 |
 +-- BM25
 +-- Semantic
 +-- Graph
 +-- Entity
 +-- Temporal
       |
       v
     RRF
       |
       v
 CrossEncoder
       |
       v
 HybridResult

The initial goal is to make entity information available as a governed
retrieval signal.

Do not unnecessarily redesign the proven Phase 8/9 retrieval architecture.

Existing hybrid retrieval behavior must remain backward compatible.

## 10I — Browser Entity & Relationship Exploration

Extend the Browser to expose entity intelligence.

Entity Inspector

Potential presentation:

Mnemosyne Visual Monitor
─────────────────────────
Type: Project

Aliases
  Mnemosyne
  Mnemosyne VM

Relationships
  uses → FastAPI
  contains → Hybrid Retrieval
  has_profile → Athena

Evidence
  37 memories
  4 profiles
Relationship Inspector

Potential presentation:

Mnemosyne ── uses ── FastAPI

Confidence: 0.96
Status: inferred

Evidence:
  Athena memory #...
  Horus memory #...
  Odin memory #...
Entity Graph

Allow the existing graph infrastructure to eventually represent:

memory nodes
entity nodes
relationship edges

The Browser remains an inspection and controlled interaction surface rather
than an unrestricted entity/relationship write path.

## 10J — Rebuild & Idempotency

Entity and relationship intelligence is derived data and must be safely
rebuildable.

Conceptually:

Collective Memories
       |
       v
Entity Extraction
       |
       v
Entity Resolution
       |
       v
Relationship Extraction
       |
       v
Entity/Relationship Index

Repeated rebuilds must not create duplicate entities or relationships.

This enables:

reproducible rebuilds
model upgrades
extraction corrections
experimentation
rollback
regeneration of derived intelligence

The collective memory and provenance layer remains authoritative.

## 10K — Testing & Production Validation

Phase 10 requires validation at multiple levels.

Unit tests
entity normalization
alias handling
entity type validation
candidate generation
entity resolution
ambiguity handling
relationship validation
confidence handling
Persistence tests
entity storage
evidence storage
relationship storage
duplicate prevention
idempotent rebuilds
Governance tests
provenance preservation
profile identity preservation
revoked evidence handling
lifecycle handling
ambiguous resolution
no silent entity merging
explicit vs inferred relationship distinction
Retrieval tests
entity-aware candidate expansion
entity retrieval signal
compatibility with existing hybrid retrieval
preservation of Phase 8/9 behavior
Browser tests
entity inspection
relationship inspection
evidence navigation
graph enrichment
existing visualization regression
Production-style validation

As demonstrated during Phase 9, anything involving cached services,
SQLite, FastAPI worker threads, or shared retrieval state must be validated
under realistic execution conditions rather than only isolated unit tests.

## Phase 10 Implementation Sequence

Phase 10 should be implemented incrementally rather than as one large change.

Stage	Work
10A	Entity schema/domain model
10B	Entity extraction pipeline
10C	Entity evidence/provenance
10D	Entity resolution
10E	Relationship model
10F	Relationship extraction
10G	Graph enrichment
10H	Entity-aware retrieval
10I	Browser entity/relationship inspection
10J	Rebuild/idempotency + production validation
10K	Phase 10 audit and closeout

Each stage should be validated before proceeding to the next.

## Governance Requirements

Phase 10 must not:

silently merge entities
modify source-profile memories
bypass collective promotion
bypass revocation
fabricate provenance
expose private memory content through visualization
automatically treat inferred relationships as facts
flatten qualified profile identities
allow Browser visualization to become an uncontrolled write path
perform destructive consolidation without explicit governed handling

Derived entity and relationship intelligence must remain rebuildable and
auditable.

## Phase 10 Exit Criteria

Phase 10 is complete when:

 Canonical entity model exists
 Entity types are defined
 Entity mentions retain source evidence
 Entity extraction works against collective memories
 Entity resolution handles aliases
 Ambiguous resolution is explicitly represented
 No silent entity merges occur
 Relationship model exists
 Relationships retain evidence
 Explicit and inferred relationships are distinguishable
 Relationship lifecycle is governed
 Collective graph can represent entity relationships
 Entity-aware retrieval works
 Phase 8/9 retrieval remains backward compatible
 Browser can inspect entities
 Browser can inspect relationships
 Evidence can be traced back to source memories
 Profile identities remain qualified and governed
 Derived entity data can be rebuilt idempotently
 Revocation and lifecycle rules are respected
 Full repository regression passes
 Live corpus validation passes
 Browser validation passes
 Phase 10 completion audit is written
 Phase 10 documentation is archived appropriately
 Phase 11 is explicitly defined as the next phase
## Phase 10 Completion Record

Phase 10 was implemented incrementally through stages 10A–10J and
validated against both the repository test suite and the live collective
corpus.

### Implemented capabilities

- Canonical entity data model and lifecycle handling
- Deterministic entity extraction
- Entity mentions with source-memory references
- Entity evidence and provenance structures
- Deterministic entity resolution
- Explicit `same_entity` resolution records
- Relationship model and relationship evidence
- Conservative explicit relationship extraction
- Entity-aware graph projection
- Entity graph API
- Browser entity inspection
- Browser mention-edge inspection
- Entity-aware hybrid retrieval
- Deterministic rebuild and idempotency support
- Read-only source-memory access through the memory gateway
- Preservation of collective promotion/revocation state
- Preservation of qualified profile identity

### Final real-corpus validation

The Phase 10 rebuild was executed against the current collective corpus.

Final derived-data counts:

- Collective entries: 570
- Active canonical entities: 21
- Entity mentions: 706
- Entity resolutions: 706
- Entity evidence records: 706
- Relationships: 0
- Relationship evidence records: 0

The 0 relationship result is intentional. Relationship extraction remains
conservative and explicit-only; the current corpus did not contain
sufficiently strong qualifying relationship statements to create semantic
relationship records. The extractor was not loosened merely to manufacture
relationships.

The entity set consisted of two projects and nineteen technology entities.
The extraction-quality correction eliminated the earlier false-positive
capitalized instruction/document fragments.

### Rebuild and idempotency

A second complete Phase 10 rebuild was executed against the same corpus.

The second rebuild reproduced the same entity, mention, resolution,
evidence, and relationship snapshots while leaving the authoritative
collective entries and collective provenance unchanged.

This confirms that the Phase 10 derived intelligence can be regenerated
deterministically.

### Source integrity

The production-style rebuild was performed through the distributed memory
gateway. Source profile memories were read but not modified.

The validated corpus contained:

- Athena: 443 eligible memories
- Horus: 41
- Odin: 55
- Thoth: 29
- Friday: 1
- Vulcan: 1

All 570 eligible collective entries remained promoted and non-revoked during
the validation.

### Automated validation

The final repository validation passed:

- Full pytest suite: 551 passed, 5 skipped, 4 warnings
- Entity graph focused tests: 15 passed
- Entity extraction focused tests: 20 passed
- Phase 10 rebuild focused tests: 54 passed
- Python compilation checks passed
- JavaScript syntax checks passed
- `git diff --check` passed

### Browser validation

The live Browser validation passed after the Phase 10 entity graph and
inspection changes.

The validated Entity Graph exposed:

- 21 entity nodes
- 570 memory-reference nodes
- 706 mention edges
- 0 semantic relationship edges

Entity nodes displayed human-readable canonical names and entity metadata.
Mention edges were selectable and exposed evidence metadata without exposing
raw source-memory content.

### Governance validation

Phase 10 preserves the established governance boundary:

- no silent entity merging
- no modification of source-profile memories
- no bypass of collective promotion
- no bypass of revocation
- no fabricated provenance
- no private raw-memory exposure through the entity graph
- no automatic promotion of inferred relationships to facts
- qualified profile identities remain intact
- Browser remains a read-only inspection surface
- derived entity/relationship data remains rebuildable

### Phase 10 completion assessment

All implemented Phase 10 capabilities have been validated at the unit,
integration, real-corpus, rebuild/idempotency, and browser levels.

Phase 10 is therefore **COMPLETE**.

The next architectural step is Phase 11 — Temporal Intelligence.

## Phase 10 Outcome

When complete, Mnemosyne will have progressed from simply finding relevant
memories toward understanding the entities and relationships represented by
those memories.

The intended progression is:

Memory → Retrieval → Entities → Relationships → Understanding

This provides the foundation for Phase 11 — Temporal Intelligence, where
entity and relationship state can be understood across time.
