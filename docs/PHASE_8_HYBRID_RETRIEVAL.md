# Phase 8 — Hybrid Retrieval

**Status:** IN PROGRESS — 8A + 8B + 8C + 8D + 8E + 8F COMPLETE
**Started:** 2026-09-07
**Current:** Phase 8G — Explainability
**Target:** Build a deterministic, explainable hybrid retrieval layer.

## Objective

Mnemosyne currently has semantic/vector retrieval and graph infrastructure. Phase 8 adds complementary retrieval signals so that a query can find information through:

- exact/lexical matching;
- semantic similarity;
- graph relationships;
- temporal relevance;
- deterministic rank fusion;
- optional local reranking.

The goal is better recall and precision without weakening governance or provenance.

## Core design

```text
                         Query
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
          BM25         Semantic        Graph
             |             |             |
             +-------------+-------------+
                           |
                      Candidate Set
                           |
                      Temporal Signal
                           |
                     Rank Fusion
                           |
                   Optional Reranker
                           |
                    Final Results
                           |
                    Explanation Data
```

## 8A — SQLite FTS5 / BM25

### Goal

Add lexical retrieval using SQLite FTS5 while keeping the system local-first.

### Requirements

- FTS5-backed index;
- BM25 ranking;
- deterministic result ordering;
- searchable-content contract;
- explicit scope filtering;
- profile-aware filtering where applicable;
- exclusion of revoked records;
- exclusion of records that are not eligible for the retrieval surface;
- provenance retained;
- index maintenance on lifecycle changes.

### Important constraint

Do not duplicate private profile memory into the collective database merely to make FTS convenient.

The retrieval layer must respect the existing separation between:

- private profile memory;
- mediated/promoted collective knowledge;
- governed searchable content.

### 8A implementation status

Phase 8A is complete.

Implemented:

- SQLite FTS5 lexical retrieval;
- BM25 ranking;
- deterministic result ordering;
- rebuildable retrieval cache at `data/retrieval.db`;
- governed indexing of promoted, non-revoked collective entries;
- profile-aware result filtering;
- authoritative lifecycle verification against `collective.db`;
- provenance preservation;
- stale-index protection;
- distributed source-memory access through `DistributedMemoryGateway`;
- unit and integration coverage.

Production validation:

- collective entries eligible for retrieval: **567**;
- indexed successfully: **567**;
- skipped: **0**;
- failed: **0**;
- retrieval index rows: **567**;
- distributed source-memory reads: **567 / 567** accessible;
- full regression suite: **208 passed, 4 skipped**.

The lexical index is intentionally separate from `collective.db`.

`collective.db` remains authoritative for:

- promotion;
- revocation;
- provenance;
- source identity;
- retrieval authorization.

`data/retrieval.db` is a rebuildable retrieval cache. Indexed content does not grant retrieval authorization by itself.

The FTS5 index currently uses the Porter tokenizer. A controlled comparison against SQLite's `unicode61` tokenizer was performed against the production 567-memory corpus. The tested technical identifiers that returned zero results were also absent from the underlying source corpus, so no tokenizer change was justified.

Governance invariant:

> **Indexed ≠ authorized to retrieve.**

Lifecycle authorization is rechecked against `collective.db` when search results are returned.

## 8B — Semantic retrieval hardening

**Status: COMPLETE — 2026-09-07**

Phase 8B established the governed semantic retrieval contract and completed the
migration from the deterministic compatibility embedding path to the production
local `all-MiniLM-L6-v2` semantic encoder.

### 8B.1 — Semantic retrieval contract

Implemented:

- dedicated `SemanticSearcher` retrieval service;
- rich `SemanticResult` records containing entry ID, source profile,
  origin memory ID, semantic score, and provenance;
- strict 384-dimensional query validation;
- rejection of non-finite query values;
- rejection of zero-norm query vectors;
- validation of stored embedding dimensions;
- rejection of malformed, non-finite, and zero-norm stored embeddings;
- promoted and non-revoked lifecycle filtering;
- optional source-profile filtering;
- normalized cosine similarity;
- deterministic ordering by semantic score descending, then entry ID ascending;
- provenance preservation through the authoritative collective DAO;
- compatibility preservation for the existing `AthenaAPI.search_by_embedding()`
  contract.

The existing legacy Athena method remains available for compatibility. Its
historical arbitrary-dimension and zero-vector behavior is preserved rather
than silently changed by the new strict semantic retrieval contract.

