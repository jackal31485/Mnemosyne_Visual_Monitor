# Phase 16 — Federation Matrix

**Status:** ACTIVE  
**Architectural checkpoint:** `phase-16-start` → `44d3e53`

## 1. Participant matrix

| Participant | Identity | Local/private memory | Discover | Authenticate | Receive governed knowledge | Adopt/project | Notes |
|---|---|---:|---:|---:|---:|---:|---|
| Local Mnemosyne instance | Explicit instance ID | Yes | Yes | Yes | Yes | Yes | Authority for its own domain |
| Local profile | Explicit profile ID | Yes | Scoped | N/A | Scoped | Yes | Remains isolated |
| Local model | Explicit participant/profile ID | Indirect | Scoped | N/A | Scoped | Governed | Jeeves/Boss/Hawk/Pope |
| Remote Mnemosyne instance | Explicit instance ID | Remote | Yes | Yes | If authorized | If authorized | Peer federation |
| Remote agent service | Explicit service/participant ID | External | Yes | Yes | If authorized | If authorized | Friday is an example |
| Federation governance actor | Explicit actor ID | N/A | Yes | Yes | By policy | Explicit authorization | Does not bypass audit |

## 2. Trust and authorization matrix

| State | Discovery | Identity | Trust | Authentication | Capability authorization | Knowledge exchange | Adoption |
|---|---:|---:|---:|---:|---:|---:|---:|
| DISCOVERED | ✓ | Partial | ✗ | ✗ | ✗ | ✗ | ✗ |
| IDENTIFIED | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| TRUST-ESTABLISHED | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| AUTHENTICATED | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| AUTHORIZED | ✓ | ✓ | ✓ | ✓ | ✓ | Scoped | ✗ |
| EXCHANGE-ELIGIBLE | ✓ | ✓ | ✓ | ✓ | ✓ | Scoped | Only through Phase 14 governance |
| BLOCKED | Metadata only | ✓ | Invalid | Invalid | ✗ | ✗ | ✗ |
| REVOKED | Historical visibility | ✓ | Revoked | Denied | ✗ | ✗ | ✗ |

## 3. Peer lifecycle

| State | Meaning | May request governed data? | May modify destination state? |
|---|---|---:|---:|
| DISCOVERED | Network metadata observed | No | No |
| IDENTIFIED | Participant identity associated | No | No |
| TRUST-ESTABLISHED | Explicit trust relationship | No, unless separately authorized | No |
| AUTHENTICATED | Participant proves identity | No, unless separately authorized | No |
| AUTHORIZED | One or more capabilities granted | Only within capability scope | No |
| EXCHANGE-ELIGIBLE | Authorized for relevant exchange | Yes, scoped | No |
| BLOCKED | Participant denied | No | No |
| REVOKED | Access withdrawn | No | No |
| EXPIRED | Time-bounded relationship ended | No | No |

## 4. Knowledge-state matrix

| State | Origin | Ordinary collective retrieval | Adoptable | Revocable | Audit retained |
|---|---|---:|---:|---:|---:|
| Profile-local private memory | Local profile | Profile-scoped only | Not directly | Profile governance | Yes |
| Governed collective knowledge | Local collective | Yes if existing governance permits | Candidate source | Yes | Yes |
| Remote received | Federation exchange | No by default | Not yet | Yes | Yes |
| Remote validated | Federation exchange | Scoped | Potentially | Yes | Yes |
| Remote eligible | Federation exchange | Scoped | Yes after authorization | Yes | Yes |
| Remote adopted | Destination-derived | Yes if destination governance permits | Already adopted | Yes | Yes |
| Remote revoked | Prior exchange/adoption | No as valid knowledge | No | N/A | Yes |
| Conflicted | Federation exchange | Not as unqualified authoritative result | Requires governance | Yes | Yes |
| Agent knowledge projection | Governed/derived | Only to authorized participant | Scoped | Yes | Yes |

## 5. Federation operation matrix

