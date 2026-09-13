# Phase 12 — Governance Invariants

**Phase:** 12 — Evidence Consolidation & Memory Synthesis  
**Status:** MANDATORY DESIGN CONTRACT  
**Purpose:** Define the governance rules that consolidation must never violate

---

# 1. Core Principle

Phase 12 may synthesize knowledge.

It may not rewrite the history that produced that knowledge.

The governing model is:

```text
Source Memory
     ↓
Evidence
     ↓
Observation
     ↓
Consolidation
     ↓
Consolidated Knowledge
Every layer must remain distinguishable.
2. Source-Memory Immutability
Consolidation must never delete, overwrite, or silently mutate a source memory.
A source memory may become:
- revoked;
- unavailable;
- superseded;
- excluded from current retrieval;
but its historical existence must remain represented where the architecture
supports that history.
3. Observation Preservation
An observation participating in consolidation must remain recoverable.
A consolidation operation may establish:
A + B → C
but must not turn that into:
A + B → delete A
           delete B
           keep C
Instead:
A ─┐
   ├──→ C
B ─┘

A and B remain traceable.
4. Provenance Preservation
Every consolidated object must preserve provenance sufficient to answer:
Where did this come from?

The provenance chain should support navigation such as:
Consolidated Knowledge
        ↓
Consolidation Record
        ↓
Observation
        ↓
Evidence
        ↓
Source Memory
        ↓
Hermes Profile
5. Profile Isolation
Profile identity must never disappear during consolidation.
If observations originate from:
Athena
Horus
Odin
Thoth
the consolidated result must retain that source information.
Consolidation is not permission to collapse profile identity.
6. Promotion Boundary
Only appropriately promoted and currently authorized evidence may be treated
as collective support.
The consolidation layer must not:
- bypass promotion;
- import private profile memories directly;
- expose raw private memory;
- infer authorization from similarity.
7. Revocation
Revocation must propagate into the current support state.
Conceptually:
Evidence revoked
      ↓
Observation support recalculated
      ↓
Consolidation support recalculated
      ↓
Confidence/status may change
Historical audit information remains available.
8. No Silent Destructive Consolidation
The following is prohibited:
A + B
 ↓
C
 ↓
A deleted
B deleted
The required model is:
A + B
 ↓
C
 ↓
A retained
B retained
history retained
9. Contradiction Preservation
Conflicting observations must remain discoverable.
The system must not resolve contradictions merely by selecting the most
convenient statement.
A contradiction may instead result in:
CONFLICT
REVIEW_REQUIRED
TEMPORAL_DISTINCTION
REFINEMENT
10. Temporal Integrity
Phase 11 temporal evidence remains authoritative for temporal facts.
Phase 12 must not invent:
- dates;
- durations;
- valid-from values;
- valid-to values;
- sequence;
- recurrence;
- state endings.
Missing temporal evidence remains unknown.
It does not imply termination.
11. Evidence vs Derived Understanding
Phase 12 creates derived consolidated knowledge.
That does not make the result equivalent to raw evidence.
The distinction must remain explicit:
Observed
    ≠
Consolidated
    ≠
Inferred
    ≠
Mental Model
Phase 13 is responsible for higher-level mental models.
12. Determinism
Given identical inputs and configuration:
observations
evidence
entities
relationships
temporal context
thresholds
governance rules
the consolidation result should be reproducible.
Randomized or opaque consolidation decisions are not acceptable without an
explicitly governed reason.
13. Explainability
Every consolidation should be able to explain:
- participating observations;
- similarity signals;
- evidence considered;
- contradictory evidence;
- temporal analysis;
- entity analysis;
- decision;
- resulting object;
- provenance;
- history.
A user should be able to ask:
Why were these observations consolidated?

and receive an evidence-backed answer.
14. Confidence
Confidence is a property of the governed evidence state.
It must not become:
confidence = truth
Instead:
confidence = assessment of current supporting evidence
Confidence may change when:
- evidence is revoked;
- new evidence is added;
- contradictory evidence appears;
- temporal evidence changes the interpretation;
- supporting observations are refined.
15. Evidence Independence
Multiple observations derived from the same source memory must not automatically
be treated as independent corroboration.
Where practical, consolidation should distinguish:
3 observations
from 1 memory
from:
3 observations
from 3 independent memories
and:
3 observations
from 3 independent profiles
Independence is a governance-relevant signal.
16. No Automatic Cross-Profile Learning
Phase 12 consolidation may combine authorized collective evidence.
It does not grant any profile the right to learn from another profile.
Cross-profile learning remains a later governed capability.
Therefore:
Collective consolidation
        ≠
Profile adoption
17. Browser/API Enforcement
Any Phase 12 API or Browser surface must enforce the same governance rules as
the underlying data layer.
The UI must not expose information merely because it exists internally.
Lifecycle and authorization checks remain mandatory.
18. Auditability
Every governed consolidation should have an audit trail containing, where
applicable:
candidate ID
participating observations
evidence references
decision
decision reason
threshold/configuration
timestamp
resulting observation
revision
revocation effects
19. Reversibility
A consolidation must be logically reversible even when the exact operation
is represented as a new derived object.
The system must be able to determine:
What was consolidated?
Why?
When?
Into what?
What evidence supported it?
What happened when evidence was revoked?
20. Governance Failure Modes
The following represent Phase 12 defects:
Critical
- source memory deletion;
- provenance loss;
- private-memory leakage;
- revoked evidence presented as current;
- profile identity loss;
- contradiction deletion;
- fabricated temporal information.
Major
- nondeterministic consolidation;
- inaccessible consolidation history;
- confidence not recalculated after revocation;
- evidence treated as equivalent to inference;
- consolidation bypassing promotion rules.
Minor
- incomplete UI explanation;
- insufficient metadata presentation;
- inefficient similarity processing.
21. Mandatory Review Questions
Before accepting a Phase 12 implementation:
1. Can every consolidated object be traced to its observations?
2. Can every observation be traced to evidence?
3. Can evidence be traced to a source memory?
4. Is source profile identity preserved?
5. Does revocation affect current support?
6. Can contradictions still be inspected?
7. Can historical temporal distinctions survive consolidation?
8. Are source memories untouched?
9. Is the decision deterministic?
10. Can the system explain why a consolidation occurred?
11. Can consolidation be distinguished from inference?
12. Does the Browser respect the same governance boundary?
22. Phase 12 Non-Negotiables
PROFILE ISOLATION
LOCAL-FIRST ARCHITECTURE
SQLITE-FIRST STORAGE
MEDIATION / AIR-LOCK
PRIVACY FILTERING
EXPLICIT PROMOTION
PROVENANCE
REVOCATION
AUDITABILITY
SOURCE-MEMORY IMMUTABILITY
NO SILENT DESTRUCTIVE CONSOLIDATION
NO AUTOMATIC TRUST → ADOPTION
NO RAW PRIVATE-MEMORY LEAKAGE
NO FABRICATED TEMPORAL FACTS
NO DERIVED KNOWLEDGE PRESENTED AS RAW EVIDENCE
23. Final Governance Rule
The Phase 12 implementation is successful only if it makes Mnemosyne's
knowledge more coherent without making its history less trustworthy.
