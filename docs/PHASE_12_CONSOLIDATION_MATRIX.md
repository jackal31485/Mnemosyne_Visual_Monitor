# Phase 12 — Consolidation Matrix

**Phase:** 12 — Evidence Consolidation & Memory Synthesis  
**Status:** READY TO BEGIN  
**Purpose:** Define deterministic, evidence-preserving consolidation behavior

---

# 1. Consolidation Decision Matrix

| Condition | Similarity | Evidence | Temporal State | Contradiction | Default Result |
|---|---:|---:|---:|---:|---|
| Clearly unrelated | Low | Any | Any | Any | Keep separate |
| Near duplicate | High | Compatible | Compatible | None | Consolidation candidate |
| Same fact, different wording | High | Corroborating | Compatible | None | Candidate |
| Same fact, different profiles | High | Independent | Compatible | None | Candidate |
| Same fact, stronger evidence | High | Compatible | Compatible | None | Candidate + evidence weighting |
| Same subject, different state | High | Valid | Different | None | Do not merge automatically |
| Historical change | High | Valid | Different periods | None | Preserve temporal distinction |
| Direct contradiction | High | Valid | Same period | Yes | Review / conflict |
| One source revoked | High | Partial | Compatible | None | Recalculate support |
| All supporting evidence revoked | High | Invalid | Any | Any | Review / invalidate current support |
| Similar wording, different entities | High | Valid | Compatible | Entity mismatch | Keep separate |
| Similar semantics, incompatible relationships | High | Valid | Compatible | Relationship mismatch | Review |
| Insufficient provenance | Any | Incomplete | Any | Any | Reject consolidation |
| Derived statement only | Any | No direct evidence | Any | Any | Do not treat as evidence |

---

# 2. Evidence State Matrix

| Evidence State | May Participate? | Current Support? | Historical Trace? |
|---|---:|---:|---:|
| Promoted + active | Yes | Yes | Yes |
| Promoted + revoked | No | No | Yes |
| Unpromoted | No | No | Yes if stored |
| Missing source memory | No | No | Preserve reference if available |
| Profile mismatch | No | No | Audit |
| Invalid lifecycle | No | No | Audit |
| Valid but contradictory | Yes | Conditional | Yes |

---

# 3. Temporal Compatibility Matrix

| Observation A | Observation B | Temporal Relationship | Default |
|---|---|---|---|
| Same state | Same state | Same period | Candidate |
| Same state | Same state | Different periods | Candidate with temporal evidence |
| State A | State B | Sequential | Preserve as change |
| State A | State B | Overlapping | Conflict/review |
| State A | Unknown | Any | Do not infer |
| Missing time | Known time | Any | Do not invent bounds |
| Recurring event | Same recurring event | Compatible recurrence | Candidate |
| Historical fact | Current fact | Different validity | Preserve temporal distinction |

---

# 4. Entity Compatibility Matrix

| Entity Relationship | Result |
|---|---|
| Same canonical entity | Candidate |
| Known alias | Candidate |
| Different canonical entities | Keep separate |
| Unresolved entity | Review |
| Entity revoked/inactive | Revalidate |
| Same entity + same relationship | Candidate |
| Same entity + different relationship | Analyze independently |

---

# 5. Provenance Matrix

Every consolidation must preserve:

| Provenance Element | Required |
|---|---:|
| Source profile | Yes |
| Source memory ID | Yes where available |
| Observation ID | Yes |
| Evidence ID | Yes where applicable |
| Entity IDs | Where applicable |
| Relationship IDs | Where applicable |
| Temporal evidence | Where applicable |
| Consolidation decision | Yes |
| Consolidation timestamp | Yes |
| Decision reason | Yes |
| Revision history | Yes |
| Revocation effects | Yes |

---

# 6. Consolidation Outcomes

A Phase 12 operation should produce one of the following governed outcomes:

```text
KEEP_SEPARATE
CANDIDATE
CONSOLIDATE
REFINE
CONFLICT
REVIEW_REQUIRED
INVALIDATED
No implicit outcome should exist.
7. Similarity Interpretation
Similarity scores are decision inputs, not authority.
Example conceptual thresholds:
0.00 ─────────────── 0.70 ───── 0.85 ───── 0.95 ───── 1.00
       unrelated         review       candidate       strong
Exact production thresholds must be established by implementation and
validation rather than assumed from this planning document.
A high score must never override:
- provenance;
- lifecycle;
- temporal incompatibility;
- entity mismatch;
- contradiction;
- authorization.
8. Contradiction Matrix
Situation	Action
Different wording, same meaning	Candidate
Additional detail	Refinement candidate
Lower-confidence duplicate	Candidate
Same fact, conflicting value	Conflict
Historical change	Temporal distinction
One evidence source revoked	Recalculate
All evidence revoked	Review/invalidate
Contradictory evidence from independent profiles	Preserve conflict
Contradiction resolved by explicit temporal evidence	Preserve temporal states


9. Consolidation Safety Rules
The following operations are prohibited:
DELETE source memory
DELETE supporting observation without history
DROP provenance
HIDE contradictory evidence
CONVERT inference into evidence
IGNORE revocation
IGNORE profile identity
INVENT temporal bounds
AUTO-ADOPT across profiles
10. Example
Before
Observation A
"SQLite is the authoritative Mnemosyne store."

Evidence:
  Athena / memory-A

Observation B
"Mnemosyne uses SQLite as its authoritative datastore."

Evidence:
  Horus / memory-B
Analysis
Entity compatibility: compatible
Semantic similarity: high
Temporal compatibility: compatible
Evidence: independent
Contradiction: none
Provenance: complete
Result
Consolidated Observation

"SQLite is the authoritative Mnemosyne datastore."

Supporting observations:
  A
  B

Supporting memories:
  Athena / memory-A
  Horus  / memory-B

Status:
  promoted

History:
  A + B -> consolidated
The source memories remain unchanged.
11. Example — Temporal Change
Observation A:
"Mnemosyne uses architecture X."

Valid:
2026-01-01 → 2026-06-01

Observation B:
"Mnemosyne uses architecture Y."

Valid:
2026-06-02 → present
These should not be treated as duplicates merely because they describe the
same subject.
The temporal layer indicates that they describe different states.
Result:
Architecture X
    ↓
historical state

Architecture Y
    ↓
current state
12. Example — Revocation
Observation:
"Feature X is supported."

Evidence:
  Athena / memory-A
  Horus  / memory-B
  Odin   / memory-C
If memory-B is revoked:
Before:
3 supporting memories

After:
2 currently supporting memories
1 revoked historical source
The observation history remains intact.
The observation may:
- retain sufficient confidence;
- have reduced confidence;
- become review-required;
depending on the governed evidence rules.
13. Required Test Categories
Phase 12 tests should cover:
- exact duplicates;
- near duplicates;
- unrelated observations;
- semantic equivalents;
- entity mismatch;
- relationship mismatch;
- temporal compatibility;
- temporal conflict;
- direct contradiction;
- multiple-profile corroboration;
- revoked evidence;
- missing source memory;
- provenance preservation;
- deterministic rebuild;
- consolidation history;
- rollback/revocation effects;
- profile isolation;
- Browser/API lifecycle filtering.
14. Phase 12 Decision Principle
The system should prefer:
Preserve evidence
      +
Explain the decision
      +
Create a stronger representation
over:
Simplify the database
      +
Delete redundancy
      +
Hide the original reasoning
The former is Mnemosyne's required consolidation model.
