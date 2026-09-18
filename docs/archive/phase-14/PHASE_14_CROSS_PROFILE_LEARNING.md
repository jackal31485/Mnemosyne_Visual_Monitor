# Phase 14 — Cross-Profile Learning & Controlled Transfer

**Status:** CURRENT — READY TO BEGIN
**Predecessor:** Phase 13 — Higher-Level Mental Models
**Successor:** Phase 15 — Advanced Retrieval Optimization
**Date:** 2026-09-16

> **Implementation status:** PLANNED — documentation checkpoint only. No Phase 14
> implementation has begun.

---

## 1. Purpose

Phase 14 introduces governed learning between Hermes profiles.

The purpose is not to create a shared writable memory pool.

The purpose is to establish a controlled mechanism through which knowledge that
has already passed through Mnemosyne's governance layers may be evaluated for
applicability to another profile and, only after explicit authorization, adopted
as profile-specific learned knowledge.

The central principle is:

> **Collective visibility is not learning. Transfer-candidate generation is not
> learning. Explicit authorized adoption is learning.**

Phase 14 therefore introduces a new architectural boundary between:

- profile-local memory;
- governed collective knowledge;
- transfer candidates;
- transfer authorization;
- destination-profile adoption;
- profile-specific derived knowledge.

---

## 2. Relationship to Previous Phases

Phase 14 depends on the governance established by earlier phases.

### Phase 8

Hybrid retrieval establishes semantic, lexical, graph, and related retrieval
capabilities.

### Phase 9

Browser-facing retrieval establishes explainable access to governed knowledge.

### Phase 10

Entity and relationship intelligence establishes structured knowledge
connections.

### Phase 11

Temporal intelligence establishes time-aware evidence and state interpretation.

### Phase 12

Evidence consolidation establishes evidence-preserving synthesis, contradiction
handling, provenance, and governed derived knowledge.

### Phase 13

Higher-level mental models establish governed derived abstractions with lifecycle,
confidence, versioning, staleness, provenance, and revocation.

### Phase 14

Cross-profile learning introduces controlled transfer of eligible knowledge between
Hermes profiles.

The distinction is important:

