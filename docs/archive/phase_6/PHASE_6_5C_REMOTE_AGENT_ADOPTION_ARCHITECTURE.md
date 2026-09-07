# Phase 6.5C – Remote‑Agent Adoption Architecture (Design Document)

> **Note:** This document is a pre-resolution design artifact for reference. The authoritative architecture contract is `PHASE_6_5C_IMPLEMENTATION_SPECIFICATION.md`. When inconsistencies exist between this document and the spec, the spec governs.

## 1. Architecture Overview
```
+-----------------+
|   LAN Bus       |
+--------+--------+
         |
DISCOVERED ----KNOWN----TRUSTED----> ADOPTED -->
    (network)   (metadata)  (auth)       (memory sync)
``` 

### Discovery
Pass‑through multicast/mDNS that reveals a client’s non‑sensitive metadata. No memory is exchanged.

### Known
User explicitly saves the discovered host as **Known**.

### Trusted
Local user grants a communication channel (e.g., mutual TLS, pairing code). This grants authorization to send/read meta but not memories.

### Adopted
User selects memories/categories to copy. Those copies retain provenance.

## 2. Threat / Privacy Model
| Goal | Threat | Mitigation |
|------|--------|------------|
| Local memories hidden from untrusted LAN participants | Remote scan of DB files | No DB traffic unless trust is granted |
| Remote agents cannot enumerate local memories | Passive snooping on multicast | Metadata only in discovery; no secret tokens emitted |
| User sees clear status for each remote agent | Unintentional auto‑adoption | Strict state machine – adoption requires UI confirmation |

## 3. DISCOVERED State
Data stored locally (in a discovery store):

Per authoritative spec §3, the broadcast payload is restricted to:
- `client_id` (UUID) — required
- Hostname / display name — optional
- Installed software version — optional

**Must NOT include:** `profile_count`, `endpoint_url` or any endpoint URIs (IP/host/port), memory information, credentials, constellation data, or database paths.

No secrets, keys, or memory data shared.
The agent that performed discovery never receives any data back.

## 4. KNOWN State
User explicitly records the discoverer as “Known”. Still no authorization; UI explicitly warns: “Known ➜ NOT TRUSTED – memories invisible.”

## 5. TRUSTED State
Authorization options (documented, but not yet chosen):
| Mechanism | Pros / Cons |
|-----------|-------------|
| Mutual TLS | Strong assurance; needs certificate infrastructure per‑device. Heavy for home LAN. |
| One‑time pairing code | Minimal setup: user scans QR or enters code. Lightweight, no PKI. Revocation achieved by deleting a short‑lived token. |
| Persistent device PIN | Simple but insecure if PIN guessed; can enforce rate limit + back‑off on login attempts. |

**Chosen for Phase 6.5C prototype:** One‑time pairing code – easiest to roll out, no PKI, revocable instantly.

## 6. ADOPTED State
User chooses granularity in the Adoption Wizard. **Per‑memory selection is the primary and only initial mechanism.** 

Granularity order of precedence (authoritative spec §5):
1. Per-memory item — primary, Phase 6.5C scope only
2. Category/tag — future expansion (not Phase 6.5C)
3. Selected collection — future expansion (not Phase 6.5C)
4. Entire profile — NOT the default; not an initial option

**Provenance schema (`AdoptedMemoryMeta`)**
```json
{
  "origin_client": "str",
  "origin_profile": "str",
  "origin_memory_id": "str",
  "original_timestamp": "datetime",
  "adopted_at": "datetime"
}
```

Local storage keeps two columns:
1. `memory` JSON blob
2. `provenance_json` string

When rendering in the UI, a toggle shows “Remote‑origin” vs “Local”.

## 7. State Transition Diagram (textual)

**Clarification:** Each transition requires EXPLICIT user action — no auto-transitions at any stage. This is now codified in the authoritative spec §1.

```
DISCOVERED --[explicit user action]--> KNOWN --[pairing code + explicit user action]--> TRUSTED --[explicit per-memory selection]--> ADOPTED
[Optional] UNKNOWN -> DISCOVERED via re‑scan (agent can be re-discovered after disconnection; trust/adoption records are preserved)
```

Transitions are only one-way except for revocation pathways described in §12. Stale agents (no broadcast for >30 seconds) are marked stale but not removed from the list.

## 8. Permission Model
| Capability | Granted at which state? | Target action |
|------------|------------------------|---------------|
| List remote profiles | TRUSTED | `GET /remote/profiles` |
| Read raw metadata | TRUSTED | `GET /remote/profile/{id}/metadata` |
| Import memories | ADOPTED | `POST /local/memories/import` |

All API endpoints require a per‑client auth token that is generated during the TRUSTED transition (pairing token → TLS cert or bearer header). That token is never shared with local peers.

## 9. Authentication Options (summarized)
| Option | Trade‑offs |
|--------|------------|
| Mutual TLS | Highest security, but requires a CA per device. |
| One‑time Pairing Code | Low overhead, easy revocation by deleting session entry. |
| Short‑lived JWT with embedded client ID | Requires an auth server; may be overkill for LAN. |

**Recommendation:** Use One‑time pairing code for Phase 6.5C and reserve mutual TLS for later security‑critical deployments.

## 10. Discovery Options (summarized)
| Mechanism | Pros | Cons |
|-----------|------|------|
| UDP Multicast | Simple, reliable on LAN. No extra services required. | Some networks block multicast; may not discover in bridged/virtual environments. |
| mDNS (bonjour) | Discoverable by hostname; integrates with OS UI. | Requires an Avahi/Bonjour agent; overkill for a few devices. |
| DNS‑SRV or central server polling | Centralized registry; easy to audit. | Needs an authoritative zone / server on the LAN. |

