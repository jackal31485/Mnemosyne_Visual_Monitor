# Phase 13 — Higher-Level Mental Models

**Status:** COMPLETE
**Phase:** 13
**Predecessor:** Phase 12 — Evidence Consolidation & Memory Synthesis
**Successor:** Phase 14 — Cross-Profile Learning & Controlled Transfer

> **Implementation status:** Phase 13A–13G are implemented and Phase 13H final validation has passed. Phase 13 remains a governed derived-knowledge layer; it does not introduce Phase 14 cross-profile learning.

---

## 1. Purpose

Phase 13 introduces higher-level mental models derived from governed Mnemosyne knowledge.

The purpose is to move beyond individual observations and consolidated evidence toward stable, reusable representations of concepts, patterns, expectations, and relationships.

Phase 13 must not turn Mnemosyne into an opaque generative summarization system.

A mental model must remain:

- evidence-backed;
- provenance-preserving;
- explainable;
- reproducible;
- versioned;
- revocation-aware;
- temporally aware;
- profile-isolated;
- distinguishable from observed facts;
- distinguishable from source memories;
- governed as derived knowledge.

The central question becomes:

> What stable understanding can be derived from accumulated governed knowledge without confusing inference with observation?

---

## 2. Relationship to Previous Phases

Phase 10 established canonical entities and typed relationships.

Phase 11 established temporal intelligence and changing relationships.

Phase 12 established evidence consolidation, contradiction handling, evidence weighting, and evidence-preserving synthesis.

Phase 13 builds on those capabilities.

