# Mnemosyne Visual Monitor — Authoritative Project Roadmap

**Status:** Phase 15 complete — Phase 16 ready to begin
**Last updated:** 2026-09-20

## Purpose

Mnemosyne Visual Monitor is a local-first system for observing, governing, searching, and visualizing memory across Hermes profiles while preserving provenance, profile isolation, mediation, promotion governance, revocation, and explicit adoption.

This document is the authoritative implementation roadmap. Historical roadmap documents should not be treated as the current phase authority.

## Data Science & Data Engineering Objective

Mnemosyne Visual Monitor is intentionally developed as an applied
**Data Science + Data Engineering project**, in addition to being a software
system for governed memory and knowledge management.

The roadmap therefore evaluates phases not only by whether functionality works,
but also by whether the resulting architecture demonstrates sound data
engineering and data science practices.

### Data Engineering

Cross-cutting Data Engineering concerns include:

- data modeling and schema design;
- governed ingestion and transformation;
- data contracts;
- validation and data quality;
- provenance and lineage;
- deterministic and idempotent processing;
- lifecycle/state management;
- duplicate handling;
- revocation propagation;
- derived-data management;
- testable pipeline boundaries;
- API/data-serving boundaries;
- scalability and production-readiness considerations.

### Data Science

Cross-cutting Data Science concerns include:

- similarity and signal engineering;
- entity resolution;
- temporal analysis;
- retrieval and ranking;
- evidence weighting;
- corroboration;
- contradiction analysis;
- threshold selection;
- empirical evaluation;
- explainability;
- separation of statistical/model signals from governance decisions.

### Final External Review

When the implementation roadmap is complete, the project should be presented
to experienced Data Scientists and Data Engineers for critical review.

The final review should seek feedback on:

- data-model quality;
- pipeline architecture;
- algorithmic choices;
- statistical assumptions;
- evaluation methodology;
- reproducibility;
- data quality;
- provenance;
- scalability;
- observability;
- production readiness;
- opportunities for stronger experimentation or modeling.

The external review is a **learning and validation step**, not a claim that the
project is production-complete or scientifically validated.

See
`docs/PROJECT_DATA_SCIENCE_DATA_ENGINEERING_POSITIONING.md`
for the detailed review framework.

---

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
| 9 | Browser-Facing Hybrid Retrieval Integration | COMPLETE |
| 10 | Entity & Relationship Intelligence | COMPLETE |
| 11 | Temporal Intelligence | COMPLETE |
| 12 | Evidence Consolidation & Memory Synthesis | COMPLETE |
| 13 | Higher-Level Mental Models | NEXT — READY TO BEGIN |
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

**Implementation status:** COMPLETE
**Final status:** COMPLETE — 2026-09-13
**Current repository HEAD:** `16a5ab7` — `Complete Phase 11F.5 temporal visualization`

Phase 11 extends Mnemosyne's entity and relationship intelligence with
governed temporal understanding.

Completed implementation:

- **11A — Temporal Evidence Foundation**
  - governed temporal evidence schema and validation;
  - provenance, precision, confidence, and lifecycle enforcement.
- **11B.1–11B.5 — Temporal Extraction**
  - temporal assertion contract;
  - explicit date/phrase extraction;
  - explicit state-change extraction;
  - evidence promotion;
  - deterministic extraction/promotion pipeline.
- **11C.1–11C.20 — Temporal Reasoning**
  - interval and precision-aware reasoning;
  - consistency and semantic contradiction detection;
  - aggregation and state timelines;
  - state transitions and immutable histories;
  - history comparison, divergence, consensus, and synthesis;
  - trajectory classification, comparison, and consensus;
  - change-point analysis;
  - change-point significance;
  - transition persistence;
  - evidence-backed trajectory analysis;
  - historical synthesis.
- **11E — Temporal Graph Integration**
  - temporal relationship derivation;
  - governed temporal graph projection;
  - temporal query intent/scoring/context;
  - temporal conflict and state-change services;
  - integration with hybrid retrieval.
- **11F.4 — Temporal History Routes**
  - governed entity history API;
  - governed relationship history API;
  - temporal history view;
  - historical state and summary services.
- **11F.5 — Temporal Visualization**
  - entity temporal visualization endpoint;
  - relationship temporal visualization endpoint;
  - evidence, precision, confidence, source profile, and source-memory display;
  - explicit UI treatment of missing temporal evidence as unknown rather than an inferred ending.

