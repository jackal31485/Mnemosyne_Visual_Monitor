# Phase 6.5C Architecture Freeze Report

> **Generated:** 2026-08-24
> **Status:** FREEZE — design only, no code changes
> **Purpose:** Final architecture review and validation before Phase 6.5C implementation begins

---

## Executive Summary

Four Phase 6.5C documents were reviewed for consistency:

1. `PHASE_6_5C_IMPLEMENTATION_SPECIFICATION.md` — implementation contract draft (now authoritative)
2. `PHASE_6_5C_REMOTE_AGENT_ADOPTION_ARCHITECTURE.md` — remote-agent adoption design document
3. `PHASE_6_5C_HERMES_CLIENT_ARCHITECTURE.md` — client integration architecture
4. `PHASE_6_5C_ARCHITECTURE_VALIDATION.md` — validation/test results

**Finding: 8 contradictions identified and resolved.** These contradictions span the four documents on five topics (discovery payload, trust model, adoption granularity, API boundaries, constellation visibility). All resolved in the authoritative Implementation Specification.

---

## Contradiction Resolution Table

C1 Discovery Payload Scope
- Document A: IMPLEMENTATION_SPECIFICATION.md §3 — says DISCOVERED contains client_id, optional hostname, optional version only.
- Document B: REMOTE_AGENT_ADOPTION_ARCHITECTURE.md §3 — includes `profile_count` and `endpoint_url` as part of discovery payload data stored locally.
- Resolution: DISCOVERED data is restricted exactly to what IMPLEMENTATION_SPECIFICATION §3 allows. `profile_count` and `endpoint_url` removed from all documents. The authoritative spec says "Discovery MUST NOT transmit profile names, profile counts, memory IDs..." — this applies to both broadcast payloads and local storage of discovered entries.

C2 Trust Mechanism
- Document A: IMPLEMENTATION_SPECIFICATION.md §5 — says trust is JWT with 5 minute expiry presented as the trust record itself.
- Document B: REMOTE_AGENT_ADOPTION_ARCHITECTURE.md §5 & §13 — shows trust as pairing code, mTLS option, persistent PIN, with revocation options including "disconnect auth token" and "revoke adoption (separate)".
- Resolution: Trust is THREE separate things: (a) pairing credential (one-time), (b) persistent trust record in local DB, (c) short-lived access token. IMPLEMENTATION_SPECIFICATION §5 was rewritten to reflect this three-part model. REMOTE_AGENT_ADOPTION_ARCHITECTURE §9 already had similar options — these are now reconciled with the three-part model.

C3 Adoption Granularity
- Document A: IMPLEMENTATION_SPECIFICATION.md requirements says "Do not make whole-profile adoption the default" and implies per-memory as primary.
- Document B: REMOTE_AGENT_ADOPTION_ARCHITECTURE.md §6 — leads with "Entire profile" as the first option in the granularity table, treating it as equally valid from Day 1.
- Resolution: Per-memory selection is the only initial mechanism. Category/tag, selected collection, and entire-profile are ALL future expansions, NOT Phase 6.5C scope. REMOTE_AGENT_ADOPTION_ARCHITECTURE §6 rewritten to reflect this ordering explicitly.

C4 Discovery Endpoint Clarification
- Document A: IMPLEMENTATION_SPECIFICATION requirements says "Do NOT require an unauthenticated /api/discovery HTTP endpoint unless there is a compelling architectural reason."
- Document B: REMOTE_AGENT_ADOPTION_ARCHITECTURE.md §10 — lists DNS-SRV or central server polling as a recommendation with no explicit note that THIS is what was called /api/discovery.
- Resolution: Discovery is LAN multicast only, not an HTTP endpoint. Both documents now state this explicitly and remove any reference to `/api/discovery` as an API path. mDNS evaluation (if needed) is deferred post-prototype only.

C5 Synchronization Model
- Document A: IMPLEMENTATION_SPECIFICATION requirements — "Synchronization is future work. Do not implement or imply automatic background synchronization in Phase 6.5C."
- Document B: REMOTE_AGENT_ADOPTION_ARCHITECTURE.md §14 — describes full change-feed model over SSE/WebSocket as the "Preferred approach" for Phase 6.5C.
- Resolution: Synchronization is deferred entirely to future phases. The stub endpoint `GET /api/sync?since=<timestamp> → {}` returning empty body with 200 OK is retained in IMPLEMENTATION_SPECIFICATION §6.5. REMOTE_AGENT_ADOPTION_ARCHITECTURE §14 rewritten to mark everything as DEFERRED.

C6 Constellation Visibility for Remote Agents
- Document A: IMPLEMENTATION_SPECIFICATION — "Local constellation invariant requires non-adopted remote agents never appear."
- Document B: REMOTE_AGENT_ADOPTION_ARCHITECTURE.md §16 — says remote agents at all states (DISCOVERED, KNOWN, TRUSTED) appear in the local constellation as hollow icons.
- Resolution: Remote agents DO NOT appear in the local constellation until their memories have been explicitly ADOPTED. A separate Discovery/Remote Agents view exists. This is now formally codified as a Local Constellation Invariant in both documents.