```text
Entities
    +
Relationships
    +
Temporal Context
    +
Validated Evidence
    +
Consolidated Knowledge
    ↓
Higher-Level Mental Models
The model is therefore a derived layer above governed observations and evidence.
It must never replace those lower layers.
3. Conceptual Model
A Phase 13 mental model is a governed derived representation of a recurring concept, pattern, relationship structure, expectation, or explanation supported by multiple pieces of evidence.
Source Memories
      ↓
Observations
      ↓
Evidence
      ↓
Consolidation
      ↓
Entities / Relationships / Temporal Context
      ↓
Governed Knowledge
      ↓
Mental Model Candidate
      ↓
Validation
      ↓
Mental Model
      ↓
Versioned Derived Knowledge
The mental model is not itself a source memory.
The mental model is not an observation.
The mental model is not evidence.
The mental model is derived knowledge whose supporting evidence must remain inspectable.
4. Goals
Phase 13 should establish the foundation for:
1. recurring concept detection;
2. pattern identification;
3. stable relationship structures;
4. expectation or tendency representations;
5. model confidence;
6. supporting-evidence references;
7. contradiction awareness;
8. temporal scope;
9. provenance chains;
10. model versioning;
11. staleness detection;
12. revocation-aware refresh;
13. deterministic model construction;
14. explainable model inspection.
5. Non-Goals
Phase 13 does not implement:
- automatic cross-profile learning;
- unrestricted profile-to-profile transfer;
- distributed federation;
- remote learning;
- autonomous trust;
- silent source-memory modification;
- destructive consolidation;
- opaque model replacement;
- unrestricted LLM-generated knowledge;
- production-scale model serving;
- generalized AGI-style reasoning.
Cross-profile learning remains Phase 14.
6. Mental Model Categories
The initial implementation should support a deliberately constrained set of model categories.
6.1 Concept Model
Represents a stable concept emerging from multiple governed observations.
Example:
Concept:
    "Mnemosyne uses SQLite as an authoritative local store."

Supporting evidence:
    multiple observations
    multiple implementation records
    stable across time
6.2 Pattern Model
Represents a recurring relationship or behavioral pattern.
Example:
Pattern:
    "Entity A repeatedly appears in relationship R with Entity B."

Evidence:
    repeated observations
    compatible temporal context
6.3 Relationship Model
Represents a higher-level relationship derived from multiple lower-level relationships.
Example:
Entity A
    ↓ repeatedly associated with
Entity B
    ↓ through
Relationship R
The derived model must retain the underlying relationship provenance.
6.4 Temporal Model
Represents a stable pattern involving change over time.
Example:
State A
    ↓
State B
    ↓
State C
Temporal models must never invent transitions that are not supported by evidence.
6.5 Expectation Model
Represents a qualified expectation derived from recurring historical evidence.
Expectations must be explicitly marked as derived and probabilistic or confidence-qualified.
They must never be presented as guaranteed facts.
7. Required Model Structure
A mental model should contain, at minimum:
- model_id
- model_type
- title
- description
- entity_ids
- relationship_ids
- supporting_observation_ids
- supporting_evidence_ids
- supporting_memory_ids
- source_profiles
- temporal_scope
- confidence
- status
- version
- created_at
- updated_at
- provenance
- derivation_method
- contradictory_evidence_ids
- staleness_state
Additional fields may be introduced only when they preserve the distinction between source data and derived knowledge.
8. Lifecycle
Mental models should have an explicit lifecycle.
CANDIDATE
    ↓
VALIDATED
    ↓
ACTIVE
    ↓
STALE
    ↓
REFRESHED / SUPERSEDED
A model may also become:
REVOKED
when its supporting knowledge is no longer valid.
A revoked model must remain auditable.
It must not be silently deleted.
9. Candidate Generation
Candidate models may be generated from:
- repeated observations;
- recurring entity relationships;
- repeated temporal patterns;
- consolidated observations;
- corroborated evidence;
- stable concepts;
- high-confidence knowledge structures.
Similarity alone is insufficient.
A similarity signal may identify a candidate but must never authorize model creation by itself.
10. Evidence Requirements
Every active model must be traceable to supporting evidence.
The minimum provenance chain is:
Mental Model
    ↓
Supporting Observation
    ↓
Evidence
    ↓
Source Memory
    ↓
Hermes Profile
    ↓
Original Provenance
Where a model depends directly on relationships:
Mental Model
    ↓
Relationship
    ↓
Relationship Evidence
    ↓
Source Memory
No active model may depend exclusively on another derived model unless the derivation chain remains fully traceable to original evidence.
11. Evidence Weighting
Phase 12 evidence weighting remains authoritative.
Phase 13 must consume evidence evaluations rather than inventing a second unrelated evidence-quality system.
A model's confidence may incorporate:
- supporting evidence quality;
- corroboration;
- independence;
- temporal compatibility;
- provenance completeness;
- contradiction state;
- observation consistency.
Confidence must not override governance.
A high confidence score does not authorize:
- cross-profile adoption;
- privacy bypass;
- promotion;
- revocation suppression;
- contradiction removal.
12. Contradiction Handling
Contradictory evidence must remain visible.
If evidence conflicts:
Model Candidate
      ↓
Contradiction analysis
      ↓
┌───────────────┬──────────────────┐
│ Resolvable    │ Unresolved       │
│ temporal      │ contradiction    │
└───────┬───────┴────────┬─────────┘
        ↓                ↓
Temporal model       Review / Conflict
The model must not choose the most convenient evidence simply because it has the highest numerical weight.
Weighting can rank evidence.
Weighting cannot erase contradiction.
13. Temporal Semantics
Models must retain temporal context where relevant.
A model may be:
- currently valid;
- historically valid;
- valid during a defined interval;
- superseded;
- temporally unresolved.
The system must not convert historical evidence into a current model without evidence supporting that transition.
14. Staleness
A mental model becomes stale when its supporting evidence changes sufficiently that the model may no longer represent current knowledge.
Possible triggers include:
- source-memory revocation;
- evidence lifecycle changes;
- contradictory evidence;
- entity changes;
- relationship changes;
- temporal expiry;
- significant supporting-evidence loss;
- model dependency changes.
Staleness must be explicit.
The system must not silently rewrite a model.
15. Model Versioning
Mental models are immutable historical records at the version level.
A refresh creates a new version rather than mutating the historical derivation.
Model v1
   ↓
new evidence
   ↓
Model v2
Version history must preserve:
- previous model state;
- derivation inputs;
- changed evidence;
- changed relationships;
- changed confidence;
- reason for refresh;
- timestamp;
- provenance.
16. Determinism
Given the same:
- source observations;
- evidence;
- entity graph;
- relationship graph;
- temporal state;
- configuration;
- model-generation rules;
the same candidate model should be produced.
If an LLM is eventually used as an optional interpretation component, its output must not become an uncontrolled source of truth.
The deterministic governed pipeline remains authoritative.
17. Data Science Requirements
Phase 13 should be treated as an applied data-science problem involving:
- feature construction;
- pattern detection;
- evidence aggregation;
- confidence estimation;
- contradiction analysis;
- temporal reasoning;
- threshold selection;
- model evaluation;
- false-positive analysis;
- false-negative analysis;
- explainability.
Where thresholds are introduced, they must be documented and testable.
Where empirical validation is possible, the project should record the evaluation methodology.
18. Data Engineering Requirements
Phase 13 must preserve:
- explicit schemas;
- lifecycle state;
- provenance;
- deterministic processing;
- idempotency;
- source immutability;
- derived-data boundaries;
- reproducible refresh;
- auditability;
- revocation propagation;
- dependency tracking.
Derived mental models should be rebuildable from governed lower-level data.
19. API / Browser Boundary
If Phase 13 exposes mental models through the Browser or API, the surface must distinguish:
Observed
Evidence
Consolidated
Derived Model
The Browser must make it possible to inspect why a model exists.
A model view should expose:
- model description;
- model type;
- confidence;
- temporal scope;
- supporting observations;
- supporting evidence;
- source profiles;
- contradictions;
- version;
- staleness;
- provenance.
No Browser surface may imply that a derived model is an original memory.
20. Privacy and Profile Isolation
Phase 13 inherits all existing profile-isolation rules.
A model may combine information only when the underlying information is already authorized within the collective knowledge boundary.
Private source memories must never leak through a derived model.
A model's provenance must not become a side channel for exposing unauthorized private content.
No Phase 13 feature grants cross-profile learning permission.
21. Revocation
If supporting evidence or source memory is revoked:
1. the model dependency graph must identify affected models;
2. current validity must be recalculated;
3. affected models may become stale, review-required, superseded, or revoked;
4. historical versions remain auditable;
5. revoked source content must not continue to provide current support.
Revocation must propagate through derived knowledge.
22. Testing Strategy
Phase 13 testing should cover:
Unit tests
- model creation;
- validation;
- lifecycle transitions;
- confidence calculation;
- provenance;
- contradiction handling;
- temporal handling;
- staleness;
- versioning;
- revocation;
- deterministic generation.
Integration tests
- observation → model;
- evidence → model;
- entity/relationship → model;
- temporal evidence → model;
- contradiction → model review;
- revocation → model invalidation;
- model → API/browser if implemented.
Regression tests
The complete existing suite must continue to pass.
Data-quality tests
Verify:
- no missing provenance;
- no unauthorized profiles;
- no orphan evidence;
- no orphan observations;
- no invalid lifecycle states;
- no duplicate active model versions;
- no silent destructive mutation.
23. Suggested Implementation Sequence
13A — Mental Model Contract
Define:
- model types;
- fields;
- lifecycle;
- provenance;
- status;
- temporal semantics.
13B — Candidate Detection
Implement deterministic candidate generation from governed observations and relationships.
13C — Model Validation
Validate:
- evidence;
- provenance;
- profile authorization;
- temporal compatibility;
- contradiction state.
13D — Model Confidence
Integrate Phase 12 evidence weighting and supporting-signal aggregation.
13E — Versioning and Staleness
Implement:
- versions;
- dependency tracking;
- refresh;
- staleness;
- revocation propagation.
13F — Governed Model Synthesis
Produce evidence-preserving derived models.
13G — Retrieval / API / Browser Integration
Expose models only if the existing Browser/API architecture can preserve the governance contract.
13H — Full Validation
Run:
- targeted Phase 13 tests;
- full regression;
- py_compile;
- git diff --check;
- API tests;
- Browser tests if a UI surface changes;
- live validation where applicable.
24. Completion Criteria
Phase 13 is complete only when:
1. mental model contracts are implemented;
2. model provenance is preserved;
3. supporting observations remain inspectable;
4. supporting evidence remains inspectable;
5. model lifecycle is explicit;
6. contradiction handling is implemented;
7. temporal semantics are preserved;
8. staleness is detectable;
9. model versions are auditable;
10. revocation propagates correctly;
11. source memories remain immutable;
12. profile isolation remains intact;
13. no derived model is represented as an observed fact;
14. deterministic behavior is tested;
15. targeted tests pass;
16. full regression passes;
17. documentation matches implementation;
18. data-science/data-engineering boundaries are documented;
19. no Phase 14 cross-profile learning behavior has been introduced accidentally.
25. Final Design Principle
Phase 13 is not about making Mnemosyne generate more text.
It is about making Mnemosyne capable of representing:
What the system has learned from accumulated governed evidence, why it believes it, when that understanding applies, how it was derived, and what evidence would cause that understanding to change.

The mental model is therefore a governed derived data product, not a replacement for memory.
