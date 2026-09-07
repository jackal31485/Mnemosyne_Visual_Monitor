# Phase 8 — Hybrid Retrieval

**Status:** IN PROGRESS — 8A COMPLETE  
**Started:** 2026-09-07  
**Current:** Phase 8B — Semantic Retrieval Hardening  
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

Review the current vector retrieval implementation and define a stable retrieval contract.

Verify:

- embedding availability;
- normalization;
- similarity calculation;
- filtering;
- result limits;
- deterministic tie handling;
- provenance.

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

**Begin with 8B: Semantic retrieval hardening.**

Review the existing semantic/vector retrieval implementation and establish a stable retrieval contract before integrating it with the Phase 8A lexical layer.

Do not implement graph, temporal, fusion, or reranking in the same change. Build and validate the semantic retrieval foundation first.