### 8B.2 — Production local semantic encoder

The production encoder is now a real local `SentenceTransformer` implementation
using:

- model: `all-MiniLM-L6-v2`;
- embedding dimension: **384**;
- output type: normalized `float32`;
- runtime backend: PyTorch;
- runtime model loading: local files only;
- network access: not required;
- development validation device: CPU.

The deterministic `embed_sanitized()` implementation remains unchanged as a
legacy compatibility path. It is not used as the production semantic encoder.

Focused encoder validation confirmed:

- correct 384-dimensional output;
- `float32` output;
- unit-norm embeddings;
- semantically meaningful similarity;
- deterministic repeated encoding;
- rejection of invalid and empty input.

Focused embedding-generator and encoder tests:

- **23 passed**

### 8B.3 — Controlled atomic embedding rebuild

A dedicated `rebuild_embeddings()` service was introduced for the migration.

The rebuild:

- processes promoted and non-revoked entries only;
- processes entries in ascending collective entry ID order;
- retrieves source content exclusively through the `MemoryGateway` abstraction;
- validates every generated embedding before database update;
- replaces existing embeddings explicitly;
- performs all SQLite updates inside one transaction;
- rolls back the complete operation if source retrieval or encoding fails;
- does not modify source Hermes/Mnemosyne databases.

A controlled migration copy of `data/collective.db` was rebuilt successfully:

- total collective entries: **567**
- eligible entries: **567**
- processed: **567**
- updated: **567**
- failures: **0**
- valid migrated embeddings: **567**
- invalid migrated embeddings: **0**
- original embedding fingerprints changed: **10/10** sampled entries

### 8B.4 — Migration safety gates

#### Gate 1 — Collective integrity

The migration copy was compared with the live database before any live
migration.

Results:

- live rows: **567**
- migration rows: **567**
- non-embedding mismatches: **0**
- provenance rows: **0** in both databases
- provenance identical: **True**
- eligible live entries: **567**
- eligible migration entries: **567**
- embeddings changed: **567**
- embeddings identical: **0**
- embedding size changes: **0**
- SQLite integrity: **ok** on both databases

**Gate 1: PASS**

This establishes that the controlled migration changed semantic embedding
content only; collective identity, lifecycle state, validation state,
revocation state, and provenance were preserved.

#### Gate 2 — Graph integrity

The graph was rebuilt against the migrated embeddings.

Results:

- eligible entries: **567**
- embedded entries: **567**
- graph nodes: **567**
- graph embeddings: **567**
- node identity match: **True**
- directed graph edges discovered: **3418**
- lifecycle-invalid graph nodes: **0**
- repeated graph expansion: deterministic

**Gate 2: PASS**

The migrated embeddings therefore remain compatible with the existing graph
architecture and produce a healthy deterministic graph without bypassing
collective lifecycle governance.

### 8B.5 — Semantic retrieval quality validation

A controlled comparison was performed using 12 representative retrieval
queries against the deterministic compatibility embeddings and the new
MiniLM embeddings.

The average top-5 overlap was **0.83/5**.

The low overlap is expected and is not itself a regression: the deterministic
path and the MiniLM encoder represent fundamentally different embedding
spaces. The important result was qualitative relevance of the new rankings.

Observed results included:

- architecture queries returning architecture-related memories;
- database-schema queries returning direct Hermes schema investigations;
- timeline queries returning timeline-related debugging memories;
- LAN discovery queries returning local discovery memories;
- graph visualization queries returning collective visualization memories;
- semantic-embedding queries returning embedding/review/architecture clusters;
- repository-recovery queries returning multiple recovery-related memories;
- exact-marker queries retaining strong lexical matches.

The exact-marker test is particularly important for Phase 8 because it validates
the need for the combined keyword + semantic retrieval architecture rather than
semantic retrieval alone.

### Governance

`collective.db` remains authoritative for:

- promotion;
- revocation;
- source identity;
- provenance;
- retrieval authorization.

Semantic retrieval and embedding generation do not treat the presence of an
embedding as authorization.

Governance invariant:

> **Embedded ≠ authorized to retrieve.**

The embedding migration did not duplicate private source-memory content into
`collective.db`; source content continues to be retrieved through
`MemoryGateway`.

### Validation summary

Phase 8B validation established:

