# Phase 16 — Distributed Collective / LAN Federation

**Status:** ACTIVE  
**Started:** 2026-09-20  
**Architectural checkpoint:** `phase-16-start` → `44d3e53`  
**Predecessor:** Phase 15 — Advanced Retrieval Optimization  
**Successor:** Phase 17 — Governance, Audit & Security Hardening

## 1. Purpose

Phase 16 extends Mnemosyne from a governed single-instance collective into a controlled federation across a LAN or other explicitly authorized network boundary.

Federation is not database replication. Network visibility, trust, authorization, knowledge exchange, and adoption are separate concepts.

```text
Network visibility
       ≠
Trust
       ≠
Authentication
       ≠
Authorization
       ≠
Knowledge exchange
       ≠
Adoption
```

The Phase 16 objective is to permit governed knowledge exchange between Mnemosyne instances and other explicitly modeled federation participants while preserving profile isolation, provenance, revocation, auditability, and Phase 14 transfer governance.

## 2. Architectural principle

The authoritative federation lifecycle is:

```text
Profile-local memory
       ↓
Governed collective knowledge
       ↓
Federation exchange
       ↓
Remote governed knowledge
       ↓
Validation / applicability
       ↓
Explicit authorization
       ↓
Explicit adoption / projection
       ↓
Destination-local derived state
```

Remote visibility never implies adoption.

## 3. Federation participants

Phase 16 uses a generic federation participant abstraction rather than treating every participant as an Ollama/local model.

Initial participant classes are:

```text
LOCAL_MODEL
LOCAL_PROFILE
REMOTE_MNEMOSYNE_INSTANCE
REMOTE_AGENT_SERVICE
```

Examples:

```text
Jeeves  → LOCAL_MODEL
Boss    → LOCAL_MODEL
Hawk    → LOCAL_MODEL
Pope    → LOCAL_MODEL
Friday  → REMOTE_AGENT_SERVICE
```

A participant has an explicit identity, capabilities, trust state, authorization context, and knowledge projection policy. A remote agent service may consume governed Mnemosyne knowledge without receiving the collective database or private profile memory.

Mnemosyne federation operates on governed Mnemosyne knowledge. It does not assume that hidden or proprietary memory belonging to an external agent service is exportable, writable, or equivalent to Mnemosyne collective memory.

## 4. Non-negotiable boundaries

Phase 16 MUST preserve:

1. Profile-local memory remains isolated.
2. Raw private memory is not exposed by default.
3. Collective knowledge remains governed.
4. Provenance remains attached to exchanged knowledge.
5. Source and destination identities remain explicit.
6. Trust does not imply authorization.
7. Authorization remains explicit and scoped.
8. Adoption remains explicit.
9. Agent-specific projections remain governed.
10. Revocation remains enforceable.
11. Conflicts remain visible and attributable.
12. Federation activity remains auditable.
13. Audit history is not destructively deleted.
14. Peer visibility does not constitute adoption.
15. Federation does not create unrestricted shared writes.
16. Athena is not an implicit federation participant.

## 5. Relationship to Phase 14

Phase 14 remains the authoritative knowledge-transfer governance boundary.

```text
candidate
   ↓
applicability
   ↓
authorization
   ↓
adoption
   ↓
revocation / rollback
```

Phase 16 places a federation boundary around this process:

```text
LAN discovery
    ↓
Federation participant
    ↓
Peer identity
    ↓
Trust
    ↓
Authentication
    ↓
Capability authorization
    ↓
Governed exchange
    ↓
Phase 14 candidate / applicability
    ↓
Phase 14 authorization
    ↓
Phase 14 adoption
    ↓
Destination-local derived state / agent projection
```

Federation MUST NOT bypass Phase 14 governance.

## 6. Historical architecture lineage

Phase 6.5C introduced LAN discovery, trust, adoption, provenance, and remote-agent concepts. Those concepts remain useful lineage, but the historical `DISCOVERED → KNOWN → TRUSTED → ADOPTED` state model is not authoritative for Phase 16.

The modern model separates discovery, identity, trust, authentication, capability authorization, exchange, validation, authorization, adoption, and revocation.

