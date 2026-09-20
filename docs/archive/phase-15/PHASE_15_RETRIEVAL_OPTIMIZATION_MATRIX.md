# Phase 15 — Retrieval Optimization Matrix

## Phase Scope Matrix

| Area | Required | Boundary |
| --- | --- | --- |
| Query classification | Yes | Routing only |
| Retrieval routing | Yes | Must preserve governance |
| BM25 / lexical retrieval | Yes | Candidate generation |
| Semantic retrieval | Yes | Candidate generation |
| Hybrid retrieval | Yes | Inspectable combined signals |
| Candidate generation | Yes | No authorization |
| Governance filtering | Yes | Promoted and non-revoked boundary |
| Reranking | Yes | Eligible candidates only |
| Evidence signals | Yes | Must preserve evidence |
| Temporal signals | Yes | Must preserve temporal meaning |
| Multilingual retrieval | Evaluate | Only where supported and justified |
| Retrieval diagnostics | Yes | Explain ranking behavior |
| Retrieval persistence redesign | No | Only if separately authorized |
| Cross-profile synchronization | No | Phase 14 boundary remains authoritative |
| Distributed LAN federation | No | Future phase |
| Autonomous memory mutation | No | Outside retrieval optimization |

## Pipeline Matrix

| Stage | Input | Output | Governance Requirement |
| --- | --- | --- | --- |
| Query normalization | User query | Normalized query | No memory mutation |
| Classification | Normalized query | Retrieval intent | Routing only |
| Routing | Query + intent | Retrieval strategy | Must preserve profile boundary |
| Candidate generation | Query + strategy | Candidate set | Governed sources only |
| Governance filtering | Candidate set | Eligible candidates | Promoted and non-revoked |
| Scoring | Eligible candidates | Relevance signals | Inspectable |
| Reranking | Scored candidates | Ordered candidates | No governance bypass |
| Projection | Ordered candidates | API/UI results | No raw private content leakage |

## Evaluation Matrix

| Dimension | Validation |
| --- | --- |
| Exact retrieval | Exact and near-exact queries |
| Lexical retrieval | BM25/keyword cases |
| Semantic retrieval | Meaning-preserving wording changes |
| Hybrid retrieval | Cases where lexical and semantic signals differ |
| Reranking | Candidate ordering and tie behavior |
| Temporal retrieval | Time-qualified queries |
| Entity retrieval | Entity-focused queries |
| Relationship retrieval | Relationship-focused queries |
| Multilingual retrieval | Supported-language test cases |
| Governance | Promoted/non-revoked filtering |
| Provenance | Source identifiers remain intact |
| Regression | Existing retrieval tests remain passing |
| Diagnostics | Ranking signals remain inspectable |
| Performance | Latency measured where meaningful |

## Failure Matrix

| Failure | Required Behavior |
| --- | --- |
| Query classification failure | Fall back safely; do not bypass governance |
| Empty candidate set | Return governed empty result |
| Conflicting ranking signals | Preserve deterministic/inspectable ordering |
| Revoked candidate | Exclude from current retrieval |
| Unpromoted candidate | Exclude from current retrieval |
| Missing provenance | Do not expose as a valid governed result |
| Temporal ambiguity | Preserve uncertainty |
| Unsupported language | Use safe fallback behavior |
| Reranker failure | Fall back to validated ranking path |
| Diagnostic failure | Do not conceal governance state |

## Phase Boundary

Phase 15 ends at optimized governed retrieval.

It does not authorize distributed federation, new learning lifecycles, profile synchronization, or unrestricted memory sharing.