- production local MiniLM encoder: **PASS**
- controlled atomic rebuild: **PASS**
- Gate 1 collective integrity: **PASS**
- Gate 2 graph integrity: **PASS**
- semantic retrieval quality review: **PASS**
- source database write protection: **PASS**
- lifecycle filtering preservation: **PASS**
- provenance preservation: **PASS**

### Live migration status

The live semantic embedding migration has been completed and validated.

The live `data/collective.db` contains **570 collective entries**, with all
570 eligible promoted/non-revoked entries rebuilt using the production local
`all-MiniLM-L6-v2` encoder.

Live migration results:

- eligible entries: **570**
- embeddings rebuilt: **570**
- rebuild failures: **0**
- valid 384-dimensional embeddings: **570**
- invalid embeddings: **0**
- non-embedding data mismatches against the pre-migration backup: **0**
- embedding replacements: **570/570**
- embedding size changes: **0**
- SQLite integrity check: **PASS**
- source Mnemosyne databases changed: **0**

Post-migration graph validation:

- graph nodes: **570**
- unique graph identities: **570**
- embedded graph entries: **570**
- deterministic neighbor retrieval: **PASS**

Post-migration semantic retrieval validation:

- production local MiniLM query generation: **PASS**
- query dimensionality: **384**
- representative queries returning results: **3/3**
- top-5 result retrieval: **PASS**
- deterministic repeated retrieval: **PASS**
- lifecycle filtering remains enforced
- provenance remains preserved

The pre-migration backup is retained temporarily as a rollback artifact:

`data/collective.db.pre-8b-live-migration.bak`

The live migration is therefore considered complete. Phase 8F can proceed.


### Architectural boundary

Phase 8B intentionally does not:

- introduce graph retrieval;
- introduce temporal retrieval;
- introduce rank fusion;
- introduce CrossEncoder reranking;
- introduce retrieval explainability;
- duplicate private profile memory into `collective.db`.

The completed Phase 8 retrieval architecture is:

**Keyword + Semantic + Graph + Temporal → RRF rank fusion → optional reranking**

Cross-channel fusion is implemented in Phase 8E. CrossEncoder reranking remains
a subsequent Phase 8 stage.

## Phase 8C — Graph-Aware Retrieval

**Status:** COMPLETE
**Completed:** 2026-09-07

### Implementation

Phase 8C adds bounded graph-aware candidate expansion on top of the
authoritative collective graph.

Implemented:

- Entry-ID-oriented graph neighbor bridge in `GraphAggregator`
- `GraphSearcher` retrieval layer
- One-hop graph expansion from semantic/keyword seed candidates
- Collective entry-ID preservation
- Duplicate collective-entry preservation
- Lifecycle authorization against authoritative `collective.db`
- Revoked-entry exclusion
- Unpromoted-entry exclusion
- Optional source-profile filtering
- Cross-seed candidate deduplication
- Deterministic score ordering
- Per-seed expansion limits
- Provenance preservation

Graph score remains the existing cosine-similarity score and existing graph
threshold semantics are unchanged. Score fusion is intentionally deferred to
Phase 8E.

### Governance boundary

The graph remains a candidate-discovery mechanism, not an authorization
mechanism.

A graph-connected entry is not automatically authorized for retrieval.
`GraphSearcher` re-checks the authoritative collective lifecycle state before
returning a candidate.

The implementation deliberately operates on `collective_entries.id` rather
than converting through presentation-oriented `graph_id` values. This
preserves identity when duplicate `(source_profile, origin_memory_id)`
references exist.

### Validation

Focused Phase 8C tests:

- 9 passed

Graph generation + collective-reference + graph-search integration:

- 20 passed

Full project regression:

- 228 passed
- 4 skipped
- 4 existing FastAPI deprecation warnings

Production validation:

- Promoted entries: 567
- Graph nodes: 567
- Graph embeddings: 567
- Production seed: entry 2841
- Graph neighbors returned: 0
- Lifecycle authorization: PASS
- Entry-ID preservation: PASS
- Provenance preservation: PASS
- Deterministic ordering: PASS
- Graph expansion: PASS

The zero-neighbor production result is valid: the selected seed had no other
production embedding meeting the existing graph similarity threshold.

### Phase 8C completion criteria

- [x] Graph-aware candidate expansion implemented
- [x] Entry identity preserved
- [x] Lifecycle governance preserved
- [x] Revoked entries excluded
- [x] Unpromoted entries excluded
- [x] Profile filtering supported
- [x] Deterministic ordering
- [x] Provenance preserved
- [x] Focused tests pass
- [x] Full regression passes
- [x] Production validation passes

