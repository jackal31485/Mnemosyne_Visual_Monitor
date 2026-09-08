# Phase 8 Completion Audit — Hybrid Retrieval

**Date:** 2026-09-07
**Status:** COMPLETE

## Scope

Phase 8 established Mnemosyne's governed hybrid retrieval architecture.

The phase combines:

- keyword/BM25 retrieval;
- semantic retrieval;
- graph-aware retrieval;
- temporal retrieval;
- reciprocal-rank fusion;
- optional local CrossEncoder reranking; and
- deterministic retrieval explainability.

The final integration adds a unified production orchestration layer and
exposes it through the read-only Athena API boundary.

## Completed implementation

### 8A — Keyword/BM25

Implemented:

- FTS5-backed keyword indexing;
- BM25 ranking;
- natural-language query handling;
- lifecycle filtering;
- profile filtering;
- deterministic ordering;
- provenance preservation.

### 8B — Semantic retrieval

Implemented:

- real local `all-MiniLM-L6-v2` embeddings;
- 384-dimensional normalized vectors;
- strict query-vector validation;
- governed semantic search;
- atomic embedding rebuild/migration;
- live migration of the collective corpus.

The live collective database was migrated from the deterministic placeholder
embedding implementation to real local MiniLM embeddings.

### 8C — Graph retrieval

Implemented bounded graph expansion over the governed collective graph.

Graph retrieval:

- operates from bounded keyword/semantic seed IDs;
- preserves lifecycle filtering;
- preserves profile scope;
- preserves provenance;
- performs discovery only;
- leaves fusion to the rank-fusion layer.

### 8D — Temporal retrieval

Implemented:

- explicit event-date retrieval;
- recency retrieval;
- event-date precision handling;
- deterministic temporal ordering;
- profile filtering;
- lifecycle filtering.

Natural-language temporal interpretation is intentionally not performed by
the retrieval layer.

### 8E — Rank fusion

Implemented deterministic reciprocal-rank fusion across:

- keyword;
- semantic;
- graph; and
- temporal channels.

Missing channels contribute zero.

Duplicate results within a channel do not consume additional rank positions.

### 8F — CrossEncoder reranking

Implemented optional local CrossEncoder reranking.

The reranker:

- consumes fused candidates;
- does not requery embeddings;
- operates only on a bounded candidate pool;
- retrieves source content through the MemoryGateway;
- does not modify collective state;
- preserves fused retrieval metadata;
- provides deterministic ordering.

The local CrossEncoder was validated on both CPU and GPU.

### 8G — Explainability

Implemented deterministic explanation of:

- keyword/BM25 rank and contribution;
- semantic rank and contribution;
- graph rank and contribution;
- temporal rank and contribution;
- fused score and rank;
- CrossEncoder score and rank;
- rank movement;
- source identity;
- provenance.

The explanation layer is read-only and does not access source memory content
or modify retrieval state.

## Final production orchestration

Implemented:

`src/retrieval/hybrid_search.py`

The `HybridRetrievalService` provides the unified production pipeline:

`Keyword/BM25 → Semantic → Graph → Temporal → RRF → Top-N → Optional CrossEncoder → Explainability → HybridResult`

The service:

- validates query input;
- validates retrieval limits;
- preserves profile scope;
- derives bounded unique graph seeds;
- keeps temporal retrieval explicitly opt-in;
- preserves lifecycle filtering through the underlying retrieval
  components;
- performs deterministic fusion;
- optionally performs bounded reranking;
- produces the unified explainability contract;
- performs no database writes.

## Athena integration

`AthenaAPI` now exposes:

`search_hybrid()`

The hybrid service is injected into Athena rather than being constructed per
query.

This prevents model-heavy dependencies from being loaded repeatedly.

The existing:

`search_semantic()`

and legacy:

`search_by_embedding()`

contracts remain intact.

The historical `search_by_embedding()` behavior was explicitly protected by
the existing Athena search test suite.

## Production smoke test

