# Phase 8G Completion Audit — Explainability

**Date:** 2026-09-07
**Status:** COMPLETE

## Scope

Phase 8G established a deterministic explainability layer for the
hybrid retrieval results produced by Phase 8 rank fusion and optional
CrossEncoder reranking.

The objective was to make retrieval results capable of explaining:

> Why was this memory returned?

The explanation layer preserves retrieval evidence, ranking information,
and provenance without introducing new retrieval, persistence, or
governance behavior.

## Verified implementation

The completed Phase 8G implementation includes:

- `src/retrieval/explainability.py`
- `tests/test_explainability.py`

The implementation introduces the immutable:

`RetrievalExplanation`

contract.

## Explanation contract

`RetrievalExplanation` preserves:

- `entry_id`;
- `source_profile`;
- `origin_memory_id`;
- keyword/BM25 rank;
- semantic rank;
- graph rank;
- temporal rank;
- keyword contribution;
- semantic contribution;
- graph contribution;
- temporal contribution;
- fused score;
- fused rank;
- CrossEncoder score;
- reranker rank;
- rank movement;
- provenance.

No source-memory content is copied into the explanation contract.

## Fused-result explanation

`explain_fused()` accepts an ordered `FusedResult` sequence.

Fused rank is assigned from the actual supplied sequence position.

Ranks are not inferred from fused scores.

This ensures the explanation represents the ordering actually produced by
rank fusion rather than independently recomputing ranking behavior.

## Reranked-result explanation

`explain_reranked()` accepts:

1. the ordered reranked result sequence; and
2. the original ordered fused-result sequence.

The second sequence is required because `RerankedResult` intentionally does
not contain an independent `fused_rank`.

The explanation layer reconstructs the original fused position by
`entry_id`.

Rank movement is calculated as:

`rank_change = fused_rank - reranker_rank`

Therefore:

- positive values represent upward movement;
- negative values represent downward movement;
- zero represents no movement.

The supplied `reranker_rank` is validated against the actual result
sequence.

A reranked entry that does not exist in the supplied fused candidate
sequence is rejected with a controlled `ValueError`.

## Architectural boundary

The explainability implementation is intentionally a pure transformation
layer.

It does not:

- query the collective database;
- query private profile databases;
- access source memory content;
- generate embeddings;
- perform retrieval;
- modify retrieval scores;
- modify collective state;
- promote or revoke memories;
- make trust decisions;
- make governance decisions.

The layer consumes already-produced retrieval results and exposes their
existing evidence in a structured form.

## Provenance verification

Provenance is carried through unchanged from the existing retrieval
contracts.

The explanation layer does not reconstruct or reinterpret provenance.

This preserves Mnemosyne's existing governance boundary:

- collective entries retain references to source memories;
- source profile identity remains available;
- provenance remains available;
- private source-memory content is not copied into the collective
  knowledge representation.

## Testing

Focused explainability coverage verifies:

- fused sequence ranking;
- score-independent rank assignment;
- all four retrieval-channel ranks;
- all channel contributions;
- optional/unranked channels;
- fused score preservation;
- CrossEncoder score preservation;
- source identity;
- source profile;
- origin memory ID;
- provenance;
- reranker rank validation;
- missing fused-entry validation;
- deterministic repeated output;
- empty-input handling.

Focused Phase 8 retrieval regression:

- **63 passed**
- `tests/test_explainability.py`
- `tests/test_rank_fusion.py`
- `tests/test_reranker.py`
- `tests/test_cross_encoder.py`
- `tests/test_keyword_search.py`

## Repository regression

The full repository regression following Phase 8F produced:

- **298 passed**
- **4 skipped**
- **4 warnings**

The warnings are the existing FastAPI `on_event` deprecation warnings.

They are non-blocking and do not indicate a Phase 8 retrieval or
explainability failure.

## Production integration boundary

Phase 8G does not claim that Mnemosyne now has a single production
hybrid-retrieval orchestrator.

The repository currently contains the individual retrieval components:

- keyword/BM25;
- semantic;
- graph;
- temporal;
- rank fusion;
- optional CrossEncoder reranking;
- explainability.

The Phase 8F evaluation harness composes these components to evaluate the
retrieval architecture, but it does not replace the production retrieval
API with a unified orchestrator.

This boundary is intentional and must remain explicit.

The completed explainability layer is designed to consume the results of
that future orchestration without requiring changes to the existing
retrieval contracts.

## Governance verification

Phase 8G introduces no persistence or governance mutation.

The implementation does not bypass:

- profile isolation;
- promotion state;
- revocation;
- provenance;
- source-memory boundaries.

The explanation layer operates only on results that have already passed
through the existing governed retrieval components.

## Completion criteria

Phase 8G is complete because:

- [x] deterministic explanation contract implemented;
- [x] fused ranking preserved;
- [x] reranked ranking preserved;
- [x] rank movement exposed;
- [x] lexical evidence preserved;
- [x] semantic evidence preserved;
- [x] graph evidence preserved;
- [x] temporal evidence preserved;
- [x] fused score preserved;
- [x] CrossEncoder score preserved;
- [x] provenance preserved;
- [x] source identity preserved;
- [x] invalid rank state rejected;
- [x] missing fused candidate rejected;
- [x] focused tests pass;
- [x] retrieval regression passes;
- [x] documentation updated;
- [x] production-orchestration boundary explicitly documented.

## Non-blocking limitations

Phase 8G does not expose a unified hybrid-retrieval service/API.

A future integration phase may compose:

`Keyword/BM25 → Semantic → Graph → Temporal → RRF → Top-N → CrossEncoder → Explainability`

into a single production retrieval contract.

That work is intentionally outside the Phase 8G explainability implementation
and should be designed and validated separately rather than being implied by
the completion of the individual retrieval components.

## Exit decision

Phase 8G satisfies its implementation and verification requirements.

The explainability layer is deterministic, read-only, provenance-preserving,
and independent of database and source-memory access.

**Phase 8G: COMPLETE**

**Next step: Phase 8 final integration/orchestration review**
