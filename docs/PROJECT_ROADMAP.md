# Mnemosyne Visual Monitor — Authoritative Project Roadmap

**Status:** Phase 9 in progress — Browser-facing hybrid retrieval integration
**Last updated:** 2026-09-09

## Purpose

Mnemosyne Visual Monitor is a local-first system for observing, governing, searching, and visualizing memory across Hermes profiles while preserving provenance, profile isolation, mediation, promotion governance, revocation, and explicit adoption.

This document is the authoritative implementation roadmap. Historical roadmap documents should not be treated as the current phase authority.

## Architectural invariants

The following remain mandatory throughout all phases:

- Local-first operation.
- SQLite remains the primary persistence mechanism unless a later phase explicitly justifies otherwise.
- Private profile memory remains isolated from collective knowledge unless explicitly promoted/adopted through the governance path.
- Provenance must survive every transformation.
- Revoked knowledge must not silently re-enter retrieval or collective views.
- Retrieval must be explainable enough to identify why a result was returned.
- Network/LAN discovery must not imply automatic trust or automatic memory adoption.
- Changes that affect governance or data integrity must be deterministic and testable.

## Phase status

| Phase | Area | Status |
|---|---|---|
| 1 | Foundations & Discovery | COMPLETE |
| 2 | Mediation Plane / Air-Lock | COMPLETE |
| 3 | Collective Knowledge Base | COMPLETE |
| 4 | Athena Interface | COMPLETE |
| 5 | Semantic Embeddings & Vector Search | COMPLETE |
| 6 | Collective Visualization & Distributed Discovery | COMPLETE |
| 7 | Browser / Visual Monitor | COMPLETE |
| 8 | Hybrid Retrieval | COMPLETE |
| 9 | Browser-Facing Hybrid Retrieval Integration | IN PROGRESS — 9A/9B implemented |
| 10 | Entity & Relationship Intelligence | PLANNED |
| 11 | Temporal Intelligence | PLANNED |
| 12 | Evidence Consolidation & Memory Synthesis | PLANNED |
| 13 | Higher-Level Mental Models | PLANNED |
| 14 | Cross-Profile Learning & Controlled Transfer | PLANNED |
| 15 | Advanced Retrieval Optimization | PLANNED |
| 16 | Distributed Collective / LAN Federation | PLANNED |
| 17 | Governance, Audit & Security Hardening | PLANNED |
| 18 | Productionization, Deployment & Final Validation | PLANNED |

## Phase 7 — Browser / Visual Monitor

Phase 7 is complete.

The Browser provides the operational visual surface for the system, including:

- profile selection/filtering;
- information, timeline, graph/constellation, and 3D views;
- configurable tiles;
- configurable number of tiles;
- selectable tile content;
- graph navigation and zooming;
- node/edge visualization;
- inspector/selection flow;
- persisted UI state;
- rebuild/discovery controls;
- browser integration coverage;
- incremental memory scanning.

Phase 7 completion is documented in:

`docs/PHASE_7_COMPLETION_AUDIT_2026-09-06.md`

## Phase 8 — Hybrid Retrieval

Phase 8 is complete. It combines multiple complementary retrieval signals rather than relying on embeddings alone.

### 8A — Keyword retrieval / BM25

**Status: COMPLETE — 2026-09-07**

Implemented SQLite FTS5-based lexical retrieval over governed searchable memory.

Completed:

- deterministic indexing;
- BM25 ranking;
- explicit scope/profile filtering;
- provenance preservation;
- exclusion of revoked/non-searchable records;
- lifecycle authorization against authoritative collective state;
- rebuildable retrieval cache in `data/retrieval.db`;
- distributed source-memory access through `DistributedMemoryGateway`;
- unit and integration tests.

Production validation:

- 567 / 567 eligible collective entries indexed;
- 0 skipped;
- 0 failed;
- 567 retrieval-index rows;
- 567 / 567 distributed source memories accessible;
- full regression suite: 208 passed, 4 skipped.

The retrieval index remains separate from `collective.db`. The collective database remains authoritative for promotion, revocation, provenance, source identity, and retrieval authorization.

