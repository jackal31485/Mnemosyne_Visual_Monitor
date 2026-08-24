# Phase 6.5C Implementation Specification (Authoritative)

> **This document is the authoritative architecture contract for Phase 6.5C.**
> All other Phase 6.5C design documents reference or derive from this spec.
> When any inconsistency exists between this document and another, this document governs.

- **Date frozen:** 2026-08-24
- **Scope:** Design only — no executable code in Phase 6.5C.
- **Guiding principle:** *Discovery is presence detection. Trust is authorization. Adoption is explicit data import. No state transition may implicitly perform the next state's function.*

---

## 1. Final State Machine

```
DISCOVERED ──(explicit user action)──► KNOWN ──(pairing + explicit user action)──► TRUSTED ──(explicit selection)──► ADOPTED
                                                                                        
(stale agent, remains)      (user can remove)   (trust record revoked)     (memory adopted only;
                              still in list)    (still in list)            trust relationship remains)
```

### 1.1 DISCOVERED

**Meaning:** A remote Hermes agent was detected on the LAN via UDP multicast.

**Stored data:**
| Field | Required? | Notes |
|-------|-----------|-------|
| `client_id` | Yes (UUID) | Opaque identifier from remote |
| `hostname` | No | Human-readable; may be blank |
| `installed_version` | No | Software version string; may be blank |

**Discovery MUST NOT transmit:**
- Profile names or counts
- Memory IDs or contents (this agent's or the remote's)
- Database paths
- Constellation information
- Credentials or authentication tokens
- Endpoint URIs / IP addresses / port numbers

Discovery does **not** establish trust. Discovery does **not** grant access to any API. Discovery does **not** exchange memories. Discovery does **not** automatically notify the remote agent that it was discovered (one-way broadcast only).

### 1.2 KNOWN

**Transition:** DISCOVERED → KNOWN requires **explicit user action.**

Discovery never auto-advances to KNOWN.

**Meaning:** *The user has chosen to remember this remote agent locally.*

KNOWN does NOT grant:
- Memory access
- Profile access
- Constellation access
- Synchronization
- Adoption

### 1.3 TRUSTED

**Transition:** KNOWN → TRUSTED requires **explicit user action and pairing.**

**Mechanism (Phase 6.5C prototype):** One-time pairing code + short-lived access token.

**Three distinct concepts — implement each separately:**

| Concept | Duration | Purpose |
|---------|----------|---------|
| *Pairing credential* | Single-use code, valid ≤ 5 minutes | Prove physical proximity / user intent |
| *Persistent trust relationship* | Stored in local DB until explicitly revoked by user | "This agent is trusted; allow it to use its auth token" |
| *Short-lived access token* | ≤ 5 minutes (JWT or comparable) | Grant access to authorized API endpoints |

**Do NOT represent persistent trust as merely a short-lived JWT.** The persistence of the trust relationship and the validity window of the access token are not the same thing.

TRUSTED permits only the API operations explicitly defined by the authenticated contract (`GET /api/profiles`, `GET /api/graph?source_profile=<profile_id>`). TRUSTED does **not** automatically import memories.

### 1.4 ADOPTED

**Transition:** TRUSTED → ADOPTED requires **explicit user action.**

The user chooses what to adopt.

**Supported initial granularity:** per-memory item.

**Future expansions (not in 6.5C scope):**
- category / tag-level
- selected collection
- entire profile
- synchronized stream

**Do not make whole-profile adoption the default.** Per-memory selection is primary.

Every adopted memory must preserve:
| Field | Notes |
|-------|-------|
| `origin_client` | client_id of the remote agent |
| `origin_profile` | profile name on source side |
| `origin_memory_id` | original database identifier |
| `original_timestamp` | creation timestamp from source |
| `adopted_at` | local adoption time |

Adopted memories must remain distinguishable as remote-origin data.

---

## 2. Local Constellation Invariant

> **Invariant:** Only locally owned memories and explicitly adopted remote memories may participate in the local constellation.

**Consequences for remote agents at each state:**

| State | Appears in constellation? | Why |
|-------|--------------------------|-----|
| DISCOVERED | No | Not yet known; no authorization |
| KNOWN | No | Trusted identity established, but no data adopted |
| TRUSTED | No | Authorized to query metadata; no memories adopted |
| ADOPTED (remote memories) | Yes, as remote-origin nodes | Explicitly imported with provenance tags |