### Next

Phase 8D — Temporal Retrieval.
## 8D — Temporal retrieval

Add time relevance without requiring every memory to have a complete timestamp.

Possible signals include:

- event time;
- proposal time;
- observation time;
- recency;
- temporal relationship.

Missing temporal metadata must be handled explicitly rather than guessed.

## 8E — Rank fusion

**Status: COMPLETE — 2026-09-07**

Combine retrieval sources using deterministic Reciprocal Rank Fusion.

Implemented in:

`src/retrieval/rank_fusion.py`

### Fusion contract

The fusion layer consumes already-ranked results from four independent
retrieval channels:

- keyword/BM25;
- semantic;
- graph;
- temporal.

It does not query databases, perform embedding operations, or interpret
channel-specific raw scores.

For each channel, the contribution is:

`weight / (k + rank)`

where:

- `rank` is one-based;
- `k` defaults to `60`;
- each channel has an independently configurable weight.

Missing channels contribute zero.

Duplicate candidates within a channel are collapsed using their first
effective rank so duplicates do not consume additional rank positions.

Final ordering is deterministic:

1. fused score descending;
2. `entry_id` ascending for ties.

The fused result retains:

- canonical entry identity;
- source profile;
- origin memory ID;
- provenance;
- per-channel ranks;
- per-channel RRF contributions;
- final fused score.

This deliberately preserves the information required for the future 8G
retrieval-explainability layer.

### Validation

Focused Phase 8E tests:

- **12 passed**

Full project regression:

- **256 passed**
- **4 skipped**
- **4 existing FastAPI deprecation warnings**

The warnings are unrelated to Phase 8 retrieval and originate from the
existing `on_event()` lifecycle handlers.

### Phase 8E completion criteria

- [x] Deterministic rank fusion implemented
- [x] Keyword/BM25 contribution supported
- [x] Semantic contribution supported
- [x] Graph contribution supported
- [x] Temporal contribution supported
- [x] Configurable channel weights
- [x] Missing-channel handling
- [x] Duplicate-candidate handling
- [x] Deterministic tie ordering
- [x] Provenance preserved
- [x] Per-channel contributions retained
- [x] Focused tests pass
- [x] Full regression passes

### Next

Phase 8F — Optional Local Reranking.

Example conceptual result:

```text
entry_id: 123

keyword_rank: 4
semantic_rank: 2
graph_rank: 7
temporal_rank: 3
fused_score: <deterministic value>
```

## 8F — Optional reranking

**Status: COMPLETE — 2026-09-07**

Phase 8F adds an optional local CrossEncoder reranking stage after deterministic
8E rank fusion.

### Implementation

Implemented:

- `src/retrieval/cross_encoder.py` — local CrossEncoder adapter;
- `src/retrieval/reranker.py` — bounded query-time reranking service;
- `tests/test_cross_encoder.py`;
- `tests/test_reranker.py`.

The production reranker:

- consumes `FusedResult` candidates from Phase 8E;
- retrieves source content through the `MemoryGateway`;
- never re-queries or modifies stored embeddings;
- never writes to `collective.db`;
- applies a configurable candidate limit, defaulting to 20;
- returns a configurable final `top_k`;
- preserves collective identity, source profile, origin memory ID, channel ranks,
  fused score, channel contributions, and provenance;
- validates score count and finite values;
- uses deterministic `entry_id` ordering for score ties;
- fails in a controlled manner when source memory cannot be retrieved.

The CrossEncoder is optional and has no mandatory cloud dependency.

### Production model

The validated local model is:

- `cross-encoder/ms-marco-MiniLM-L6-v2`;
- local model path: `models/cross-encoder-ms-marco-MiniLM-L6-v2`;
- runtime: Sentence Transformers / PyTorch;
- validated on CPU and CUDA;
- model loading is local-only after installation;
- no network access is required at query time.

The model is an English/MS-MARCO passage-ranking model. It must not be represented
as multilingual retrieval capability.

### Focused validation

Phase 8F focused tests:

- CrossEncoder adapter: **9 passed**
- Reranker: **12 passed**
- Combined 8F + keyword focused tests: **38 passed**

### Frozen evaluation

A frozen evaluation set was created from the existing Mnemosyne corpus before the
Phase 8F benchmark.

Evaluation safeguards:

- **20 queries**
- frozen relevance judgments;
- current Mnemosyne corpus only;
- Phase 8 memories intentionally excluded;
- identical candidate generation for 8E and 8F;
- no collective database mutation during evaluation;
- metrics: Recall@5, Recall@10, MRR@5, MRR@10.

Evaluation artifacts:

- `docs/phase_8f_evaluation_set.json`
- `docs/phase_8f_evaluation_results.json`
- `scripts/evaluate_phase_8f.py`

### Evaluation results

| Metric | 8E RRF | 8F RRF + CrossEncoder | Delta |
|---|---:|---:|---:|
| Recall@5 | 0.4317 | **0.5192** | **+0.0875** |
| Recall@10 | 0.5833 | **0.6208** | **+0.0375** |
| MRR@5 | 0.4617 | **0.5267** | **+0.0650** |
| MRR@10 | 0.4806 | **0.5400** | **+0.0594** |

The CrossEncoder improved all four aggregate evaluation metrics.

These results provide measurable evidence that the reranking stage adds value to
the fused retrieval candidate set. The evaluation contains only 20 queries, so
the results are treated as engineering evidence rather than a claim of
statistical significance.

Some individual queries regressed after reranking. These are retained in the
evaluation artifact rather than tuned away individually. Queries with no relevant
candidates also demonstrate that reranking cannot repair candidate-generation
failures; those limitations belong to the broader retrieval architecture rather
than being treated as 8F defects.

### Governance boundary

Reranking is a ranking operation, not an authorization operation.

The reranker receives candidates already constrained by the retrieval architecture
and does not expand the candidate pool or bypass collective lifecycle filtering.

Governance remains authoritative in `collective.db`.

### Phase 8F completion criteria

- [x] Local/offline-capable CrossEncoder implemented
- [x] Optional query-time reranking implemented
- [x] Bounded candidate processing
- [x] Fused-result metadata preserved
- [x] Provenance preserved
- [x] Lifecycle filtering not bypassed
- [x] No collective DB writes
- [x] Deterministic tie handling
- [x] CPU validation
- [x] CUDA validation
- [x] Focused tests pass
- [x] Frozen evaluation set created
- [x] Baseline and reranked metrics measured
- [x] Aggregate improvement demonstrated

### Phase 8F conclusion

**Phase 8F is complete.**

The CrossEncoder is validated as an optional local reranking layer. Further
improvements to candidate generation, multilingual retrieval, or retrieval
coverage should be addressed as separate retrieval/knowledge work rather than
by destabilizing the completed 8F implementation.


## 8G — Explainability

Every hybrid result should be capable of answering:

> Why was this memory returned?

The explanation should identify applicable signals and preserve provenance.

## Testing strategy

Phase 8 should add:

### Unit tests

- FTS indexing;
- BM25 ranking;
- filtering;
- revocation;
- profile scope;
- semantic scoring;
- graph expansion;
- temporal scoring;
- rank fusion;
- tie ordering.

### Integration tests

- end-to-end hybrid query;
- lifecycle/index synchronization;
- promotion/revocation;
- multiple profiles;
- mixed retrieval signals;
- explainability payload.

### Regression tests

Existing Phase 1–7 tests must remain green except for tests explicitly classified as environment-dependent.

## 8A exit criteria

8A can be marked complete only when:

- FTS5 index exists;
- governed searchable records are indexed;
- BM25 retrieval works;
- filtering works;
- revoked records cannot appear;
- provenance is retained;
- lifecycle synchronization works;
- unit/integration tests pass;
- documentation is updated.

## Phase 8 final exit criteria

The entire phase is complete only when:

- BM25;
- semantic;
- graph;
- temporal;
- fusion;
- optional reranking;
- explainability

are integrated, tested, documented, and compatible with Mnemosyne's governance invariants.

## Current implementation status

Phase 8A through Phase 8F are complete.

The remaining Phase 8 implementation target is **8G — Explainability**.

The intended retrieval architecture is:

Keyword/BM25 → Semantic → Graph → Temporal → RRF (8E) → Top-N → Optional CrossEncoder (8F) → Final Results → Explainability (8G)

The individual retrieval components and the evaluation pipeline are operational. However, there is not yet a single production hybrid-retrieval orchestrator that exposes the complete pipeline as one unified service/API contract. The Phase 8F evaluation harness composes the retrieval components to measure the architecture without changing production retrieval behavior.

This distinction must remain explicit until unified production orchestration is implemented and validated.
