Phase 13 — Mental Model Matrix
Status: COMPLETE
Phase: 13 — Higher-Level Mental Models

> **Implementation status:** COMPLETE through Phase 13G. Phase 13H final validation passed. The matrix remains the governance/reference contract for the implemented mental-model layer.
1. Purpose
This matrix defines the expected mental-model categories, inputs, outputs, evidence requirements, temporal semantics, lifecycle behavior, and governance constraints for Phase 13.
The matrix is an implementation reference.
It does not authorize functionality that conflicts with the Phase 13 specification or existing Mnemosyne governance.
2. Model Categories
Model Type	Primary Purpose	Typical Inputs	Derived Output
Concept	Represent a stable concept	Observations, entities, evidence	Concept model
Pattern	Represent recurring behavior/structure	Repeated observations, relationships	Pattern model
Relationship	Represent a higher-order relationship	Typed relationships, entities, evidence	Relationship model
Temporal	Represent recurring change over time	Events, temporal relationships, evidence	Temporal model
Expectation	Represent qualified recurring expectation	Historical observations, temporal evidence	Expectation model


3. Input Layer
Input	Allowed?	Role
Source memory	Indirectly	Original provenance
Observation	Yes	Primary analytical input
Entity	Yes	Concept identity
Relationship	Yes	Structural signal
Temporal evidence	Yes	Time/change context
Consolidated knowledge	Yes	Higher-level governed input
Evidence evaluation	Yes	Quality/confidence signal
Contradiction analysis	Yes	Conflict control
Existing mental model	Controlled	Versioned dependency
Raw private memory	No direct cross-boundary use	Privacy boundary
Unvalidated evidence	No current support	Governance boundary


4. Evidence Matrix
Condition	Model Eligibility
Promoted + active evidence	Current support
Promoted + revoked evidence	Historical only
Unpromoted evidence	No current support
Missing source memory	No current support
Unauthorized profile	Reject
Incomplete provenance	Reject/review
Contradictory evidence	Review/conflict
Temporal incompatibility	Review
Derived statement treated as evidence	Reject


5. Confidence Signals
Signal	Purpose
Evidence quality	Strength of supporting evidence
Corroboration	Independent support
Independence	Avoid duplicated evidence
Observation consistency	Pattern stability
Temporal compatibility	Applicability over time
Provenance completeness	Traceability
Contradiction state	Conflict penalty/review
Recency	Current relevance


Confidence is a descriptive signal.
It is not an authorization mechanism.
6. Lifecycle Matrix
State	Meaning	Current Retrieval	Historical Audit
CANDIDATE	Proposed model	No	Yes
VALIDATED	Passed governance validation	Controlled	Yes
ACTIVE	Current governed model	Yes	Yes
STALE	Supporting basis may have changed	No/flagged	Yes
SUPERSEDED	Replaced by later version	No	Yes
REVOKED	No longer valid	No	Yes


7. Contradiction Matrix
Situation	Required Outcome
No contradiction	Model may proceed
Direct contradiction	Preserve conflict / review
Temporal contradiction with explicit resolution	Temporally scoped model
Temporal contradiction without resolution	Review
Independent profiles contradict	Preserve contradiction
Weight difference only	Must not erase contradiction
Unknown temporal state	Review


8. Temporal Matrix
Temporal State	Interpretation
Current	Evidence supports current validity
Historical	Evidence supports past validity
Interval	Valid during explicit interval
Superseded	Replaced by later state/model
Unknown	Insufficient temporal information
Conflicted	Multiple incompatible temporal claims


Unknown must never be silently interpreted as current.
9. Provenance Matrix
Every active model should be traceable through:
Model
 ↓
Observation
 ↓
Evidence
 ↓
Source Memory
 ↓
Hermes Profile
 ↓
Original Provenance
Where a relationship is involved:
Model
 ↓
Relationship
 ↓
Relationship Evidence
 ↓
Source Memory
 ↓
Profile
Provenance Requirement	Required
Model ID	Yes
Derivation method	Yes
Supporting observations	Yes
Supporting evidence	Yes
Supporting memories	Yes
Source profiles	Yes
Temporal context	When applicable
Model version	Yes
Refresh reason	On refresh
Revocation state	Yes


10. Version Matrix
Event	Version Behavior
Initial validated model	v1
New supporting evidence	New version if materially changes model
Contradictory evidence	New version/review state
Revocation	State change and audit event
Temporal change	New version
Refresh	New version
Supersession	Preserve previous version
Destructive overwrite	Prohibited


11. Staleness Matrix
Trigger	Expected Action
Supporting memory revoked	Recalculate
Supporting evidence revoked	Recalculate
Major contradiction	Review
Entity identity changed	Recalculate
Relationship changed	Recalculate
Temporal interval expired	Mark stale/review
Supporting evidence materially reduced	Recalculate
Model dependency changed	Recalculate


12. Governance Matrix
Rule	Phase 13 Requirement
Profile isolation	Mandatory
Provenance	Mandatory
Source immutability	Mandatory
Evidence preservation	Mandatory
Revocation	Mandatory
Contradiction preservation	Mandatory
Temporal integrity	Mandatory
Determinism	Mandatory
Explainability	Mandatory
Cross-profile learning	Deferred to Phase 14
Raw private-memory leakage	Prohibited
Silent destructive consolidation	Prohibited
Confidence-based authorization	Prohibited


13. Data Science / Data Engineering Matrix
Concern	Classification	Phase 13 Treatment
Feature construction	Data Science	Required
Pattern detection	Data Science	Required
Confidence estimation	Data Science	Required
Threshold evaluation	Data Science	Required where thresholds exist
False-positive analysis	Data Science	Required
Schema design	Data Engineering	Required
Provenance	Data Engineering	Required
Idempotency	Data Engineering	Required
Lifecycle management	Data Engineering	Required
Rebuildability	Data Engineering	Required
Auditability	Both	Required
Explainability	Both	Required


14. API / Browser Matrix
Surface	Requirement
Model list	Identify derived models explicitly
Model detail	Show provenance
Evidence view	Show supporting evidence
Observation view	Show supporting observations
Relationship view	Show relevant relationships
Temporal view	Show validity interval/state
Conflict view	Show contradictions
Version view	Show historical versions
Revocation view	Show invalidated dependencies


A Browser model must never look identical to an original memory.
15. Phase 13 Deliverable Matrix
Phase	Deliverable	Validation
13A	Model contract	Unit tests
13B	Candidate detection	Unit + integration
13C	Validation	Governance tests
13D	Confidence	Numerical tests
13E	Version/staleness	Lifecycle tests
13F	Synthesis	Provenance tests
13G	API/Browser	Route/UI tests if implemented
13H	Final validation	Full regression


16. Core Invariant
The fundamental Phase 13 rule is:
A mental model may summarize or generalize governed knowledge, but it may never sever the chain back to the evidence from which that understanding was derived.
