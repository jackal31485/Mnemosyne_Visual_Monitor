# Phase 9 — Browser-Facing Hybrid Retrieval Integration

**Status:** COMPLETE  
**Started:** 2026-09-09  
**Completed:** 2026-09-09  
**Previous phase:** Phase 8 — Hybrid Retrieval  
**Next phase:** Phase 10 — Entity & Relationship Intelligence

## Objective

Expose the completed Phase 8 governed hybrid retrieval pipeline through the
Mnemosyne Browser without weakening existing governance, provenance,
profile-isolation, lifecycle, or source-memory boundaries.

Phase 8 provides:

Query
  → BM25
  → Semantic
  → Graph expansion
  → Optional temporal signal
  → RRF fusion
  → Optional local CrossEncoder
  → Explainability
  → HybridResult

Phase 9 makes that capability operationally visible and usable through the
Browser.

## 9A — Browser API boundary

Implemented:

- `GET /api/search/hybrid`
- Query, profile, date-window, result-count, candidate-limit, and rerank
  controls
- Date filters mapped to governed event-date retrieval
- Pydantic response contract for `HybridResult`
- Explicit CrossEncoder availability reporting
- Athena API remains the domain boundary for hybrid search
- Model-heavy dependencies constructed once through an application-level
  cached retrieval service
- Optional CrossEncoder failure does not disable base hybrid retrieval

The endpoint does not write collective state and does not bypass lifecycle
authorization.

### Profile identity resolution

Browser-facing local profile names such as `athena` are resolved at the
Athena read-only API boundary to the governed qualified collective identity,
for example:

`agent-id:athena`

Qualified identities are preserved unchanged. Ambiguous short profile names
are rejected rather than silently selecting an identity.

The underlying retrieval/searchers continue to operate on their authoritative
qualified collective identities.

## 9B — Browser search surface

Implemented:

- Dedicated Hybrid Search visualization mode
- Explicit Hybrid Search action from the Browser header
- Current search/profile/date filters forwarded to the hybrid API
- Result cards exposing fused rank and score
- BM25, semantic, graph, temporal, and RRF explainability metadata
- CrossEncoder score/rank movement when reranking is available
- Provenance count visibility
- Result inspection through the existing Inspector/source-memory flow
- Hybrid Search lifecycle cleanup when leaving the view
- Clear Filters correctly returns to the normal visualization state
- Existing visualization modes remain functional
- Existing client-side global filtering behavior preserved for legacy
  graph/table/information views

## 9C — Production validation fixes

Real FastAPI/AnyIO execution exposed a SQLite thread-affinity issue caused by
the cached retrieval service retaining a SQLite connection across worker
threads.

The retrieval layer was corrected so that:

- ML/model-heavy components remain long-lived and cached
- SQLite search connections are created per search operation
- No `check_same_thread=False` workaround is required
- Concurrent retrieval calls are covered by regression testing

This preserves the performance benefit of cached retrieval models without
sharing thread-affine SQLite connections.

## Governance boundary

Browser receives collective retrieval results only.

Promotion, revocation, provenance, source identity, retrieval authorization,
and source-memory access remain authoritative outside the Browser.

Source memory content is fetched only on explicit inspection through the
existing controlled memory gateway/API path.

Phase 9 does not copy private source-memory content into `collective.db`.

## Testing and validation

### Automated validation

Final full repository regression:

- **331 passed**
- **5 skipped**
- **4 warnings**

The warnings are existing FastAPI `on_event()` deprecation warnings and do
not represent Phase 9 test failures.

Additional validation:

- Hybrid search route tests
- Athena hybrid-search delegation tests
- Qualified/short profile identity tests
- Ambiguous profile rejection test
- Concurrent keyword-search thread-safety regression test
- Browser JavaScript syntax validation with `node --check`
- `git diff --check`

### Live API validation

Validated through the running FastAPI application:

- Base hybrid search
- Profile-filtered hybrid search
- Date-window filtering
- CrossEncoder-enabled reranking
- Result explainability
- Collective entry → source-memory ID mapping
- Athena profile resolution

The production Athena profile filter returned results with the expected
qualified source identity:

`3de1e96e-70e5-49e0-a128-529c55071b2b:athena`

### Live Browser validation

Validated in the Browser against the live local service:

- Hybrid Search action
- Query `timeline API`
- Athena profile filtering
- Hybrid Search visualization
- Ten returned results
- BM25/semantic/graph/CrossEncoder metadata
- Result inspection
- Source-memory content inspection through the existing controlled path
- Leaving Hybrid Search correctly removes the Hybrid Search center pane
- Clear Filters correctly exits Hybrid Search when appropriate

## Exit criteria

- [x] Browser hybrid-search API exists
- [x] API uses the Phase 8 `AthenaAPI.search_hybrid()` boundary
- [x] Model-heavy dependencies are not recreated per query
- [x] SQLite retrieval connections are thread-safe
- [x] Profile/date filters are governed by the retrieval service
- [x] Browser profile names resolve to qualified collective identities
- [x] Explainability metadata reaches the Browser
- [x] Browser exposes a dedicated Hybrid Search view
- [x] Search results can open the existing Inspector/source-memory path
- [x] Existing Browser views remain functional
- [x] Hybrid Search lifecycle cleanup is correct
- [x] Focused automated tests pass
- [x] Full repository regression passes in the real project venv
- [x] Live API corpus smoke test passes
- [x] Live Browser smoke test passes
- [x] Documentation and authoritative roadmap reconciled
- [x] Phase 9 completion audit written and archived

## Phase 9 outcome

Phase 9 is complete.

Mnemosyne's Phase 8 governed hybrid retrieval engine is now exposed through
the Browser as an operational search surface while preserving the existing
mediation, provenance, lifecycle, profile-isolation, and source-memory
boundaries.

The project is ready to begin Phase 10: **Entity & Relationship
Intelligence**.