```text
Phase 12:
    observations -> consolidated evidence-backed knowledge

Phase 13:
    governed knowledge -> higher-level mental models

Phase 14:
    governed knowledge / mental models
            -> transfer candidate
            -> authorization
            -> destination adoption
3. Core Principle
Mnemosyne must never equate:
shared knowledge exists
with:
every profile has learned the knowledge
The system must preserve the difference between:
1. available — knowledge can be inspected;
2. eligible — knowledge satisfies transfer requirements;
3. candidate — transfer has been proposed for a destination;
4. authorized — transfer has been explicitly approved;
5. adopted — destination-specific learning has been created;
6. revoked — adoption is no longer valid;
7. superseded — a newer learned representation replaces an older one.
4. Transfer Lifecycle
The Phase 14 lifecycle is:
COLLECTIVE KNOWLEDGE
        |
        v
TRANSFER ELIGIBILITY
        |
        v
TRANSFER CANDIDATE
        |
        v
SOURCE / DESTINATION AUTHORIZATION
        |
        v
APPLICABILITY VALIDATION
        |
        v
EXPLICIT ADOPTION
        |
        v
DESTINATION-SPECIFIC LEARNED STATE
        |
        +------------------+
        |                  |
        v                  v
     REFRESH            REVOKE
        |                  |
        v                  v
 NEW VERSION          INVALIDATED
Every transition must be explicit and auditable.
5. Source Profile Boundary
A source profile owns its private memory.
Phase 14 must never require raw source-memory content to be copied into the
destination profile.
A transfer may reference:
- source profile;
- source memory identifier;
- collective entry identifier;
- observation identifiers;
- evidence identifiers;
- mental-model identifier;
- relationship identifiers;
- temporal scope;
- provenance;
- authorization state.
It must not reproduce private raw memory content merely to facilitate transfer.
6. Destination Profile Boundary
The destination profile owns any learned representation created by adoption.
A destination profile must not be modified merely because:
- a collective entry exists;
- a transfer candidate exists;
- another profile knows something;
- a transfer is recommended;
- a transfer is authorized but not yet adopted.
Adoption must be an explicit state transition.
7. Transfer Candidate
A transfer candidate represents a proposed knowledge transfer.
A candidate should identify:
- candidate identifier;
- source profile;
- destination profile;
- source knowledge identifier;
- source memory identifiers;
- supporting observation identifiers;
- supporting evidence identifiers;
- mental-model identifier when applicable;
- proposed applicability;
- benefit signals;
- temporal applicability;
- contradiction state;
- provenance;
- creation timestamp;
- lifecycle state.
The candidate itself is not learned knowledge.
8. Applicability
Knowledge useful to one profile may not be useful to another.
Phase 14 therefore requires destination-specific applicability analysis.
Potential signals include:
- shared entities;
- shared relationships;
- compatible temporal scope;
- task relevance;
- destination knowledge gaps;
- source evidence quality;
- confidence;
- contradiction state;
- freshness;
- prior destination knowledge;
- explicit destination preferences or authorization rules.
These signals must remain inspectable.
No opaque score may be treated as sufficient explanation for adoption.
9. Benefit Analysis
Phase 14 may evaluate whether transfer is useful to the destination.
Benefit analysis should consider:
- whether the destination lacks the knowledge;
- whether the knowledge fills an identifiable gap;
- whether existing destination knowledge conflicts with it;
- whether the source evidence is sufficiently strong;
- whether the information is temporally applicable;
- whether adoption would introduce unnecessary duplication.
Benefit analysis produces a governed decision signal.
It does not itself authorize adoption.
10. Authorization
Authorization must identify:
- source profile;
- destination profile;
- knowledge being transferred;
- authorization actor or mechanism;
- authorization timestamp;
- authorization scope;
- expiration where applicable;
- revocation state.
Authorization must not be inferred merely from membership in the collective.
The default must be no transfer unless an explicit rule permits it.
11. Adoption
Adoption creates a destination-profile representation.
The destination representation must preserve a chain back to:
destination learned state
        |
        v
transfer record
        |
        v
collective knowledge
        |
        v
evidence
        |
        v
observations
        |
        v
source memory identifiers
        |
        v
source profile
The destination representation must therefore remain explainable.
Adoption must not rewrite the source memory.
12. Adaptation
The destination may require a profile-specific representation.
Adaptation may change:
- wording;
- local categorization;
- relationship interpretation;
- destination-specific applicability;
- temporal interpretation within governed limits.
Adaptation must not:
- erase source provenance;
- convert inference into observation;
- remove contradictory evidence;
- claim that the destination originated the knowledge;
- sever the evidence chain.
13. Conflict Handling
Destination knowledge may conflict with transferred knowledge.
Phase 14 must preserve the conflict rather than silently replacing one representation.
Possible outcomes include:
- KEEP_EXISTING;
- ADOPT_ALONGSIDE;
- REVIEW_REQUIRED;
- CONFLICT;
- REJECT;
- SUPERSEDE_EXISTING.
The exact decision mechanism must remain governed and testable.
Conflict history must remain auditable.
14. Temporal Applicability
Transferred knowledge may have a validity interval.
The system must preserve:
- source temporal scope;
- transfer timestamp;
- destination adoption timestamp;
- applicability interval;
- expiration or staleness where applicable.
A historical fact must not automatically become a timeless destination rule.
15. Revocation
Revocation must propagate through the transfer chain.
If source knowledge becomes invalid because of:
- source-memory revocation;
- collective revocation;
- evidence invalidation;
- provenance failure;
- authorization withdrawal;
then dependent transfer records and destination-derived representations must become
invalid, stale, or otherwise governed according to their lifecycle.
The audit record must remain.
Revocation must never mean destructive deletion of the transfer history.
16. Provenance
Every adopted representation must retain:
- source profile;
- destination profile;
- source knowledge identifier;
- transfer identifier;
- source memory identifiers;
- supporting observation identifiers;
- supporting evidence identifiers;
- derivation method;
- authorization information;
- adoption timestamp;
- version;
- revocation state.
No transfer is valid if its provenance cannot be reconstructed.
17. Privacy
Phase 14 inherits all existing privacy boundaries.
The system must not use cross-profile learning as an excuse to copy:
- raw private memory;
- private user identifiers;
- private credentials;
- sensitive metadata;
- ungoverned free-form content.
Shared knowledge remains governed knowledge.
The source profile remains the owner of source memory.
18. Data Science Boundary
Phase 14 is an applied evaluation problem.
The system should be able to answer:
Why was this knowledge considered useful to this profile?

and:
What evidence supports that decision?

and:
What would cause the transfer to be rejected or revoked?

Potential measurable dimensions include:
- applicability;
- evidence quality;
- novelty;
- destination coverage;
- contradiction;
- temporal compatibility;
- confidence;
- expected benefit.
The system must avoid presenting arbitrary model scores as unquestionable truth.
19. Data Engineering Boundary
Phase 14 introduces a controlled transfer pipeline.
It does not create a shared writable profile database.
The intended architecture is:
Source Profile
     |
     v
Governed Collective Knowledge
     |
     v
Transfer Candidate
     |
     v
Authorization / Validation
     |
     v
Destination Adoption Boundary
     |
     v
Destination Profile
Each boundary should be independently testable.
20. Determinism
Candidate generation and governance checks should be deterministic where possible.
Given the same:
- source knowledge;
- destination state;
- authorization policy;
- evidence;
- temporal state;
the system should produce the same transfer decision.
If an LLM is introduced later, it must remain subordinate to deterministic governance
checks.
LLM output must not bypass authorization or provenance validation.
21. Browser / API Expectations
If Phase 14 exposes transfer functionality through the Browser or API, surfaces
must distinguish:
- source knowledge;
- transfer candidate;
- authorization;
- adoption;
- destination representation;
- evidence;
- provenance;
- conflict;
- revocation.
A transfer candidate must never look like an ordinary source memory.
An adopted representation must clearly identify that it was learned through
controlled transfer.
22. No Implicit Social Learning
The following are explicitly prohibited:
- automatic copying from one profile to another;
- automatic adoption because knowledge is highly confident;
- automatic adoption because multiple profiles agree;
- automatic destination writes from collective retrieval;
- silent replacement of destination knowledge;
- hidden profile synchronization;
- profile learning merely because a Browser user viewed a collective entry.
Viewing is not adoption.
Retrieval is not adoption.
Recommendation is not adoption.
23. Athena Boundary
Phase 14 does not require Athena work.
No Athena-specific implementation should be introduced merely because the
project is implementing cross-profile learning.
If a future experiment explicitly requires Athena, that work must be separately
authorized and documented.
24. Testing Requirements
Phase 14 testing must cover at minimum:
- transfer candidate construction;
- source authorization;
- destination authorization;
- provenance preservation;
- profile isolation;
- applicability;
- benefit analysis;
- conflict detection;
- temporal compatibility;
- explicit adoption;
- rejection;
- revocation;
- rollback;
- versioning;
- audit preservation;
- raw-content boundary;
- deterministic behavior;
- unauthorized transfer attempts;
- cross-profile leakage attempts.
25. Completion Criteria
Phase 14 may be marked COMPLETE only when:
1. transfer contracts are implemented;
2. candidate generation is deterministic;
3. authorization is explicit;
4. source and destination identities are preserved;
5. provenance is preserved;
6. evidence remains inspectable;
7. profile isolation remains intact;
8. source memories remain immutable;
9. destination adoption is explicit;
10. adaptation does not sever provenance;
11. conflicts remain visible;
12. temporal applicability is preserved;
13. revocation propagates;
14. audit history remains immutable;
15. no raw private memory content crosses the boundary;
16. unauthorized transfers are rejected;
17. deterministic behavior is tested;
18. API/Browser surfaces, if implemented, preserve the governance contract;
19. full regression passes;
20. documentation matches implementation;
21. no Phase 15 retrieval optimization is accidentally introduced;
22. no unrestricted shared-memory mechanism is introduced.
26. Final Design Principle
A profile may learn from another profile only through an explicit, governed,
provenance-preserving transfer whose source, destination, evidence,
authorization, applicability, and revocation state remain inspectable.

Phase 14 is therefore not about making all Hermes profiles share one mind.
It is about making controlled collective learning possible without destroying
profile identity, privacy, provenance, or auditability.