The complete pipeline was executed against the live collective corpus.

Verified environment:

- live collective database;
- 570-entry governed corpus;
- local MiniLM embedding model;
- local CrossEncoder model;
- CUDA execution;
- real keyword search;
- real semantic search;
- real graph expansion;
- RRF fusion;
- CrossEncoder reranking;
- explainability transformation.

Representative query:

`How did we fix the Phase 7 timeline API?`

The pipeline returned five unified hybrid results successfully.

The observed provenance lists for the tested entries were empty because
the underlying collective records themselves contained no provenance rows.
The orchestration layer therefore correctly preserved the underlying state
rather than fabricating provenance.

## Phase 8F evaluation evidence

The frozen 20-query evaluation demonstrated improvement from adding
CrossEncoder reranking to RRF:

| Metric | 8E RRF | 8F RRF + CrossEncoder | Delta |
|---|---:|---:|---:|
| Recall@5 | 0.4317 | 0.5192 | +0.0875 |
| Recall@10 | 0.5833 | 0.6208 | +0.0375 |
| MRR@5 | 0.4617 | 0.5267 | +0.0650 |
| MRR@10 | 0.4806 | 0.5400 | +0.0594 |

These results are engineering evidence from a frozen 20-query evaluation
set. They are not presented as statistically significant findings.

## Focused integration verification

The final focused Athena and hybrid orchestration regression produced:

- **24 passed**
- **1 skipped**

The skipped test intentionally documents that
`reference_time=None` is valid for recency retrieval and means the temporal
searcher should use the current time.

## Governance verification

Phase 8 preserves Mnemosyne's existing governance boundaries.

The retrieval pipeline does not:

- promote memories;
- revoke memories;
- modify collective lifecycle state;
- copy private source content into collective storage;
- bypass profile filtering;
- bypass promotion filtering;
- bypass revocation filtering;
- manufacture provenance;
- write to the collective database during query execution.

The MemoryGateway remains the source-memory access boundary for reranking.

## Architecture

The completed production architecture is:

```text
                    ┌──────────────────┐
                    │   User Query     │
                    └────────┬─────────┘
                             │
             ┌───────────────┼───────────────┐
             │               │               │
             ▼               ▼               ▼
          Keyword         Semantic         ...
           /BM25          /MiniLM
             │               │
             └───────┬───────┘
                     ▼
              Graph expansion
                     │
                     ▼
             Temporal channel
                     │
                     ▼
                RRF Fusion
                     │
                     ▼
              Bounded Top-N
                     │
                     ▼
          Optional CrossEncoder
                     │
                     ▼
              Explainability
                     │
                     ▼
               HybridResult
                     │
                     ▼
                Athena API
```

Temporal retrieval remains explicitly selectable rather than inferred from
the query.

Regression status

The final full-repository regression passed:

325 passed;
5 skipped;
4 warnings.

The four warnings are existing FastAPI `on_event` deprecation warnings and
are deferred to future maintenance.

Completion criteria
- [x] Keyword/BM25 implemented and tested
- [x] Real semantic embeddings implemented and migrated
- [x] Graph retrieval implemented and tested
- [x] Temporal retrieval implemented and tested
- [x] Rank fusion implemented and tested
- [x] CrossEncoder reranking implemented and evaluated
- [x] Explainability implemented and tested
- [x] Unified production orchestrator implemented
- [x] Athena hybrid API boundary implemented
- [x] Legacy Athena search contract preserved
- [x] Real-corpus end-to-end smoke test passed
- [x] Governance boundaries preserved
- [x] Documentation updated
- [x] Final full-repository regression passed
Exit decision

Phase 8 implementation is complete.

The final repository regression passed with 325 tests passed, 5 skipped,
and 4 warnings.

The warnings are existing FastAPI `on_event` deprecation warnings and are
deferred to future maintenance.

Phase 8: COMPLETE

Next phase: Phase 9 — Browser-facing hybrid retrieval integration.