### Phase 11 governance invariants

The following remain mandatory:

- source-memory immutability;
- provenance preservation;
- promoted and non-revoked evidence only;
- profile/source-memory consistency;
- no fabricated dates, bounds, or missing states;
- descriptive reasoning before any future inferential layer;
- deterministic rebuildability;
- derived temporal analysis must not silently become authoritative evidence.

### Phase 11 validation

Focused temporal validation against the supplied repository snapshot:

- `447 passed, 10 skipped, 4 warnings` across temporal test modules.
- The 4 warnings are the existing FastAPI `on_event` deprecation warnings.
- The full repository run in the isolated snapshot could not be treated as the authoritative baseline because the supplied environment lacks `sentence_transformers`, and the snapshot also exposes unrelated baseline failures in hybrid-route/profile-discovery tests. These are not evidence of a Phase 11 temporal defect.
- Final closure must therefore be performed in the project's normal `.venv` on the actual working repository.

### Phase 11 exit criteria

The Phase 11 closure criteria were completed before Phase 12 implementation
advanced:

1. The complete test suite was run in the normal project `.venv`.
2. Expected tests passed with only known/accepted skips and warnings.
3. Live desktop/browser validation covered:
   - temporal history;
   - entity temporal visualization;
   - relationship temporal visualization;
   - governed evidence filtering;
   - missing-time/unknown-state behavior.
4. No Athena work was required for Phase 11 closure.
5. Final Phase 11 documentation was committed.
6. The final Phase 11 completion tag was created.
7. The roadmap was advanced to Phase 12.

## Phase 12 — Evidence Consolidation & Memory Synthesis

**Status: COMPLETE — 2026-09-14**

Phase 12 establishes governed, evidence-preserving consolidation and memory
synthesis contracts.

Completed:

- observation similarity;
- deterministic near-duplicate detection;
- consolidation candidate modeling;
- evidence validation;
- evidence weighting;
- contradiction handling;
- evidence-preserving synthesis;
- revocation-aware current-support handling;
- provenance preservation;
- deterministic domain behavior;
- comprehensive Phase 12 validation.

Validation:

- 133 focused Phase 12 tests passed;
- 1,158 full regression tests passed;
- 14 tests skipped;
- 0 failures;
- `git diff --check` clean.

Phase 12 deliberately does not grant cross-profile learning or profile
adoption. Consolidation of authorized collective evidence remains distinct
from profile-specific adoption.

Completion audit:

`docs/archive/phase-12/PHASE_12_COMPLETION_AUDIT_2026-09-14.md`

## Phase 13 — Higher-Level Mental Models

**Status: COMPLETE**

Derive stable concepts and models from accumulated governed knowledge.

Focus:

- concepts;
- patterns;
- abstractions;
- topic structures;
- inferred relationships;
- explicit distinction between observed facts and derived models.

## Phase 14 — Cross-Profile Learning & Controlled Transfer

**Status: COMPLETE — archived under `docs/archive/phase-14/`**

Enable governed, explicitly authorized knowledge transfer between Hermes profiles without collapsing profile isolation or silently propagating private memory.

Focus:

- transfer candidates;
- source-profile authorization;
- destination-profile authorization;
- benefit and applicability analysis;
- explicit adoption;
- profile-specific adaptation;
- provenance and evidence preservation;
- conflict handling;
- revocation and rollback;
- immutable transfer audit history;
- strict prevention of implicit cross-profile learning.

## Phase 15 — Advanced Retrieval Optimization

**Status: COMPLETE — archived under `docs/archive/phase-15/`**

Optimize retrieval quality after the hybrid foundation is proven and browser-integrated.

Focus:

- query classification;
- retrieval routing;
- latency/quality tradeoffs;
- multilingual retrieval;
- evaluation datasets;
- measurable retrieval metrics;
- retrieval diagnostics and explainability;
- governed multilingual fallback;
- retrieval evaluation and regression protection.

Phase 15 final validation:

- 1,498 tests passed;
- 14 tests skipped;
- 0 failures;
- 4 FastAPI deprecation warnings;
- 19.43 seconds;
- `git diff --check` clean.

The authoritative completion audit is
`docs/PHASE_15_COMPLETION_AUDIT.md`.

## Phase 16 — Distributed Collective / LAN Federation

**Status: CURRENT — READY TO BEGIN**

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
