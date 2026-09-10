# Phase 10 — Entity & Relationship Intelligence

**Status:** PLANNED — READY TO BEGIN
**Planned start:** 2026-09-09
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
## Phase 10 Outcome

When complete, Mnemosyne will have progressed from simply finding relevant
memories toward understanding the entities and relationships represented by
those memories.

The intended progression is:

Memory → Retrieval → Entities → Relationships → Understanding

This provides the foundation for Phase 11 — Temporal Intelligence, where
entity and relationship state can be understood across time.