| Operation | Identity | Trust | Authentication | Capability | Phase 14 governance |
|---|---:|---:|---:|---:|---:|
| Discover | No | No | No | No | No |
| Register peer | Yes | Policy-dependent | No/initial | No | No |
| Establish trust | Yes | Explicit action | Appropriate mechanism | Trust capability | No |
| Authenticate | Yes | Expected trust | Yes | Session capability | No |
| Request metadata | Yes | Yes | Yes | Metadata capability | No |
| Request governed knowledge | Yes | Yes | Yes | Knowledge-read | If adoption intended |
| Send governed knowledge | Yes | Yes | Yes | Exchange-write | Destination processing |
| Receive governed knowledge | Yes | Yes | Yes | Exchange-read | Candidate/validation |
| Synchronize | Yes | Yes | Yes | Sync | Governed per item |
| Detect conflict | Yes | Yes | Yes | Sync/exchange | No |
| Adopt | Yes | Yes | Yes | Adoption | Yes |
| Create projection | Yes | Yes | Yes | Projection | Destination governance |
| Revoke | Yes | Yes | Yes | Revocation | Phase 14 revocation |
| Propagate revocation | Yes | Yes | Yes | Revocation notification | History retained |

## 6. Data exposure matrix

| Data class | Discovery | Trusted peer | Authorized peer | Agent projection | Default remote exposure |
|---|---:|---:|---:|---:|---:|
| Instance identity | Limited | Yes | Yes | Yes | Limited |
| Hostname/display name | Optional | Yes | Yes | Yes | Optional |
| Peer capabilities | No | Scoped | Scoped | Scoped | No |
| Trust state | No | Self/controlled | Scoped | Scoped | No |
| Collective entry identity | No | Scoped | Yes | Yes | No |
| Governed collective knowledge | No | No | Scoped | Scoped | No |
| Provenance | No | No | Required with knowledge | Required | No |
| Temporal metadata | No | No | Scoped with knowledge | Scoped | No |
| Profile-local raw memory | **Never by default** | **Never by default** | **Never by default** | **Never by default** | **Never** |
| Private prompts/notes | **Never** | **Never** | **Never** | **Never** | **Never** |
| Credentials/secrets | **Never** | **Never** | **Never** | **Never** | **Never** |
| Local audit history | No direct mutation | Read only if explicitly exposed | Controlled read | Controlled subset | No remote write |

## 7. Agent projection matrix

| Projection target | Source | Allowed content | Raw private memory | Provenance | Revocation |
|---|---|---|---:|---:|---:|
| Local model participant | Governed collective | Authorized knowledge | No | Required | Required |
| Remote Mnemosyne instance | Governed collective | Authorized governed knowledge | No | Required | Required |
| Remote agent service | Governed collective / destination-derived | Authorized projection | No | Required | Required |

A projection is a governed view/derived representation, not unrestricted database replication.

## 8. Failure matrix

| Failure | Required behavior |
|---|---|
| Unknown participant | Reject privileged operation; retain observable failure |
| Discovery without trust | Permit discovery metadata only |
| Trust without authorization | Reject governed knowledge operation |
| Authentication failure | Fail closed |
| Capability mismatch | Reject operation |
| Invalid provenance | Reject/quarantine; do not silently repair |
| Revoked source knowledge | Reconcile as revoked; do not silently treat as current |
| Duplicate exchange | Idempotently recognize existing exchange |
| Partial transfer | Retry safely without duplicate adoption |
| Synchronization divergence | Surface conflict/divergence |
| Remote datastore mutation attempt | Reject |
| Audit deletion request | Reject |
| Private-memory request | Reject by default |
| Projection beyond scope | Reject |
| Network timeout | Preserve governance state; retry only idempotently |

## 9. Phase 14 lineage

| Phase 14 capability | Phase 16 extension |
|---|---|
| Transfer candidate | Candidate generated from governed remote exchange |
| Applicability | Evaluates destination participant/profile applicability |
| Explicit authorization | Remains explicit after network exchange |
| Adoption | Produces destination-local derived state |
| Transfer provenance | Preserved through exchange and projection |
| Conflict handling | Federation surfaces conflicts before/around adoption |
| Revocation | Propagated across peer boundary |
| Immutable transfer audit | Federation adds exchange/session/peer audit without replacing transfer audit |

## 10. Negative-governance test targets

- discovery MUST NOT equal trust;
- trust MUST NOT equal unrestricted authorization;
- authentication failure MUST fail closed;
- capability mismatch MUST reject;
- private raw memory MUST NOT be exposed by default;
- provenance MUST NOT be stripped;
- received knowledge MUST NOT become adopted solely because it was received;
- remote visibility MUST NOT automatically create retrieval/graph state;
- revoked knowledge MUST remain governed as revoked;
- duplicate exchanges MUST NOT duplicate adoption;
- partial transfers MUST be retry-safe;
- remote peers MUST NOT directly mutate destination datastores;
- remote peers MUST NOT delete local audit history;
- agent projections MUST remain capability-scoped;
- local-model and remote-agent participant classes MUST remain explicit.
