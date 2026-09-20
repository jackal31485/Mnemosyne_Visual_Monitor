# Phase 16 — Governance Invariants

**Status:** ACTIVE / AUTHORITATIVE  
**Architectural checkpoint:** `phase-16-start` → `44d3e53`

Every Phase 16 implementation task MUST be traceable to one or more invariants below. Every invariant MUST have corresponding tests, including negative cases where applicable.

## Identity

### INV-16.01 — Participant identity is explicit
Every federation participant has a stable identifier independent of hostname, network address, profile name, or connection.

### INV-16.02 — Identity is not trust
Knowing a participant's identity does not establish trust.

### INV-16.03 — Participant type is explicit
A participant MUST declare its architectural class, including `LOCAL_MODEL`, `LOCAL_PROFILE`, `REMOTE_MNEMOSYNE_INSTANCE`, or `REMOTE_AGENT_SERVICE` as applicable.

### INV-16.04 — Remote agent services are not local models
A remote agent/service participant MUST NOT be modeled as a local downloaded model merely to simplify federation.

## Discovery and trust

### INV-16.05 — Discovery is not trust
Network discovery establishes visibility only.

### INV-16.06 — Discovery exposes minimal metadata
Discovery MUST NOT expose private memory, credentials, authorization grants, or unrestricted endpoints by default.

### INV-16.07 — Trust is explicit
Trust MUST be established through an explicit governed mechanism.

### INV-16.08 — Trust is not authorization
A trusted participant does not automatically receive knowledge-access capabilities.

### INV-16.09 — Trust can expire or be revoked
Trust state MUST support explicit withdrawal or expiration.

## Authentication and capabilities

### INV-16.10 — Privileged communication is authenticated
Federation operations involving protected knowledge or state MUST authenticate the communicating participant.

### INV-16.11 — Authentication failure fails closed
Authentication failure MUST NOT degrade into anonymous privileged access.

### INV-16.12 — Capabilities are explicit
Knowledge, synchronization, projection, adoption, and revocation operations MUST be capability-scoped.

### INV-16.13 — Least authority applies
A participant receives only the capabilities required for its authorized federation role.

## Data isolation

### INV-16.14 — Profile isolation survives federation
Federation MUST NOT merge profile-local private memory stores.

### INV-16.15 — Raw private memory is not exposed by default
A federation exchange MUST NOT expose raw private memory merely because a peer is trusted or connected.

### INV-16.16 — Collective governance precedes federation
Only knowledge eligible under collective governance may be exchanged as governed collective knowledge.

### INV-16.17 — No unrestricted shared writes
A remote participant MUST NOT receive arbitrary write access to a local Mnemosyne datastore.

### INV-16.18 — Remote direct datastore mutation is prohibited
Federation APIs MUST operate through governed domain contracts rather than permitting remote peers to mutate local tables directly.

## Provenance

### INV-16.19 — Provenance survives exchange
Knowledge crossing a federation boundary MUST retain its source provenance.

### INV-16.20 — Source identity remains attributable
A destination MUST be able to identify the source participant/instance associated with exchanged knowledge.

### INV-16.21 — Exchange identity is stable
Each governed exchange has a stable identifier suitable for idempotency and audit.

### INV-16.22 — Provenance cannot be silently replaced
Destination processing MUST NOT silently overwrite source lineage with destination identity.

## Adoption and projection

### INV-16.23 — Receipt is not adoption
Receiving remote knowledge MUST NOT automatically create adopted destination state.

### INV-16.24 — Validation is not adoption
Successful validation alone MUST NOT authorize adoption.

### INV-16.25 — Phase 14 authorization remains authoritative
Federation MUST NOT bypass the Phase 14 transfer authorization contract.

### INV-16.26 — Adoption is auditable
Every federation-derived adoption MUST have an attributable audit trail.

### INV-16.27 — Destination state remains destination-owned
Adopted knowledge is represented as destination-local derived state rather than a writable alias to remote state.

### INV-16.28 — Agent projections are governed
A participant-specific knowledge projection MUST have an explicit source, scope, authorization context, and provenance.

### INV-16.29 — Projection is not database replication
An agent-specific projection MUST NOT be implemented as unrestricted replication of `collective.db`.

### INV-16.30 — External agent memory is not Mnemosyne memory
Federation MUST exchange governed Mnemosyne knowledge rather than assuming hidden/proprietary memory belonging to an external agent service is directly exportable or writable.

## Revocation

### INV-16.31 — Revocation remains authoritative
Revoked knowledge or revoked transfer authorization MUST remain non-valid according to existing governance rules.

### INV-16.32 — Revocation propagates
Where a federated dependency is revoked, relevant destination state MUST become governed accordingly rather than silently remaining valid.

### INV-16.33 — Revocation is observable
Revocation propagation MUST be represented in audit/diagnostic state.

### INV-16.34 — Revocation does not erase history
Revocation MUST NOT destructively delete the historical transfer or exchange record.

## Synchronization

### INV-16.35 — Synchronization is governed
Synchronization MUST operate through explicit exchange contracts and authorization boundaries.

### INV-16.36 — Synchronization is idempotent
Retries and duplicate messages MUST NOT produce duplicate governed state.

### INV-16.37 — Partial synchronization is safe
A failed or partial transfer MUST NOT leave governance in an ambiguous state that grants unintended access.

### INV-16.38 — Divergence is visible
Conflicting or divergent remote state MUST remain detectable and attributable.

## Audit

### INV-16.39 — Federation activity is auditable
Relevant discovery, trust, authentication, authorization, exchange, synchronization, conflict, adoption, projection, and revocation activity MUST be auditable.

### INV-16.40 — Audit history is immutable to peers
Remote participants MUST NOT delete or rewrite local audit history.

### INV-16.41 — Audit attribution is explicit
Audit records MUST identify the participant/actor and operation context where available.

## Conflict and failure safety

### INV-16.42 — Conflicts remain visible
Federation MUST NOT silently conceal competing versions, provenance conflicts, or revocation conflicts.

### INV-16.43 — Invalid governance state fails closed
Invalid authorization, invalid provenance, invalid identity, and capability violations MUST fail closed.

### INV-16.44 — Network failure does not corrupt governance
Timeouts, disconnects, and retries MUST NOT bypass or silently mutate governance state.

## Phase boundaries

### INV-16.45 — Phase 17 remains a distinct hardening phase
Phase 16 may identify security concerns but MUST preserve the Phase 17 boundary for broader adversarial/security hardening unless an explicit phase decision changes scope.

### INV-16.46 — Athena is not an implicit participant
No federation implementation may silently activate or modify Athena participation.

### INV-16.47 — Existing Phase 14 governance remains intact
Phase 16 may extend Phase 14 for networked exchange but MUST NOT weaken candidate, applicability, authorization, adoption, conflict, revocation, or rollback guarantees.

## Enforcement rule

For every implementation change:

1. identify the governing invariant(s);
2. add or update positive tests;
3. add negative tests for prohibited behavior where relevant;
4. run targeted tests;
5. run the full suite before completion;
6. verify documentation and invariant references before the Phase 16 completion tag.