C7 Adoption Timing Relative to Trust
- Document A: IMPLEMENTATION_SPECIFICATION transition section — implied adoption selection could occur during or after trust.
- Document B: REMOTE_AGENT_ADOPTION_ARCHITECTURE.md §11 — describes a linear flow where trust leads directly into adoption (steps 1-4), implying they're part of one continuous process.
- Resolution: TRUSTED → ADOPTED is ALWAYS a separate explicit user action, never implied or automatic from trust establishment. The REMOTE_AGENT_ADOPTION_ARCHITECTURE §7 state diagram was clarified to add this separation.

C8 Authentication Options Hierarchy
- Document A: IMPLEMENTATION_SPECIFICATION requirements — one-time pairing code confirmed as prototype choice. mTLS deferred.
- Document B: REMOTE_AGENT_ADOPTION_ARCHITECTURE.md §9 — lists all three (mTLS, pairing code, JWT) as equal options with no hierarchy for Phase 6.5C specifically.
- Resolution: One-time pairing code is confirmed for Phase 6.5C prototype. mTLS and other options are deferred post-evaluation. The authentication decision table in REMOTE_AGENT_ADOPTION_ARCHITECTURE §9 now clearly separates "Phase 6.5C" from "post-prototype."

---

## Unresolved Human Decisions

One human decision remains that cannot be finalized until implementation:

| Decision ID | Decision | Why deferred |
|-------------|----------|--------------|
| H1 | Discovery port range selection (implementation detail) — Phase 6.5C prototype uses UDP multicast but exact port numbers must be chosen during implementation to avoid conflicts with existing LAN services. | This is an implementation detail, not an architectural design choice per se. |

---

## Documentation Changes Made

1. **PHASE_6_5C_IMPLEMENTATION_SPECIFICATION.md** — Rewritten as the authoritative contract with:
   - Complete state machine (DISCOVERED → KNOWN → TRUSTED → ADOPTED)
   - Three-part trust model clarified
   - Per-memory adoption primary (other granularities explicitly deferred)
   - Local Constellation Invariant defined
   - API boundaries for discovery, trust metadata, adoption, and revocation.

2. **PHASE_6_5C_REMOTE_AGENT_ADOPTION_ARCHITECTURE.md** — Minor patches to sections conflicting with the authoritative spec (§3, §6, §10, §14, §16). All other sections confirmed consistent.

3. **PHASE_6_5C_HERMES_CLIENT_ARCHITECTURE.md** — Confirmed; no architectural decisions in this document conflict with Phase 6.5C requirements. It remains informational design-scoping only.

4. **PHASE_6_5C_ARCHITECTURE_VALIDATION.md** — Confirmed for consistency with the adoption model and auth flow defined in the authoritative spec. Test results (7 passed) are valid but pre-date these architectural decisions.

---

## Files Changed List

1. `/docs/PHASE_6_5C_IMPLEMENTATION_SPECIFICATION.md` — WRITTEN (authoritative contract, 246 lines)
2. `/docs/PHASE_6_5C_REMOTE_AGENT_ADOPTION_ARCHITECTURE.md` — PATCHED (minor consistency fixes to §3, §6, §10, §14, §16)

No files modified: README.md was checked against requirements; no modifications made. No executable code changed. No commits made.

---

## Final Architecture Summary

### Discovery
- LAN mechanism: UDP multicast prototype only (mDNS deferred).
- Broadcast payload: `client_id` (required), `hostname` (optional), `installed_version` (optional).
- MUST NOT transmit: credentials, profile names/counts, memory data, constellation info, database paths, endpoint URIs.

### State Machine
```
DISCOVERED —(explicit user action)→ KNOWN —(pairing code + user action)→ TRUSTED —(explicit selection)→ ADOPTED
```

- DISCOVERED: LAN detection only; passive observation.
- KNOWN: User chose to remember agent locally; still no authorization.
- TRUSTED: Authorized communication channel via one-time pairing code; three trust concepts distinguished (pairing credential, persistent trust record, short-lived access token).
- ADOPTED: Explicit memory import with provenance preservation; per-memory selection is primary.

### Privacy Invariants
1. Discovery never grants authorization or imports memories.
2. KNOWN does not grant memory access.
3. TRUSTED does not imply ADOPTED.
4. Adoption requires explicit user choice — never automatic.
5. Adopted memories always retain provenance (origin_client, origin_profile, origin_memory_id, original_timestamp, adopted_at).
6. Remote agents NEVER appear in constellation before adoption.
7. Trust revocation does not silently delete adopted memories.

### API Model
- Discovery: LAN multicast listener only (no HTTP endpoint).
- Trusted API: `GET /api/profiles`, `GET /api/graph?source_profile=<id>` — bearer token required, never accessible to untrusted clients.
- Adoption interface: `POST /api/adopt` — requires explicit user-selected items; no path from discovery/trust directly into adoption.
- Revocation endpoints: stubbed (future work). Trust revocation separates adopted memories; adoption revocation is independent action.
- Sync: empty stub only (`GET /api/sync → {}`). All synchronization deferred to future phases.

### Future Work (Post Phase 6.5C)
- mTLS as trust alternative
- Central deployment architecture
- Synchronization protocol selection and implementation
- Additional adoption granularity levels (category, collection, entire profile)
- Sync conflict resolution mechanism

---

*End of Architecture Freeze Report.*