## Recommendation for Phase 6.5C: UDP Multicast only (no HTTP `/api/discovery` endpoint). Payload must match the authoritative spec §3 exactly — `client_id`, optional hostname, optional version only. **No endpoint URIs in broadcasts.** If multicast proves unsuitable, evaluate mDNS later; do not implement in 6.5C.

## 11. Adoption Workflow
1. User scans pairing code from remote UI → local app stores token.
2. App validates token by querying `/remote/verify-token`.
3. If validation passes, transition to TRUSTED; an auth token is issued.
4. User opens Adoption Wizard → selects memories.
5. For each selected memory: `GET /remote/memory/{id}` (with auth).
6. POST to local `/memories/import` includes provenance_json.
7. UI displays toggles “Remote‑origin” per node.

## 12. Provenance Model
Every adopted memory contains `origin_client`, `origin_profile` and a unique `origin_memory_id`. Queries can filter:
```sql
SELECT * FROM memories WHERE provenance_remote = '12345678' -- remote client ID
```
When revoking an adopted client's trust, all `provenance_origin_client = <client>` entries should be flagged as revoked but NOT deleted automatically. User is prompted to either:
| Option | Result |
|-----|--------|
| Keep memories (stale flag) | Prevents future sync; memory stays in local database with provenance flag. |
| Delete all adopted memories | Permanently removes them. |

## 13. Revocation Model
| Action | Effect |
|--------|--------|
| Revoke Trust | Disconnect auth token, close any open streams. Adopted memories remain but are marked revoked; no further sync allowed. |
| Revoke Adoption | Mark all memories with that provenance as retracted. Remote client still visible in “Known”. No future updates for those memories. |
| Client disappears from LAN | No new actions. Local UI drops them from DISCOVERED list after X minutes of silence. User can re‑discover. |
| Credential compromised | Invalidate token immediately; local user must revoke the Trust state and optionally delete adopted memories. |

## 14. Synchronization Protocol (DEFERRED)

**No automatic background synchronization in Phase 6.5C.** All sync protocol choices below are deferred to future phases and may be revisited when sync work begins.

Phase 6.5C defines only a stub endpoint: `GET /api/sync?since=<timestamp> → {}` returning empty body with 200 OK — no sync logic, no change-feed, no conflict resolution.

| Layer | Phase 6.5C status |
|-------|-------------------|
| Change Feed | DEFERRED - do not implement or imply in 6.5C |
| Version numbers / timestamps | DEFERRED |
| Verification & hash comparison | DEFERRED |
| Incremental download | DEFERRED |
| Handling deletes / revokes | DEFERRED |

When sync work begins post-prototype: evaluate SSE, WebSocket, or HTTP polling per user's operational experience with the adoption workflow. The specific recommendation made below has no force in Phase 6.5C.

## 15. Offline / Reconnect Behavior
When a trusted client goes offline, it stops sending events.
Upon reconnection the server queries `last_sync_timestamp` and sends only newer mem‑events.
If both sides have diverged (e.g., same memory updated differently), conflict resolution policy is invoked (user’s last‑write wins or merge UI).

## 16. Constellation Representation
- **Local Profiles** – solid nodes with their full graph.
- **Remote Agents** – hollow icons labeled “DISOVERED / KNOWN / TRUSTED”.
- **Adopted Memories** – attached to local nodes, tagged remote‑origin. Hover shows provenance details.

UI clearly separates Local and Remote graphs.
Optionally collapse remote agents so only metadata is shown until adoption.

## 17. Failure Scenarios
| Scenario | Mitigation |
|----------|------------|
| Remote host sends malformed memory JSON | Verify schema; discard with log notification. |
| Token expired mid‑transfer | Server retries handshake; client shows “Token expired”. |
| Network partition during sync | Resume after reconnection; reconcile differences via seq numbers. |

## 18. Security Considerations
- All communication beyond discovery must be authenticated and encrypted (TLS at application layer).
- No credentials are broadcast in discovery.
- Memories are never transmitted without explicit user permission.
- Replay protection: pairing codes single‑use + short TTL.

## 19. Recommended Architectural Path
1. **Discovery** – UDP multicast with minimal payload (`client_id`, hostname, endpoint). 
2. **Auth/Trust** – One‑time pairing code → device generates a bearer token. 
3. **Adoption UI** – Wizard that fetches metadata only after Trust; adopts selected memories. 
4. **Sync** – Event‑based feed over secure HTTP(S) or WebSocket for incremental updates. 
5. **Revocation** – Token revocation endpoint + UI flagging adopted memories as “revoked”.

Why this fits the project: Minimal new infra, uses existing FastAPI, keeps user control front‑and‑centered.

## 20. Human Decisions Required Prior to Implementation
| Decision | Why? |
|----------|------|
| Discovery Transport – multicast vs mDNS vs custom UDP port | Network policies / client support vary. |
| Authentication Mechanism – pairing code vs TLS certificates | Security vs developer effort trade‑off. |
| Adoption Granularity – per‑memory UI or whole profiles by default | UX complexity versus usability. |
| Conflict Resolution Policy – last‑write‑wins vs merge dialog | Data integrity for collaborative memory sharing. |
| Visibility Rules – whether remote node summaries appear in local constellation pre‑adoption | User expectation of privacy. |

These choices will shape the code that follows.

## README Changes (excerpt)
### Phase 6.5C
- **Remote‑Agent Adoption:** Design documented in
  [PHASE_6_5C_REMOTE_AGENT_ADOPTION_ARCHITECTURE.md](./docs/PHASE_6_5C_REMOTE_AGENT_ADOPTION_ARCHITECTURE.md)

---
**Context Warnings**
- @url:`http://192.168.1.12:8000`: no content extracted