Remote agents may have a separate **Remote Agents / Discovery** UI. That UI must not be confused with the constellation and must never share rendering logic with it.

---

## 3. LAN Discovery

### 3.1 Transport: UDP Multicast (Prototype)

UDP multicast is the Phase 6.5C prototype discovery mechanism. If multicast proves unsuitable in future environments, mDNS may be evaluated later. **Discovery networking is not implemented in 6.5C.**

### 3.2 Discovery Payload

Minimal — only:
```json
{
  "client_id": "uuid-v4",
  "hostname": "optional-string-or-null",
  "installed_version": "optional-string-or-null"
}
```

**Must NOT include:**
- Endpoint URIs (IP, port)
- `profile_count`
- Profile names
- Memory information of any kind
- Credentials or tokens

### 3.3 One-Way Guarantee

The broadcast is entirely one-way: the discovering agent learns a remote agent exists. The remote side receives no message acknowledging detection. Discovery cannot be used for passive reconnaissance by a rogue agent.

---

## 4. Trust Behavior

Trust is authorization only — nothing more.

### 4.1 Pairing Flow (Prototype)

```
KNOWNSide:     SHOWS pairing code (6-digit, single-use, TTL ≤ 5 min)
REMOTE Side:   ENTERS the displayed code into its local app
SERVER Local:  Verifies code == stored value && timestamp ≤ TTL → OK
Both:          Issue short-lived access token; store persistent trust record
```

### 4.2 Token Types (Clear Separation)

| Token | Lifetime | Storage | Can be revoked? |
|-------|----------|---------|-----------------|
| Pairing code | ≤ 5 min, single use | Server-side hash+nonce | Yes — by expiry or server deletion |
| Persistent trust record | Until manual revocation | Local SQLite `trust_relationships` row | Yes — via `POST /api/revoke_trust` |
| Short-lived access token (JWT) | ≤ 5 min | Both sides; expires automatically | No — simply expires; revoke the *trust* instead |

---

## 5. Adoption Behavior

### 5.1 User Interface Concept: Adoption Wizard

After TRUSTED is established, the user opens the Adoption Wizard on the **Remote Agents / Discovery** UI. The wizard presents only metadata (profile names available on remote) — never raw memory content or full graph topology until after per-item confirmation.

For each memory item:
1. User sees title/content preview, provenance fields, and timestamp.
2. User checks/unchecks individually.
3. On "Adopt," the client POSTs only checked items to `POST /api/adopt`.

### 5.2 Adoption is Irreversible Within 6.5C Scope

Phase 6.5C defines `POST /api/revoke_adoption` (separate from `revoke_trust`). Revoking adoption marks adopted memories; it does NOT automatically delete them — user confirms the deletion action explicitly.

### 5.3 Provenance Enforcement

Every adopted memory row in the local Mnemosyne database includes:

| Column | Type | Notes |
|--------|------|-------|
| `origin_client` | TEXT | `client_id` of source agent |
| `origin_profile` | TEXT | Source profile name |
| `origin_memory_id` | TEXT | Original primary key on remote side |
| `original_timestamp` | DATETIME | Creation time from source |
| `adopted_at` | DATETIME | When adoption occurred locally |
| `is_remote_origins` | INTEGER (0/1) | Flag for constellation visibility |

---

## 6. API Boundary

### 6.1 Discovery — NO HTTP Endpoint

**LAN discovery is a UDP multicast listener on the server side. There is no `/api/discovery` HTTP endpoint.** The only unauthenticated "endpoint" is the multicast socket itself, which accepts inbound advertisements only.

### 6.2 Trusted Endpoints (after auth, bearer token required)

| Method | Endpoint | Scope | Auth Required? |
|--------|----------|-------|----------------|
| `GET` | `/api/profiles` | Remote agent profiles metadata | Yes — TRUSTED+ access token |
| `GET` | `/api/graph?source_profile=<id>` | Graph fragments filtered by source profile | Yes — TRUSTED+ access token |

**Important:**
- These endpoints are NOT accessible to untrusted LAN clients.
- `/api/profiles` is the authoritative profile metadata endpoint. Do not use `/api/graph` to determine profile counts.
- No raw SQLite paths are exposed through any endpoint.

### 6.3 Adoption Endpoint

