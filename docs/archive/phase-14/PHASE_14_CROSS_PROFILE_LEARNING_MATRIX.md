# Phase 14 — Cross-Profile Learning & Controlled Transfer Matrix

**Status:** CURRENT — READY TO BEGIN
**Date:** 2026-09-16

> **Implementation status:** PLANNED — this matrix is the Phase 14 governance
> and implementation contract.

---

## 1. Transfer Lifecycle Matrix

| State | Meaning | Destination modified? | Auditable? |
|---|---|---:|---:|
| AVAILABLE | Knowledge can be inspected | No | Yes |
| ELIGIBLE | Knowledge satisfies transfer prerequisites | No | Yes |
| CANDIDATE | Transfer proposed | No | Yes |
| AUTHORIZED | Transfer explicitly permitted | No | Yes |
| ADOPTED | Destination representation created | Yes | Yes |
| STALE | Adopted representation requires review/refresh | Existing state only | Yes |
| SUPERSEDED | Replaced by a newer version | Historical state retained | Yes |
| REVOKED | Transfer/adoption invalidated | Existing state retained for audit | Yes |
| REJECTED | Transfer explicitly declined | No | Yes |

---

## 2. Core Data Objects

| Object | Owner | Purpose |
|---|---|---|
| Source Knowledge | Collective/source governance | Knowledge eligible for consideration |
| Transfer Candidate | Mediation/transfer layer | Proposed source→destination transfer |
| Authorization | Governance layer | Explicit permission |
| Transfer Record | Audit/transfer layer | Immutable transfer history |
| Destination Learned Model | Destination profile | Profile-specific adopted knowledge |
| Revocation Event | Governance layer | Invalidates dependent state |

---

## 3. Required Provenance

| Field | Required |
|---|---:|
| Source profile | Yes |
| Destination profile | Yes |
| Source knowledge ID | Yes |
| Transfer candidate ID | Yes |
| Transfer record ID | Yes |
| Source memory IDs | Yes where applicable |
| Observation IDs | Yes where applicable |
| Evidence IDs | Yes |
| Mental-model ID | When applicable |
| Authorization ID | Yes |
| Derivation method | Yes |
| Created/adopted timestamps | Yes |
| Version | Yes |
| Revocation state | Yes |

---

## 4. Governance Rules

| Rule | Phase 14 Requirement |
|---|---|
| Profile isolation | Mandatory |
| Raw private content transfer | Prohibited |
| Collective visibility = adoption | Prohibited |
| Candidate = adoption | Prohibited |
| Explicit authorization | Mandatory |
| Provenance | Mandatory |
| Evidence preservation | Mandatory |
| Source mutation | Prohibited |
| Destination ownership | Mandatory |
| Audit deletion | Prohibited |
| Revocation propagation | Mandatory |
| Conflict suppression | Prohibited |
| Implicit synchronization | Prohibited |
| Unrestricted profile-to-profile writes | Prohibited |
| Athena work | Not required |

---

## 5. Candidate Evaluation Matrix

| Signal | Purpose |
|---|---|
| Evidence quality | Determine strength of source knowledge |
| Novelty | Determine whether destination already knows equivalent information |
| Entity overlap | Determine subject applicability |
| Relationship overlap | Determine structural applicability |
| Temporal compatibility | Determine whether knowledge applies now |
| Destination knowledge gap | Identify potential benefit |
| Contradiction state | Detect incompatible destination knowledge |
| Source profile provenance | Preserve origin |
| Collective lifecycle | Ensure knowledge remains valid |
| Revocation state | Prevent invalid transfer |
| Prior transfer history | Prevent redundant or conflicting adoption |

---

## 6. Adoption Decision Matrix

| Condition | Result |
|---|---|
| Missing source provenance | REJECT |
| Missing evidence | REJECT |
| Source revoked | REJECT |
| Destination unauthorized | REJECT |
| Transfer unauthorized | REJECT |
| Strong destination contradiction | REVIEW_REQUIRED / CONFLICT |
| Knowledge already adopted | KEEP_EXISTING / NO_OP |
| Valid and applicable | ADOPT |
| Temporally expired | REJECT / STALE |
| Source superseded | Refresh/re-evaluate |
| Provenance chain broken | REJECT |

---

## 7. Browser/API Surface Matrix

| Surface | Required Information |
|---|---|
| Transfer list | Source, destination, state, knowledge ID |
| Transfer detail | Full provenance and lifecycle |
| Candidate view | Why candidate exists |
| Authorization view | Who/what authorized it |
| Evidence view | Supporting evidence IDs |
| Conflict view | Destination conflicts |
| Adoption view | Destination-derived representation |
| Temporal view | Applicability interval |
| Revocation view | Dependency chain and invalidation |
| Version view | Historical destination versions |

---

## 8. Testing Matrix

| Area | Required Test |
|---|---|
| Candidate generation | Deterministic candidate |
| Source isolation | No source mutation |
| Destination isolation | Unauthorized destination unchanged |
| Authorization | Unauthorized transfer rejected |
| Provenance | Complete source→destination chain |
| Evidence | Supporting evidence preserved |
| Conflict | Conflicts remain visible |
| Temporal | Incompatible transfer rejected |
| Adoption | Explicit adoption required |
| Revocation | Dependent state invalidated |
| Audit | Historical record retained |
| Privacy | Raw private content excluded |
| Rebuild | Same inputs produce same candidate |
| API | Governance fields exposed |
| Browser | Transfer state visibly distinguished |

---

## 9. Phase Deliverable Matrix

| Deliverable | Expected Validation |
|---|---|
| 14A Transfer contract | Unit tests |
| 14B Candidate generation | Unit + integration |
| 14C Applicability/benefit analysis | Numerical/decision tests |
| 14D Authorization | Governance tests |
| 14E Controlled adoption | Integration tests |
| 14F Conflict handling | Governance + lifecycle tests |
| 14G Revocation/rollback | Lifecycle tests |
| 14H API/Browser | Route/UI tests if implemented |
| 14I Final validation | Full regression |

---

## 10. Fundamental Rule

> **Cross-profile learning is a controlled transfer operation, not a side effect of
> collective retrieval.**

The transfer chain must remain reconstructable from destination state back to
the source evidence.
