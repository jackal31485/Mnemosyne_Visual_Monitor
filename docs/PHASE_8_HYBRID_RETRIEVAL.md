# Phase 8 — Hybrid Retrieval

**Status:** IN PROGRESS — 8A + 8B COMPLETE  
**Started:** 2026-09-07  
**Current:** Phase 8C — Graph-Aware Retrieval  
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

Phase 8B established a stable, governed semantic retrieval contract without changing the existing embedding-generation backend.

Implemented:

- dedicated `SemanticSearcher` retrieval service;
- rich `SemanticResult` records containing entry ID, source profile, origin memory ID, semantic score, and provenance;
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
- compatibility preservation for the existing `AthenaAPI.search_by_embedding()` contract.

The existing legacy Athena method remains available for compatibility. Its historical arbitrary-dimension and zero-vector behavior is preserved rather than silently changed by the new strict semantic retrieval contract.

### Governance

`collective.db` remains authoritative for:

- promotion;
- revocation;
- source identity;
- provenance;
- retrieval authorization.

Semantic retrieval does not treat the presence of an embedding as authorization.

Governance invariant:

> **Embedded ≠ authorized to retrieve.**

### Validation

Focused semantic retrieval and legacy compatibility tests:

- **19 passed**

Full project regression:

- **219 passed**
- **4 skipped**
- **4 warnings**
- **0 failures**

Production validation:

- eligible embedded collective entries: **567**
- returned semantic results: **10**
- query embedding dimensions: **384**
- query entry self-match: **1.000000**
- top result: **entry 2841**
- status: **PASS**

The production semantic ranking matched the established Phase 8B baseline, confirming that the richer retrieval contract did not alter the underlying cosine-ranking behavior.

### Architectural boundary

Phase 8B intentionally does not:

- replace the embedding generator;
- introduce graph retrieval;
- introduce temporal retrieval;
- introduce rank fusion;
- introduce reranking;
- duplicate private profile memory into `collective.db`.

Those concerns remain isolated to subsequent Phase 8 stages.

## 8C — Graph-aware retrieval

Allow graph relationships to influence candidate selection.

Graph expansion must have:

- bounded depth;
- bounded candidate count;
- deterministic ordering;
- provenance;
- safeguards against traversal explosions.

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

Combine retrieval sources using Reciprocal Rank Fusion or another deterministic method documented in code and tests.

The fused result should retain the underlying contributions.

Example conceptual result:

```text
memory_id: 123

lexical_rank: 4
semantic_rank: 2
graph_rank: 7
temporal_rank: 3
fused_score: <deterministic value>
```

## 8F — Optional reranking

Only after 8A–8E are stable.

Requirements:

- local/offline-capable;
- optional;
- deterministic when configured deterministically;
- no mandatory cloud dependency;
- measurable improvement using a test/evaluation set.

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

## Next implementation task

**Begin with 8C: Graph-aware retrieval.**

Use the existing graph infrastructure to add bounded graph expansion as a complementary retrieval signal.

Do not implement temporal scoring, rank fusion, reranking, or explainability integration in the same change. Build and validate graph-aware candidate retrieval first.