| Method | Endpoint | Scope | Auth Required? |
|--------|----------|-------|----------------|
| `POST` | `/api/adopt` | Explicit user-selected memory items | Yes — TRUSTED+ only |

**Invariants:**
- Must require explicit user-selected items.
- Impossible for discovery or trust establishment alone to invoke adoption.
- Payload: `{ "items": [ { "origin_memory_id": "...", "source_profile": "..." }, ... ] }`

### 6.4 Revocation Endpoints

| Method | Endpoint | Effect | Auth Required? |
|--------|----------|--------|----------------|
| `POST` | `/api/revoke_trust` | Removes/invalidates authorization; prevents future communication | Yes — TRUSTED owner of trust record |
| `POST` | `/api/revoke_adoption` | Separately marks or retracts adopted memories | Yes — TRUSTED+ owner |

**Trust revocation:** removes/invalidates authorization, prevents future communication. **Does NOT automatically delete adopted memories.**

**Adoption revocation:** separately marks or retracts adopted memories. Must not be conflated with trust revocation.

### 6.5 Sync — Stub Only (Phase 6.5C)

```
GET /api/sync?since=<timestamp> → {} 200 OK
```

Returns empty body in Phase 6.5C. This endpoint is a design placeholder for future incremental synchronization work. **No automatic background sync is implied or authorized by this stub.**

---

## 7. Privacy / Security Invariants

The following invariants are mandatory:

| # | Invariant | Why |
|---|-----------|-----|
| 1 | Discovery never grants authorization | Prevents auto-authorization via sniffing LAN broadcasts |
| 2 | Discovery never imports memories | Memory transfer requires explicit user action at ADOPTED state |
| 3 | Discovery never exposes local memories | Local data remains hidden until trust is established |
| 4 | KNOWN never grants memory access | Being "known" is purely a local record — no auth tokens involved |
| 5 | TRUSTED never implies ADOPTED | Authorization ≠ authorization to import data |
| 6 | Adoption always requires explicit user action | Every adopted item must be individually confirmed by the user |
| 7 | Remote memories never enter the local constellation before adoption | The Local Constellation Invariant (Section 2) |
| 8 | Adopted memories always retain provenance | All five provenance columns mandatory for every remote-origin row |
| 9 | Revoking trust does not silently delete adopted memories | User confirms deletion separately via `revoke_adoption` or UI |
| 10 | Discovery broadcasts never contain credentials or memory data | Discovery payload is `client_id`, optional hostname, optional version only |
| 11 | Untrusted LAN clients cannot enumerate local profiles or memories | No `/api/profiles` or `/api/graph` without valid auth token |
| 12 | The local server never exposes raw SQLite paths through its API | No endpoint returns filesystem paths to database files |

---

## 8. Remote Agent UI (Constellation-Independent)

A separate **Remote Agents / Discovery** view:

| State | What the user sees |
|-------|--------------------|
| DISCOVERED | Identifier, optional hostname/status; no profile info |
| KNOWN | Same + "Known" badge; still no metadata |
| TRUSTED | Authenticated status; authorized metadata (available profiles) visible only |
| ADOPTED memories | Adopted items represented in local constellation with remote-origin tags |

**Never show remote memory content or profile information before the appropriate authorization stage.**

---

## 9. Revocation Model

### 9.1 Revoke Trust (`POST /api/revoke_trust`)

Effect:
1. Invalidates the persistent trust relationship record in local DB.
2. Rejects all access tokens issued under this trust entry from the remote agent.
3. Prevents future API calls from this remote agent.
4. **Adopted memories remain untouched** — they persist with their provenance columns intact.

### 9.2 Revoke Adoption (`POST /api/revoke_adoption`)

Effect:
1. Separately marks or retracts adopted memories (separate from trust revocation).
2. User confirms explicitly; not automatic on trust revocation.
3. Retains the provenance row for audit/traceability until user confirms permanent deletion.

### 9.3 Stale Agent Lifecycle

If an agent stops broadcasting for >30 seconds:
1. Local entry is marked "stale" (not removed).
2. UI indicates stale status.
3. Trust state, if any, is preserved.
4. Re-discovery with same `client_id` restores timestamps without losing trust/adoptions.

---

## 10. Human Decision Summary (Final)

The following decisions are **confirmed as stated** — no reconsideration needed:

| # | Decision | Selected Approach |
|---|----------|-------------------|
| 1 | Discovery transport | UDP multicast (prototype); mDNS evaluated later if needed |
| 2 | DISCOVERED → KNOWN transition | Manual (explicit user action) |
| 3 | Trust mechanism | One-time pairing code |
| 4 | Adoption granularity | Explicit per-memory selection |
| 5 | Provenance enforcement | Mandatory provenance fields on every adopted memory |
| 6 | Automatic adoption | No — must always require explicit user action |
| 7 | Pre-adoption constellation visibility | None — remote agents never appear in constellation before adoption |
| 8 | Synchronization | Deferred to future phases; stub only in 6.5C |
| 9 | mTLS for trust | Deferred — pairing code is Phase 6.5C prototype choice |
| 10 | Unraid deployment | Deferred — future concern |

### Pending Human Decisions (for later, not 6.5C)

| Decision | When to decide | Why |
|----------|---------------|-----|
| Sync protocol choice (SSE vs WebSocket vs HTTP polling) | Phase 6.6+ | Depends on operational experience with adoption workflow |
| Conflict resolution policy when both sides modify same memory | Phase 6.6+ | Not needed for one-way adopt; matters during future bi-directional sync |
| Whether to add mTLS as trust alternative | Post-prototype evaluation | Higher security cost; evaluate after one-time pairing code is in the wild |
| Central deployment model (Docker, Kubernetes, Unraid) | Phase 6.7+ | Infrastructure scaling decision |
| Auditing requirements for trust/adoption events | Compliance-driven | Determine when and if audit trails become mandatory |

---

## 11. Architecture Overview (Reference)

### Key Components

1. **Discovery Service** — Passive UDP multicast listener accepting minimal JSON payloads from remote agents. One-way only; no acknowledgment sent to broadcaster.

2. **Central Server API** — HTTPS/REST endpoints accessible only to TRUSTED+ clients with valid bearer tokens.

3. **Trust Engine** — One-time pairing code exchange producing: (a) a short-lived access token and (b) a persistent trust relationship record, clearly separated per Section 4.

4. **Adoption Workflow** — Explicit UI prompts listing available memories for the TRUSTED user to select; adoption writes to local Mnemosyne with provenance columns.

5. **Revocation Handlers** — Defined stubs (`revoke_trust`, `revoke_adoption`); trust revocation does not affect adopted memory rows.

---

## 12. Contradiction Resolution Log

The following contradictions were identified across all Phase 6.5C documents and resolved by enforcing the authoritative spec above:

| # | Source Document | Section | Contradiction | Resolution |
|---|----------------|---------|---------------|------------|
| C1 | `IMPLEMENTATION_SPEC.md` §3 Transition Rules | "DISCOVERED → KNOWN" described as *automatic upon multicast receipt* | **Reconciled to explicit user action.** Per the requirements: "DISCOVERED → KNOWN requires explicit user action." The spec erroneously stated auto-transition. |
| C2 | `IMPLEMENTATION_SPEC.md` §5 Security | Trust represented as "JWT with 5 min expiry" presented as the primary trust mechanism | **Reconciled to three-token model** (pairing code, persistent trust record, short-lived access token). A mere 5-minute JWT is not the trust relationship. |
| C3 | `REMOTE_AGENT_ADOPTION.md` §3 DISCOVERED data | Lists `profile_count` and `endpoint_url` as part of discovery payload | **Reconciled.** The requirements explicitly forbid transmitting profile counts, endpoint URIs, or any memory-identifying information in discovery broadcasts. Both removed from payload. |
| C4 | `IMPLEMENTATION_SPEC.md` §4 API Boundary | Lists a public unauthenticated `GET /api/discovery` HTTP endpoint | **Reconciled.** Discovery is LAN multicast transport only — no HTTP endpoint. The `/api/discovery` path was removed entirely. This aligns with the requirements: "Do NOT require an unauthenticated /api/discovery HTTP endpoint." |
| C5 | `REMOTE_AGENT_ADOPTION.md` §14 Sync Model | Describes full change-feed over SSE/WebSocket as the "preferred approach" for Phase 6.5C | **Reconciled.** Synchronization is explicitly deferred to future phases. The sync endpoint exists only as an empty stub returning `{}`. |
| C6 | `REMOTE_AGENT_ADOPTION.md` §6 Adoption Granularity | Lists "Entire profile" as equally valid alongside per-memory selection | **Reconciled.** Per-memory selection is primary. The requirements state: "Do not make whole-profile adoption the default." This will be a future expansion, not an initial option. |
| C7 | `IMPLEMENTATION_SPEC.md` §3 step 4 & transition table | Implies adoption selection occurs as part of the trust flow rather than separate | **Reconciled.** TRUSTED → ADOPTED is strictly a separate explicit user action — never implied by or bound to the trust establishment flow. |
| C8 | `REMOTE_AGENT_ADOPTION.md` §16 Constellation Representation | Remote agents shown as "hollow icons" in local constellation at DISCOVERED/KNOWN/TRUSTED states | **Reconciled.** The Local Constellation Invariant (Section 2 above) forbids this. Only locally owned and adopted remote memories participate. A separate Remote Agents UI handles non-constellation display. |