The FTS5 Porter tokenizer was retained after a controlled comparison with `unicode61` against the production corpus. Technical identifiers tested with zero lexical matches were also absent from the underlying source memories, so no tokenizer change was warranted.

Governance invariant:

> Indexed does not mean authorized to retrieve.

### 8B — Semantic retrieval hardening

**Status: COMPLETE — 2026-09-07**

Established a governed semantic retrieval contract through `SemanticSearcher`.

Completed:

- strict 384-dimensional query validation;
- finite/non-zero query validation;
- stored embedding validation;
- promoted/non-revoked filtering;
- optional source-profile filtering;
- normalized cosine similarity;
- deterministic score/entry-ID ordering;
- rich scored results;
- provenance preservation;
- legacy Athena compatibility.

Validation:

- 19 focused tests passed;
- 219 full regression tests passed;
- 4 tests skipped;
- 0 failures;
- production validation: 567 eligible embedded entries;
- production top result self-match: 1.000000;
- production semantic validation: PASS.

`collective.db` remains authoritative for lifecycle authorization, provenance, promotion, revocation, and source identity.

### 8C — Graph-aware retrieval

**Status: COMPLETE — 2026-09-07**

Implemented bounded graph-aware candidate expansion using the existing
authoritative collective graph.

Completed:

- controlled one-hop graph expansion;
- deterministic per-seed limits;
- collective entry-ID preservation;
- lifecycle authorization;
- promoted/non-revoked filtering;
- profile filtering;
- provenance preservation;
- deterministic ordering;
- focused and full regression tests;
- production validation.

Graph expansion remains a candidate-discovery mechanism rather than an
authorization mechanism. Score fusion is handled independently by 8E.

### 8D — Temporal retrieval

**Status: COMPLETE — 2026-09-07**

Implemented governed temporal retrieval with explicit separation between
event-date retrieval and recording-time recency.

Completed:

- inclusive event-date window filtering;
- explicit `event_date_precision` handling;
- unknown event dates are never guessed;
- recording-time recency weighting;
- `timestamp` then `created_at` fallback;
- future timestamps capped at maximum recency;
- profile filtering;
- promoted/non-revoked filtering;
- missing/malformed temporal metadata is skipped safely;
- provenance preservation;
- deterministic ordering;
- focused temporal tests;
- full regression validation.

Temporal relationships and event-proximity reasoning remain future work and
are intentionally deferred to the later Temporal Intelligence phase.

### 8E — Rank fusion

**Status: COMPLETE — 2026-09-07**

Implemented deterministic Reciprocal Rank Fusion across the four independent
retrieval channels:

- keyword/BM25;
- semantic;
- graph;
- temporal.

The fusion layer consumes already-ranked candidates and does not query
databases or interpret channel-specific scores.

RRF contribution:

`weight / (k + rank)`

with one-based ranks and a default `k=60`.

Completed:

- configurable channel weights;
- missing-channel zero contribution;
- duplicate candidate handling;
- deterministic score and entry-ID ordering;
- configurable `top_k`;
- invalid configuration validation;
- identity preservation;
- provenance preservation;
- per-channel rank retention;
- per-channel contribution retention;
- explicit independence from raw channel scores.

This preserves the underlying retrieval contributions needed for the future
8G explainability layer.

Validation:

- focused 8E tests: **12 passed**;
- full project regression: **256 passed, 4 skipped**;
- existing FastAPI `on_event()` deprecation warnings remain unrelated to 8E.

### 8F — Optional local reranking

Add a local reranker only after the base hybrid pipeline is stable.

The reranker must be optional and must not become a mandatory network dependency.

### 8G — Retrieval explainability

Expose why a result was returned.

A result should be able to report relevant signals such as:

- lexical/BM25 match;
- semantic similarity;
- graph relationship;
- temporal relevance;
- fused rank;
- reranker contribution, when enabled;
- provenance/source profile.

### Phase 8 exit criteria

Phase 8 is complete only when:

1. lexical and semantic retrieval both work;
2. graph and temporal signals can contribute;
3. fusion is deterministic;
4. revoked/non-governed content is excluded correctly;
5. provenance survives retrieval;
6. retrieval explanations are available;
7. integration and regression tests pass;
8. documentation describes the retrieval contract.

## Phase 9 — Browser-Facing Hybrid Retrieval Integration

Expose the completed Phase 8 retrieval pipeline through the operational Browser.

Focus:

- browser API boundary;
- hybrid search controls;
- explainability presentation;
- profile/date filtering;
- source-memory inspection;
- retrieval error handling;
- live-corpus validation.

Implementation details are tracked in `docs/PHASE_9_BROWSER_HYBRID_RETRIEVAL.md`.

## Phase 10 — Entity & Relationship Intelligence

Build stronger entity resolution and relationship semantics.

Focus:

- entity extraction/normalization;
- entity identity resolution;
- aliases;
- relationship typing;
- confidence;
- provenance;
- conflict handling.

## Phase 11 — Temporal Intelligence

Move beyond timestamp filtering into temporal relationships.

Focus:

- before/after;
- duration;
- recurrence;
- temporal validity;
- changing facts;
- temporal conflict detection.

## Phase 12 — Evidence Consolidation & Memory Synthesis

Combine related memories into evidence-backed knowledge units.

Focus:

- evidence clustering;
- duplicate/near-duplicate detection;
- contradiction handling;
- confidence;
- source weighting;
- traceable synthesis.

## Phase 13 — Higher-Level Mental Models

Derive stable concepts and models from accumulated governed knowledge.

Focus:

- concepts;
- patterns;
- abstractions;
- topic structures;
- inferred relationships;
- explicit distinction between observed facts and derived models.

## Phase 14 — Cross-Profile Learning & Controlled Transfer

Enable governed learning between Hermes profiles.

Focus:

- candidate knowledge;
- benefit analysis;
- explicit adoption;
- profile-specific adaptation;
- provenance;
- rollback/revocation.

## Phase 15 — Advanced Retrieval Optimization

Optimize retrieval quality after the hybrid foundation is proven and browser-integrated.

Focus:

- query classification;
- retrieval routing;
- latency/quality tradeoffs;
- multilingual retrieval;
- evaluation datasets;
- measurable retrieval metrics;
- future reranking improvements beyond the validated Phase 8F baseline.

## Phase 16 — Distributed Collective / LAN Federation

Expand controlled collective knowledge across trusted local Mnemosyne instances.

Focus:

- discovery;
- identity;
- trust;
- synchronization;
- conflict resolution;
- explicit adoption;
- federation observability.

LAN discovery implemented during earlier phases is a foundation, not automatic federation.

## Phase 17 — Governance, Audit & Security Hardening

Harden the system before production deployment.

Focus:

- complete audit trails;
- permission boundaries;
- revocation guarantees;
- migration safety;
- integrity checks;
- failure recovery;
- security review;
- adversarial testing.

## Phase 18 — Productionization, Deployment & Final Validation

Prepare for deployment and operational use.

Focus:

- deployment packaging;
- backup/restore;
- monitoring;
- upgrade/migration procedures;
- performance validation;
- operational documentation;
- final end-to-end validation.

The planned final deployment target is the user's Unraid environment. Development remains local until the project reaches the deployment phase.

## Hindsight-inspired improvements

The roadmap incorporates ideas inspired by modern memory systems such as Hindsight, while preserving Mnemosyne's governance architecture.

Important additions include:

- hybrid semantic + lexical retrieval;
- graph-aware retrieval;
- temporal retrieval;
- rank fusion;
- optional reranking;
- entity resolution;
- evidence consolidation;
- stronger temporal relationships;
- higher-level mental models;
- retrieval explainability.

These are implementation inspirations, not permission to copy external project architecture blindly.

## Completion policy

A phase is not complete merely because code exists.

Every phase requires:

1. implementation;
2. automated tests;
3. integration/regression verification;
4. documentation;
5. roadmap status update;
6. explicit exit criteria review.

Only then should the phase be marked COMPLETE.
