# Phase 15 — Governance Invariants

## 1. Retrieval Eligibility

Only knowledge already eligible under Mnemosyne governance may enter the active retrieval result set.

Promoted and non-revoked state remains authoritative.

## 2. No Governance Bypass

Query classification, routing, scoring, and reranking are retrieval mechanisms.

None of them may authorize, adopt, revoke, or synchronize knowledge.

## 3. Profile Isolation

Retrieval optimization must respect profile ownership and existing profile isolation.

Cross-profile retrieval must occur only through knowledge already made eligible by the governed architecture.

## 4. Provenance Preservation

Optimization must never discard source profile, source memory, collective knowledge, evidence, observation, or derivation identifiers required for provenance.

## 5. Evidence Preservation

Evidence remains attached to the knowledge representation being retrieved.

A ranking optimization must not replace evidence with an opaque score.

## 6. Temporal Integrity

Temporal evidence and temporal scope remain authoritative.

Ranking may use temporal relevance but must not rewrite temporal relationships or precision.

## 7. Revocation Integrity

Revoked knowledge must not remain retrievable as current governed knowledge merely because it ranked highly before revocation.

Historical audit information may remain preserved separately.

## 8. Conflict Visibility

Conflicting knowledge must not be silently collapsed merely to improve ranking.

Where conflicting representations are eligible, retrieval behavior must remain explainable.

## 9. Determinism

Governed decisions and testable retrieval paths should be deterministic where the architecture requires reproducibility.

Nondeterministic model behavior must not be used to conceal governance behavior.

## 10. Explainability

Retrieval diagnostics must expose meaningful signals sufficient to understand why candidates were selected or ordered.

A single opaque score is insufficient as the only explanation.

## 11. No Raw Private Content Leakage

Retrieval optimization must not introduce raw private memory content into transfer metadata, diagnostics, governance records, or unrelated shared representations.

## 12. No Implicit Learning

Retrieval does not create learned knowledge.

A frequently retrieved item does not automatically become promoted, transferred, consolidated, or adopted.

## 13. No Implicit Synchronization

Improved retrieval must not create a hidden profile-to-profile synchronization channel.

## 14. Safe Fallbacks

Failures in classification, retrieval, scoring, or reranking must fall back to a previously validated governed path rather than bypassing eligibility checks.

## 15. Phase Boundary

Phase 15 is limited to advanced retrieval optimization.

Distributed LAN federation, unrestricted shared memory, autonomous learning, and later architectural capabilities remain outside this phase.

## 16. Evaluation Integrity

Evaluation metrics describe retrieval behavior.

They do not authorize a candidate, override governance, or establish that a result is correct merely because it scores highly.

## Final Principle

Retrieval optimization may change how governed knowledge is found and ordered. It must never change what governance permits Mnemosyne to retrieve.
