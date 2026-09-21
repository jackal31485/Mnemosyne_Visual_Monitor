# Mnemosyne Visual Monitor — Phase 17 Security Matrix

**Status:** PLANNING BASELINE
**Phase:** 17 — Governance, Audit & Security Hardening

## Purpose

This matrix defines the security-hardening surface for Phase 17 and provides traceability between threats, controls, tests, and completion evidence.

| ID | Area | Required control | Negative condition | Validation |
|---|---|---|---|---|
| 17.01 | Identity | Participant identity is explicit | Unknown identity accepted as trusted participant | Unit + negative |
| 17.02 | Discovery | Discovery exposes minimal metadata | Discovery grants authority | Negative |
| 17.03 | Trust | Trust is explicit and bounded | Trust implies authorization | Negative |
| 17.04 | Authentication | Privileged communication requires authenticated session | Unauthenticated privileged request succeeds | Negative |
| 17.05 | Authorization | Capabilities are explicit | Capability inferred or escalated | Negative |
| 17.06 | Least authority | Operations require only necessary capability | Excess authority silently granted | Negative |
| 17.07 | Session validity | Expired/revoked sessions fail closed | Stale session accepted | Negative |
| 17.08 | Exchange | Knowledge exchange is governed | Direct unrestricted write succeeds | Integration + negative |
| 17.09 | Provenance | Source identity and lineage survive exchange | Provenance silently replaced | Negative |
| 17.10 | Replay | Replayed exchange/checkpoint is detectable | Replay creates new authoritative state | Adversarial |
| 17.11 | Synchronization | Sync is idempotent | Duplicate transfer changes state | Integration |
| 17.12 | Divergence | Divergence remains visible | Conflict silently disappears | Integration + negative |
| 17.13 | Adoption | Phase 14 remains authoritative | Federation receipt directly becomes learned state | Negative |
| 17.14 | Projection | Projection is destination-owned | Projection becomes datastore replication | Negative |
| 17.15 | Revocation | Revocation remains effective | Revoked knowledge/authority remains valid | Negative |
| 17.16 | Profile isolation | Raw private memory remains profile-local | Federation leaks private memory | Negative |
| 17.17 | Audit | Audit records are append-only at application layer | Update/delete/replace succeeds | Negative |
| 17.18 | Audit privacy | Audit contains metadata, not raw memory | Raw memory appears in audit | Negative |
| 17.19 | Attribution | Security events identify actor/participant | Unattributed privileged event accepted | Negative |
| 17.20 | Validation | Invalid state fails closed | Malformed state becomes accepted state | Negative |
| 17.21 | Integrity | Corrupt/incompatible state is detected | Corrupt state silently loads | Integrity test |
| 17.22 | Migration | Migration safety is explicit | Partial migration creates ambiguous state | Migration test |
| 17.23 | Recovery | Recovery preserves governance | Recovery bypasses authorization | Recovery test |
| 17.24 | Observability | Security failures are observable | Failure leaves no diagnostic evidence | Integration |
| 17.25 | Diagnostics | Diagnostics remain observational | Diagnostic path creates authority | Negative |
| 17.26 | Federation boundary | Remote agents remain external participants | Remote service becomes implicit local memory | Negative |
| 17.27 | Athena boundary | Athena remains excluded unless explicitly enabled later | Athena participates implicitly | Static + negative |
| 17.28 | Network failure | Network failure cannot corrupt governance | Partial transfer creates ambiguous authority | Adversarial |
| 17.29 | Stale authority | Stale authorization is rejected | Expired/revoked authority remains usable | Adversarial |
| 17.30 | Completion | Security evidence is traceable | Phase marked complete without required validation | Completion audit |

### 17G Temporal Session Evidence

The federation session boundary now provides explicit temporal validity
evaluation through `session_is_active(session, at=...)`. The governed
`receive_remote_knowledge()` boundary requires an operation timestamp and
rejects an authenticated session at or after its configured expiration.

Evidence:
- `tests/unit/test_federation_session.py`
- `tests/unit/test_federation_exchange.py`
- targeted 17G/security suite: 61 passed
- full regression: 1,657 passed, 14 skipped, 4 warnings

## Threat Categories

### T1 — Identity Confusion

- unknown peer;
- duplicate participant identity;
- conflicting identity;
- spoofed source;
- mismatched participant type.

### T2 — Trust Confusion

- discovery treated as trust;
- trust treated as authorization;
- expired trust treated as active;
- revoked trust treated as valid.

### T3 — Authorization Escalation

- capability escalation;
- unauthorized collective read;
- unauthorized collective write;
- unauthorized knowledge request;
- unauthorized knowledge receipt.

### T4 — Session Abuse

- replayed session;
- expired session;
- revoked session;
- unauthenticated request;
- mismatched participant/session.

### T5 — Knowledge Integrity

- provenance substitution;
- lineage mismatch;
- duplicate exchange;
- replay;
- stale receipt;
- fabricated adoption lineage.

### T6 — Privacy Leakage

- raw private memory in collective state;
- raw private memory in audit;
- remote direct datastore access;
- unauthorized profile crossing.

### T7 — Revocation Bypass

- revoked participant continues exchange;
- revoked knowledge remains retrievable;
- stale projection remains authoritative;
- revocation history is erased.

### T8 — State Corruption

- partial synchronization;
- invalid transition;
- corrupt persisted state;
- incompatible migration;
- failed recovery.

### T9 — Audit Integrity

- audit deletion;
- audit replacement;
- duplicate audit identity;
- missing attribution;
- diagnostic mutation of authority.

## Required Evidence

Every implemented control must have traceable evidence in one or more of:

- unit test;
- negative governance test;
- integration test;
- adversarial test;
- migration/integrity test;
- regression result;
- static analysis;
- completion audit.

No security claim is complete without evidence.