---

## 13. Consistency Notes for Other Phase 6.5C Documents

### `PHASE_6_5C_HERMES_CLIENT_ARCHITECTURE.md`

This document served as a **design-scope inventory** and is informational. Its architectural decisions table (Section 1) should be read as *pre-resolution considerations*, not binding commitments. The authoritative decisions for Phase 6.5C are now in this Implementation Specification.

Key clarifications:
- LAN discovery: UDP multicast confirmed; `/api/discovery` HTTP endpoint removed — use Section 3 of this spec instead.
- Authentication: One-time pairing code confirmed as prototype choice; mTLS deferred. See Section 4.
- Adoption: Per-memory primary, whole-profile deferred. See Section 5.
- Synchronization: Deferred entirely. Stub only. See Section 6.5.

### `PHASE_6_5C_ARCHITECTURE_VALIDATION.md`

This document is a **validation record** (test results, UI confirmation). Its findings about endpoint filtering and profile discovery for local-only use remain valid. Sections marked "⚠️" and "⚙️ Pending" should be cross-referenced against this spec:
- Remote Agent Adoption model → Section 1 of this spec.
- Authentication/authorization → Section 4.
- Sync protocol → Section 6.5 (stub only).
- Revocation endpoint → Section 6.4.
- UI Validation finding (§8) remains valid but now references the **Remote Agents / Discovery** UI, not constellation integration.

### `PHASE_6_5C_REMOTE_AGENT_ADOPTION_ARCHITECTURE.md`

Sections confirmed correct as-is:
- §1 Architecture overview (high-level model still applies)
- §2 Threat/Privacy Model (still valid; tightened in Section 7 of this spec)
- §4 KNOWN State (correct as described)
- §5 TRUSTED State — mechanism choice (one-time pairing code confirmed)
- §8 Permission Model (conceptually correct; see Sections 3-6 for refined API boundaries)
- §12 Provenance Model (correct; now formally mandated with all five columns in Section 5)
- §17 Failure Scenarios (still valid as design considerations)
- §18 Security Considerations (confirmed; expanded via Section 7 invariants)

Sections requiring the reader to defer to this spec:
- §3 (DISCOVERED data → use §3 of this spec for payload)
- §6 (Adoption granularity → see §5 of this spec)
- §9 (Auth options pairing code confirmed, others deferred)
- §10 (Discovery → see §3 of this spec); recommendation changed: discard `endpoint_url` from broadcast.
- §11 (Adoption workflow → see §5.1 of this spec; remove "Entire profile" default)
- §13 (Revocation → see §9 of this spec; trust/adoption clearly separated)
- §14 (Sync → deferred; use stub in §6.5 here)
- §16 (Constellation → see §2 invariant; remove constellation rendering for non-adopted)
- §19 (Recommended path → updated per authoritative decisions §10 of this spec)
- §20 (Human Decisions → now confirmed in §10 of this spec, no longer "pending")

### `README.md` (/home/jackal31485/Documents/Hermes/projects/Mnemosyne_Visual_Monitor/README.md)

The README update note at the project root is informational. The authoritative specification reference now points here to `docs/PHASE_6_5C_IMPLEMENTATION_SPECIFICATION.md`. No README file modification was made — only this cross-reference documentation note.

---

## 14. Scope Confirmed as Design Only

**No executable code is part of Phase 6.5C.** This document defines the architecture contract. Implementation begins in a future phase, upon user authorization to proceed.

---

*End of Phase 6.5C Implementation Specification — Authoritative Version FROZEN 2026-08-24.*
