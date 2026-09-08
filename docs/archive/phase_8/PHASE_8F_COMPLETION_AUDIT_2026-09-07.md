# Phase 8F Completion Audit — CrossEncoder Reranking

**Date:** 2026-09-07
**Status:** COMPLETE

## Scope

Phase 8F added an optional, local CrossEncoder reranking stage after Phase 8E rank fusion.

The objective was to improve ordering of an already-authorized hybrid retrieval candidate set without weakening Mnemosyne's governance, provenance, profile-isolation, deterministic-behavior, or local-first requirements.

The intended retrieval sequence is:

```text
Keyword / BM25
        ↓
Semantic
        ↓
Graph
        ↓
Temporal
        ↓
RRF rank fusion
        ↓
Top-N candidate set
        ↓
Optional CrossEncoder reranking
        ↓
Final results
        ↓
Explainability
Phase 8B prerequisite correction

During Phase 8B validation, the existing embedding path was found to use a deterministic placeholder rather than the intended real local semantic embedding model.

This was corrected before Phase 8F evaluation.

The live collective database was migrated to real local all-MiniLM-L6-v2 embeddings:

eligible entries: 570
embeddings updated: 570
failures: 0
valid embeddings after migration: 570
invalid embeddings: 0
sampled embedding fingerprints changed: 10/10

The migration preserved the existing collective lifecycle and governance model.

Verified Phase 8F capabilities

Phase 8F provides:

optional CrossEncoder reranking;
bounded candidate reranking;
configurable candidate limit;
configurable final top_k;
query-time scoring only;
source-content retrieval through MemoryGateway;
preservation of fused retrieval metadata;
reranker score and rank;
provenance preservation;
deterministic score ordering with entry_id tie-breaking;
controlled failure when source memory cannot be retrieved;
validation of score count and finite score values;
no collective database writes;
no bypass of promotion/revocation filtering;
no expansion of the candidate pool;
no re-querying of embeddings.

The reranker consumes FusedResult objects produced by Phase 8E rather than independently reconstructing retrieval candidates.

CrossEncoder implementation

The production adapter is:

src/retrieval/cross_encoder.py

It uses the locally installed:

cross-encoder/ms-marco-MiniLM-L6-v2

stored at:

models/cross-encoder-ms-marco-MiniLM-L6-v2

The adapter uses Sentence Transformers and PyTorch and supports both CPU and CUDA execution.

The model is loaded with local-only behavior after installation. No runtime network dependency is required.

The model is an English/MS-MARCO passage-ranking model. This limitation is explicit and is not represented as multilingual capability.

Reranking service

The reranking implementation is:

src/retrieval/reranker.py

The service:

receives the frozen candidate ordering from Phase 8E;
applies the configured candidate limit;
retrieves source memory content through MemoryGateway;
constructs (query, content) CrossEncoder pairs;
obtains CrossEncoder scores;
validates the returned score count and values;
deterministically orders candidates by reranker score;
applies the requested final top_k;
preserves the original fused retrieval metadata and provenance.

The CrossEncoder therefore acts strictly as a query-time ordering layer.

It does not alter stored memories, embeddings, collective lifecycle state, provenance, or revocation state.

Architectural verification

The Phase 8F implementation preserves the project's established architectural boundaries.

Profile isolation

Private profile memories remain isolated.

Reranking obtains source content through the MemoryGateway rather than directly merging or copying private databases into the collective store.

Collective governance

Only the candidate set already produced by governed retrieval is reranked.

The CrossEncoder does not promote, revoke, validate, or otherwise alter collective entries.

Provenance

Reranked results preserve the provenance and channel metadata established by earlier retrieval stages.

Determinism

Deterministic ordering is retained through explicit tie-breaking by entry_id.

Local-first operation

The CrossEncoder model is stored locally and can run on CPU or CUDA without a mandatory cloud service.

Candidate-bound reranking

Reranking cannot discover additional entries. It can only reorder the bounded candidate set supplied by Phase 8E.

Testing

Focused Phase 8F tests cover both the CrossEncoder adapter and reranking service.

The CrossEncoder adapter test suite contains:

9 passed

The reranker test suite contains:

12 passed

The combined focused validation with the keyword-search regression suite produced:

38 passed
3.06 seconds

Coverage includes ranking behavior, candidate limits, top_k, pair construction, metadata preservation, provenance, deterministic ties, empty candidates, missing source memories, invalid limits, empty queries, score-count mismatch, and non-finite scores.

Runtime validation

The local CrossEncoder was validated on both CPU and CUDA.

The same candidate ordering was produced across devices, with only small floating-point score differences.

The model was loaded from the local model directory and did not require network access at query time.

Frozen evaluation methodology

A frozen Phase 8F evaluation set was created at:

docs/phase_8f_evaluation_set.json

The evaluation contains:

20 queries
frozen relevance judgments;
current Mnemosyne corpus only;
explicit exclusion of Phase 8 memories;
identical candidate generation for the baseline and reranked systems.

This distinction is important because ChatGPT/FriDAY memories have not yet been synchronized into Mnemosyne. Phase 8 memories therefore do not exist in the evaluated corpus and were not used to construct the benchmark.

The benchmark compares:

8E baseline

Keyword + Semantic + Graph + Temporal
        ↓
RRF
        ↓
Top 10

against:

8F

Keyword + Semantic + Graph + Temporal
        ↓
RRF
        ↓
Top 20 candidates
        ↓
CrossEncoder
        ↓
Top 10

Both systems therefore receive the same candidate-generation process.

The evaluation harness is:

scripts/evaluate_phase_8f.py

The harness is evaluation-only and does not modify the collective database.

Evaluation artifacts

The evaluation produced:

docs/phase_8f_evaluation_set.json
docs/phase_8f_evaluation_results.json
scripts/evaluate_phase_8f.py

The evaluation result artifact contains per-query rankings, relevance comparisons, and aggregate metrics.

Evaluation results

The frozen 20-query evaluation produced the following aggregate results:

Metric	Phase 8E RRF	Phase 8F RRF + CrossEncoder	Delta
Recall@5	0.4317	0.5192	+0.0875
Recall@10	0.5833	0.6208	+0.0375
MRR@5	0.4617	0.5267	+0.0650
MRR@10	0.4806	0.5400	+0.0594

The CrossEncoder therefore improved all four measured aggregate metrics.

The strongest aggregate gain was:

Recall@5: +0.0875

followed by:

MRR@5: +0.0650

These results provide engineering evidence that the reranking stage improves retrieval ordering on the frozen evaluation corpus.

They should not be interpreted as statistical significance. The benchmark contains only 20 queries and has a manually frozen relevance judgment set.

Per-query behavior

The evaluation also demonstrated that reranking is not uniformly beneficial for every query.

Examples include:

Phase 7 timeline repair improved substantially;
collective architecture retrieval improved;
isolation and reference-related queries improved;
LAN discovery retrieval improved;
some queries experienced lower reciprocal rank after reranking;
some relevant entries remained outside the candidate set entirely.

These regressions were retained rather than tuning the CrossEncoder around individual queries.

This is intentional.

The evaluation is evidence for the usefulness of the reranking stage, not a justification for overfitting the reranker to a small benchmark.

Candidate-generation limitation

Several weak queries demonstrate an important architectural boundary.

A CrossEncoder cannot rerank a relevant memory that was never included in the Phase 8E candidate pool.

Therefore, remaining failures such as weak retrieval for some embedding-model and architectural-principle queries are not automatically evidence of a CrossEncoder defect.

They may instead indicate limitations in:

keyword matching;
semantic retrieval;
graph expansion;
temporal retrieval;
rank-fusion coverage;
candidate-generation breadth;
relevance judgments.

These issues should be addressed in later retrieval or knowledge-model phases rather than by indiscriminately increasing reranking complexity.

Production orchestration boundary

Phase 8F completes the reranking component and its evaluation, but it does not claim that a single production hybrid-retrieval orchestrator is already complete.

The evaluation harness composes the existing retrieval components:

Keyword
Semantic
Graph
Temporal
   ↓
RRF
   ↓
CrossEncoder

There is currently no single production service that formally exposes this entire pipeline as one unified retrieval API.

That remains an architectural integration task and must not be silently represented as complete merely because the individual retrieval components and evaluation harness can be composed.

Governance verification

Phase 8F does not weaken the project's governance invariants.

The implementation preserves:

profile isolation;
local-first operation;
SQLite-first persistence;
mediation / air-lock boundaries;
explicit collective promotion;
provenance;
revocation;
controlled memory access;
deterministic retrieval behavior;
auditability;
no raw private-memory leakage into the collective database;
no automatic trust-to-adoption behavior;
no destructive consolidation.

The CrossEncoder operates strictly after governed candidate generation.

Completion criteria

Phase 8F satisfies its completion requirements:

 CrossEncoder reranking implemented.
 Local/offline-capable model validated.
 CPU execution validated.
 CUDA execution validated.
 Candidate-limit enforcement implemented.
 Deterministic tie behavior implemented.
 MemoryGateway source-content access implemented.
 Provenance and fused metadata preserved.
 Missing-memory failure handled deterministically.
 No collective database mutation during reranking.
 Focused test coverage complete.
 Frozen evaluation set created.
 Phase 8 memories excluded from evaluation.
 Baseline and reranked systems evaluated against the same candidate generation.
 Recall@5 and Recall@10 measured.
 MRR@5 and MRR@10 measured.
 Measurable improvement demonstrated.
 Individual regressions documented rather than overfit.
 Candidate-generation limitations documented.
 Production orchestration boundary documented.
Non-blocking limitations

The following do not block Phase 8F completion:

The CrossEncoder model is optimized for English/MS-MARCO passage ranking and should not be assumed to provide multilingual semantic equivalence.
The benchmark contains only 20 queries and should be expanded in a future evaluation pass if larger representative corpora become available.
The current architecture still requires a formal production hybrid-retrieval orchestration layer.
Some retrieval weaknesses originate before reranking and require future improvements to candidate generation rather than CrossEncoder tuning.
Existing FastAPI lifecycle deprecation warnings remain a separate maintenance concern.
Exit decision

Phase 8F is complete.

The implementation provides a bounded, optional, deterministic, locally executable CrossEncoder reranking layer that operates only on already-authorized retrieval candidates.

The frozen evaluation demonstrates improvement across all four aggregate retrieval metrics:

Recall@5;
Recall@10;
MRR@5;
MRR@10.

The evaluation also clearly identifies the remaining boundary between candidate generation and candidate reranking, preventing the CrossEncoder from being treated as a solution for retrieval failures occurring upstream.

The Phase 8F implementation and evidence are therefore sufficient to advance to:

Phase 8G — Explainability