The historical `IncrementalCollectiveScanner` is also treated as a legacy integration path. It MUST NOT become an implicit bypass around federation governance. Phase 16 will map and, where necessary, gate or refactor that path rather than silently preserving unrestricted remote insertion.

## 7. Discovery

Discovery is metadata-only.

A discovery payload may contain:

- participant/client identifier;
- hostname or display name where appropriate;
- installed version or protocol version.

Discovery MUST NOT broadcast:

- memory contents;
- private profile data;
- credentials or secrets;
- authorization grants;
- raw collective entries;
- endpoint URIs unless explicitly established through a trusted mechanism.

Discovery establishes visibility only. It does not establish trust or authorization.

## 8. Peer lifecycle

```text
DISCOVERED
    ↓
IDENTIFIED
    ↓
TRUST-ESTABLISHED
    ↓
AUTHENTICATED
    ↓
AUTHORIZED
    ↓
EXCHANGE-ELIGIBLE
```

A peer may additionally become `BLOCKED`, `REVOKED`, or `EXPIRED`.

These states are distinct from knowledge adoption.

## 9. Identity

Every federation participant MUST have a stable identity distinct from hostname, network address, profile name, transport connection, trust state, and authorization state.

Existing `AgentEndpoint.agent_id` is a useful lineage primitive, but Phase 16 will establish the richer federation participant/peer contract around it.

## 10. Trust and authentication

Trust is an explicit governance relationship. Authentication proves that a connection is associated with the expected participant identity; neither fact grants unrestricted knowledge access.

Privileged federation communication MUST authenticate the communicating participant and MUST fail closed on authentication failure.

The historical one-time pairing mechanism may inform implementation, but Phase 16 does not treat it as the final security architecture. Broader adversarial/security hardening belongs to Phase 17.

## 11. Capabilities and authorization

Federation authorization is capability-scoped.

Potential capabilities include discovery, authenticated sessions, governed knowledge requests/submission, revocation notifications, synchronization, and agent-specific projection consumption.

Capabilities MUST be explicit, enforceable, and least-privilege.

Trust MUST NOT imply all capabilities.

## 12. Governed knowledge exchange

Federation exchanges governed knowledge envelopes rather than arbitrary database rows.

An exchange envelope SHOULD identify:

- exchange identifier;
- source and destination participant/instance;
- source governance/provenance;
- knowledge identity and version/state;
- evidence/derivation references where applicable;
- temporal/provenance metadata;
- authorization and capability context;
- revocation state;
- integrity/authentication metadata.

Raw private memory MUST NOT be included by default.

## 13. Agent-specific knowledge projections

The collective remains the governed source. Participants receive projections appropriate to their identity, capabilities, and authorized scope.

```text
                         COLLECTIVE
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
         Friday            Jeeves            Boss
            │                │                │
       projection        projection        projection
```

A projection is not a copy of `collective.db` and is not a replacement for the participant's local memory system.

A projection MUST preserve the provenance and governance needed to explain why the participant can see the knowledge and what destination-side state, if any, was derived from it.

## 14. Synchronization

Synchronization is governed exchange, not blind replication.

The implementation MUST support, as applicable:

- stable exchange identifiers;
- duplicate detection;
- idempotent processing;
- remote version tracking;
- synchronization checkpoints;
- retry-safe behavior;
- partial-transfer safety;
- visible divergence;
- observable synchronization status.

A network retry MUST NOT create duplicate adoption or silently alter governance history.

## 15. Conflict handling

Federation conflicts MUST remain visible and attributable.

Potential conflict classes include competing knowledge versions, incompatible provenance, source revocation versus destination state, participant capability mismatch, synchronization divergence, and stale remote state.

Phase 16 may identify and surface conflicts. It must not introduce unrestricted automatic conflict resolution. Broader conflict/security policy belongs in Phase 17 where appropriate.

## 16. Adoption and destination state

Receipt is not adoption.

```text
REMOTE RECEIVED
      ↓
VALIDATED
      ↓
ELIGIBLE
      ↓
EXPLICIT AUTHORIZATION
      ↓
EXPLICIT ADOPTION / PROJECTION
      ↓
DESTINATION-LOCAL DERIVED STATE
```

Phase 14's transfer candidate, applicability, authorization, adoption, and revocation contracts remain authoritative.

