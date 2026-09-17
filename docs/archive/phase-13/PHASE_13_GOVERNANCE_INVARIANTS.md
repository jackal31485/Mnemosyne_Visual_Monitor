Phase 13 — Governance Invariants
Status: COMPLETE
Phase: 13 — Higher-Level Mental Models

> **Implementation status:** COMPLETE through Phase 13G. Phase 13H final validation passed. These invariants remain non-negotiable for derived mental models.
1. Purpose
This document defines the non-negotiable governance invariants for Phase 13.
These rules take precedence over convenience, model quality, retrieval quality, implementation simplicity, or generation speed.
2. Source Immutability
Mental-model generation must never modify or destroy source memories.
Source Memory
    ↓
Observation
    ↓
Model
is permitted.
Source Memory
    ↓
Model
    ↓
overwrite Source Memory
is prohibited.
3. Derived-Knowledge Boundary
A mental model is derived knowledge.
It must never be represented internally or visually as if it were an original observation.
The system must preserve:
- source;
- observation;
- evidence;
- consolidation;
- derived model.
4. Provenance Preservation
Every active model must retain sufficient provenance to answer:
Why does this model exist?

At minimum:
Model
 ↓
Supporting observation(s)
 ↓
Evidence
 ↓
Source memory
 ↓
Profile
 ↓
Original provenance
Breaking this chain invalidates the model for current use.
5. Evidence Preservation
Evidence used to support a model must remain independently inspectable.
The model must not replace its supporting evidence.
6. Profile Isolation
Phase 13 does not authorize cross-profile learning.
Models may only consume information already authorized within the existing collective boundary.
No implementation may:
- read private profile memory directly to construct collective models;
- expose private memory through model provenance;
- infer authorization from model confidence;
- infer permission from repeated observations.
7. Promotion Boundary
Only governed knowledge may provide current support to a collective mental model.
Unpromoted information is not current collective evidence.
8. Revocation Propagation
Revocation must propagate through derived knowledge.
Source Memory Revoked
        ↓
Evidence invalidated
        ↓
Observation support recalculated
        ↓
Model dependency recalculated
        ↓
Model stale/reviewed/revoked
A revoked source cannot silently continue supporting an active model.
9. Historical Preservation
Revocation does not erase history.
Historical model versions and audit information must remain available where governance permits.
10. Contradiction Preservation
Contradictory evidence must not be deleted merely because one claim has higher confidence.
Weighting may influence ranking.
Weighting may not erase contradiction.
11. Temporal Integrity
Historical evidence must not automatically become current evidence.
Unknown temporal state must not be silently treated as current.
Temporal transitions require evidence.
12. Deterministic Derivation
Mental-model construction must be reproducible from its governed inputs and documented configuration.
The system should support rebuilding derived models without requiring undocumented hidden state.
13. Explainability
A model must expose enough information to explain:
- what it represents;
- why it exists;
- what supports it;
- what contradicts it;
- when it applies;
- how confident the system is;
- how it was derived;
- what changed between versions.
14. Confidence Is Not Authorization
No numerical confidence threshold may authorize:
- profile transfer;
- promotion;
- privacy bypass;
- revocation suppression;
- contradiction deletion.
Confidence describes evidence.
Governance determines permission.
15. No Silent Model Mutation
An active model must not silently change its meaning.
Material changes create a new version or explicit lifecycle transition.
16. No Silent Destructive Consolidation
Phase 13 must not destructively merge:
- memories;
- observations;
- evidence;
- entities;
- relationships;
- model versions.
Derived models may consolidate understanding, but source structures remain preserved.
17. Dependency Integrity
Every model dependency must be explicit.
A model must not depend on:
- missing observations;
- revoked current evidence;
- unauthorized profiles;
- incomplete provenance;
- invalid lifecycle states.
18. Model-on-Model Dependencies
A mental model may reference another mental model only when the dependency remains traceable to original governed evidence.
Derived-on-derived chains must never become an opaque knowledge layer.
19. Browser Governance
If mental models are exposed through the Browser:
- derived status must be visible;
- provenance must be inspectable;
- lifecycle state must be respected;
- revoked information must not surface as current;
- unauthorized profile data must remain inaccessible.
20. API Governance
If Phase 13 creates API routes:
- request parameters must be validated;
- lifecycle state must be enforced;
- profile authorization must be preserved;
- provenance must be returned where appropriate;
- errors must not leak private content;
- derived models must remain distinguishable from source memories.
21. Rebuildability
A derived model should be reconstructable from:
Governed observations
+
Evidence
+
Entities
+
Relationships
+
Temporal context
+
Documented derivation rules
The system should not require an opaque generated artifact as the sole source of truth.
22. Auditability
Important model events should be attributable:
- creation;
- validation;
- activation;
- refresh;
- supersession;
- staleness;
- revocation;
- contradiction review.
23. Data Science Boundary
Statistical or model-based signals may identify:
- similarity;
- recurring patterns;
- candidate concepts;
- confidence;
- ranking.
They do not independently establish truth.
24. Data Engineering Boundary
The data pipeline remains authoritative for:
- schema;
- lifecycle;
- provenance;
- authorization;
- source integrity;
- deterministic transformation;
- rebuildability.
25. LLM Boundary
If an LLM is used during Phase 13:
1. its output is derived content;
2. its output is not automatically evidence;
3. its output is not automatically authoritative;
4. provenance must identify the generation method;
5. supporting evidence must exist independently;
6. deterministic validation must remain outside the model.
An LLM must never become an undocumented source of truth.
26. Phase Boundary
Phase 13 must not accidentally implement Phase 14.
Specifically prohibited during Phase 13:
- automatic cross-profile learning;
- automatic profile adoption;
- unrestricted profile synchronization;
- remote knowledge transfer.
Those capabilities remain governed future work.
27. Core Governance Rule
Mental models may increase abstraction, but abstraction must never decrease accountability.

Every higher-level understanding must remain connected to the governed knowledge beneath it.