Destination-local representations MUST retain source-to-destination provenance and MUST NOT become an excuse to copy raw private source memory.

## 17. Revocation propagation

Source-side revocation MUST remain enforceable across federation boundaries.

A revoked source knowledge item or revoked transfer authorization MUST NOT remain silently retrievable or usable as valid adopted knowledge where governance requires revocation.

Revocation events remain auditable. Audit history is not deleted to make revocation appear as though the transfer never occurred.

## 18. Existing remote-agent interfaces

`AgentEndpoint` and `AgentMemoryClient` provide an existing read-only transport abstraction. Phase 16 should retain the useful transport separation while adding federation governance around it.

`AgentMemoryReference` remains useful for identifying source agent/profile/memory lineage without embedding raw memory content in collective representations.

`IncrementalCollectiveScanner` requires explicit Phase 16 review because its current remote inventory-to-collective path predates the full federation governance model.

## 19. Observability and audit

Federation activity MUST be observable and auditable, including where applicable:

- participant discovery;
- identity establishment;
- trust changes;
- authentication outcomes;
- capability grants/rejections;
- exchange requests/outcomes;
- synchronization checkpoints;
- conflicts;
- validation;
- adoption/projection;
- revocation;
- failures.

Audit records are append-oriented and MUST NOT be remotely deleted or rewritten by a peer.

## 20. Testing strategy

Phase 16 tests MUST include positive and negative governance cases:

- participant identity validation;
- discovery without trust;
- trust without unrestricted authorization;
- authentication failure;
- capability mismatch;
- unauthorized exchange rejection;
- raw private-memory exposure rejection;
- provenance preservation;
- exchange idempotency;
- duplicate handling;
- partial transfer recovery;
- conflict visibility;
- explicit adoption;
- revocation propagation;
- remote audit immutability;
- remote direct-database mutation rejection;
- participant-specific projection boundaries.

## 21. Phase 16 work breakdown

### 16A — Federation foundation and participant identity
Define participant types, instance identity, peer identity, and stable identifiers.

### 16B — Peer discovery and records
Define LAN discovery, peer records, discovery payload boundaries, and lifecycle state.

### 16C — Trust establishment
Define explicit trust establishment, expiration, blocking, and revocation.

### 16D — Authenticated communication
Define authenticated federation sessions and fail-closed transport behavior.

### 16E — Capabilities and authorization
Define capability-scoped access and participant-specific authorization.

### 16F — Governed knowledge exchange
Define exchange envelopes, provenance, validation boundaries, and remote knowledge receipt.

### 16G — Synchronization and idempotency
Define checkpoints, duplicate handling, retries, versions, and divergence visibility.

### 16H — Conflict detection and visibility
Define conflict records and attributable conflict handling.

### 16I — Explicit adoption and knowledge projections
Integrate Phase 14 transfer governance and define governed agent-specific projections.

### 16J — Revocation propagation
Propagate source and transfer revocation while preserving immutable history.

### 16K — Observability and audit
Expose federation lifecycle and exchange activity through governed audit records and diagnostics.

### 16L — Integrated validation and closure
Run full federation validation, negative governance tests, regression suite, GUI validation where applicable, documentation reconciliation, and completion audit.

## 22. Completion criteria

Phase 16 is complete only when:

- participant identity is explicit;
- discovery is separated from trust;
- trust is separated from authorization;
- privileged communication is authenticated;
- capabilities are enforced;
- governed knowledge exchange works;
- provenance survives federation;
- synchronization is idempotent and observable;
- conflicts are visible;
- Phase 14 adoption remains authoritative;
- agent-specific projections are governed;
- revocation propagates correctly;
- federation audit history is immutable;
- profile-local raw memory remains protected;
- negative governance tests pass;
- the complete test suite passes;
- GUI validation is complete where applicable;
- Phase 16 documentation and completion audit are reconciled;
- a Phase 16 completion commit and tag establish the boundary to Phase 17.

## 23. Phase 17 boundary

Phase 16 establishes federation architecture and governance boundaries.

Phase 17 performs broader governance, audit, adversarial, and security hardening. Phase 16 MUST NOT silently expand into unrestricted security redesign merely because a security concern is discovered; concerns must be captured and routed to the appropriate phase boundary.
