
# Mnemosyne Current Architecture Reconciliation — 2026-09-16

> **Authority:** This reconciliation records the implementation state established
> through completion of Phase 13. Where older sections of this specification
> describe proposed, experimental, or superseded architecture, the implemented
> repository and phase-specific governance documents take precedence.

## Current Project State

Phase 13 — **Higher-Level Mental Models** — is complete.

The completed Phase 13 layer establishes governed derived mental models with:

- explicit model types and lifecycle states;
- deterministic candidate detection;
- evidence and provenance validation;
- confidence derived from governed evidence;
- versioning and staleness handling;
- revocation propagation;
- evidence-preserving synthesis;
- read-only API projection;
- Browser inspection surfaces;
- explicit separation between source memories and derived knowledge.

Phase 13 does **not** authorize cross-profile learning.

The current repository baseline is:

```text
master
e645c37 Complete Phase 13 higher-level mental models documentation
The repository has been consolidated to a single master branch. Phase-specific
Git tags and temporary phase branches are no longer part of the active repository
workflow.
Phase 14 — Cross-Profile Learning & Controlled Transfer
Phase 14 is the next implementation phase.
Its purpose is to establish a governed transfer mechanism through which knowledge
that is already eligible for sharing may be evaluated for adoption by another
Hermes profile.
Phase 14 must distinguish:
Profile-Local Memory
        |
        v
Governed Collective Knowledge
        |
        v
Transfer Candidate
        |
        v
Authorization / Applicability / Evidence Validation
        |
        v
Explicit Profile Adoption
        |
        v
Profile-Specific Derived Knowledge
A collective entry being visible to a profile does not constitute learning.
A transfer candidate being generated does not constitute learning.
Only an explicitly authorized and auditable adoption operation may create
profile-specific learned state.
Phase 14 Non-Negotiable Boundaries
Phase 14 must preserve:
1. profile-local memory isolation;
2. source-memory immutability;
3. collective provenance;
4. evidence provenance;
5. source-profile identity;
6. destination-profile identity;
7. explicit transfer authorization;
8. explicit adoption state;
9. deterministic transfer decisions;
10. immutable transfer audit history;
11. revocation propagation;
12. conflict visibility;
13. temporal applicability;
14. absence of raw private memory content from shared derived representations;
15. prevention of implicit cross-profile learning.
Phase 14 must not:
- copy private raw memory between profile databases;
- silently modify a destination profile;
- treat collective visibility as adoption;
- discard source provenance;
- delete transfer history;
- bypass revocation;
- hide conflicting evidence;
- introduce unrestricted profile-to-profile synchronization;
- create a shared writable memory database;
- introduce ungoverned LLM-generated learning;
- modify Athena merely because cross-profile learning is being designed.
Data Science Boundary
Phase 14 is an applied decision and evaluation problem.
The system should make explicit:
- why a transfer candidate was generated;
- what evidence supports it;
- what evidence contradicts it;
- which source profile produced it;
- which destination profile is being considered;
- why the knowledge is applicable;
- what adaptation is required;
- what confidence or benefit signals were used;
- what conditions would invalidate the transfer.
The decision mechanism must remain inspectable and deterministic where
determinism is required by the governance contract.
Data Engineering Boundary
Phase 14 introduces a controlled transfer pipeline rather than a shared
cross-profile write path.
The architecture should preserve separate ownership boundaries:
Source Profile
     |
     | governed candidate
     v
Transfer / Mediation Boundary
     |
     +--> validation
     +--> authorization
     +--> provenance
     +--> audit
     |
     v
Destination Profile
The destination profile remains the owner of any profile-specific learned
representation created by adoption.
The transfer record must remain auditable independently of whether the
destination later revokes or supersedes the learned representation.
Phase 14 Completion Boundary
Phase 14 is complete only when cross-profile transfer can be demonstrated as:
- explicit rather than implicit;
- authorized rather than assumed;
- provenance-preserving rather than opaque;
- evidence-backed rather than text-only;
- reversible through governed revocation;
- profile-isolated rather than globally mutating;
- auditable rather than destructive;
- deterministic enough to reproduce and test.
Phase 15 must not be implemented as part of Phase 14 merely because retrieval
optimization could improve transfer quality.
Phase 14 establishes the governance and transfer mechanism first.

# Implementation Specification for Mnemosyne Visual Monitor

> **Author:** Athena (local implementation specialist)
>
> **Scope:** This document bridges the independent architectural reviews, Athena’s synthesis, and the next engineering effort. It formalises what is *currently* in the repository, what must be implemented, what remains experimental, and a clear roadmap of phases.

---
## 1. CORE ARCHITECTURE

| Layer | Responsibility | Storage | Access & Constraints |
|-------|----------------|---------|---------------------|
| **Local Vault** (Per‑Profile) | Raw memory storage & local inference | SQLite database located at `$HOME/.hermes/profiles/{profile}/mnemosyne.db` | *Strict isolation* – read‑only discovery only; no cross‑profile writes. Athena owns its own profile DB but is never a write target for the collective layer.
| **Mediation Plane** (Air‑Lock) | Promotion pipeline + privacy scrubber | In‑memory service (runs in local or shared process, never directly on a profile DB). Holds a *Proposal Queue* and enforces Validation logic before forwarding to Collective. | Only writes to the **Collective** table(s) after successful validation; keeps provenance (`source_profile`, `proposed_at`).
| **Collective Knowledge Base** (Global) | Shared, validated knowledge accessible by all profiles. | Dedicated SQLite DB (`collective.db`) or a future PostgreSQL instance on Unraid/Server. | Read‑only for all profiles; write‑privileges limited to the Mediation Plane. Stores *references* (`profile:memory_id`) instead of copying raw records.

### Boundary Rules
- **No cross‑profile data copy** – the collective only stores a reference record + provenance metadata. The owner profile keeps the full content locally.
- **Privacy filter** runs on every proposal; a `PrivacyFilter` component strips or masks any PII/private fields before the reference is written to shared storage.
- **Athena** has no direct write access to the collective DB; Athena merely queries and displays results. Validation logic resides in the Mediation Plane.

---
## 2. MEMORY LIFECYCLE

1. **Private memory** – stored in profile's local Vault.
2. **Candidate/Proposal** – a *proposal* is created when a profile decides to expose a record for collective insight (e.g., via UI button or auto‑detect heuristics).
3. **Privacy filtering** – the proposal passes through `PrivacyFilter`; any private text, user identifiers, or sensitive metadata is scrubbed/masked.
4. **Validation** – a state machine (`Validator`) checks:
   - **Source provenance** (profile, timestamp)
   - **Consistency** with other profiles (optional cross‑profile score)
   - **LLM corroboration** (score ≥ *threshold*; threshold experimental; see §14.)
5. **Promotion / Rejection** – on success the proposal is promoted to Collective; otherwise it may be rejected or flagged for manual review.
6. **Collective knowledge** – promoted records live as *reference entries* in the Collective DB. They can be queried by any profile.
7. **Revision** – a collective member can submit a revised memory. This creates a new record with a link to the original via `revision_of` reference; both are stored as separate entries.
8. **Revocation / Deletion** – if the source profile deletes a private memory that has already been promoted, a *revocation event* is issued by the Mediation Plane; the collective entry receives an `is_revoked = 1` flag and remains for audit trail.

Transition triggers are explicit:
- **Proposal creation** → admin UI or auto‑detect.
- **Privacy filtering** → automatic step in pipeline.
- **Validation** → validator decision.
- **Promotion** → write to Collective DB via Mediation service.
- **Revocation** → event fired by source profile through a *soft delete* API (no hard removal yet).

### Experimental Thresholds
`LLM-score >= 0.92` and `minimumThreeSourcesCorroboration()` as suggested by Pope are *experimental*. Precise thresholds will be determined in §14.

---
## 3. PROVENANCE

Each collective entry contains the following columns:
- `id`
- `source_profile`
- `origin_memory_id`
- `proposed_at`
- `validated_at`
- `validator_profile` (Athena)
- `validation_score`
- `revision_of` (nullable foreign key to original id)
- `is_revoked` (boolean)
- `revocation_reason`

Queries can join back to the source profile's DB via file path or a shared API that exposes raw memory if necessary. The provenance chain ensures traceability: *“Where did this collective knowledge come from?”* is answered unambiguously.

---
## 4. PRIVACY / PROFILE ISOLATION

| Crossing the boundary | Allowed? | Why | Implementation |
|-----------------------|----------|-----|-----------------|
| Full content of a private record | **No** | Violates privacy; violates project intent | The Mediation Plane never stores full raw text – only references.
| Metadata (e.g., timestamp, tags) | **Yes**, if non‑PII | Useful for analytics | Stored in Collective DB.
| PII fields (names, emails) | **Never** | Regulatory and safety | `PrivacyFilter` removes/masks.
|
### Filtering Mechanism
- A rule engine that applies a *whitelist/blacklist* of column names.
- Optional content‑based heuristics using simple regex or a small NLP model to catch hidden PII.
- Experimental: user‑configurable sensitivity; will be validated in §14 (Experiment 2).

---
## 5. COLLECTIVE KNOWLEDGE DATABASE

### CONFIRMED DESIGN
| Table | Purpose |
|-------|---------|
| `collective_entries` | Core reference table – each row represents a promoted memory. Contains provenance, validation history and metadata.
| `entry_references` | Stores foreign keys to profile DBs (`source_profile`, `origin_memory_id`).
| `validation_log` | Immutable audit trail of every validation attempt (score, validator, timestamp).
| `revision_links` | Many‑to‑one mapping from revised entries back to original.
| `conflict_resolution` | Stores conflict flags and resolution decisions (auto/ manual). |

### PROPOSED DESIGN
- A single SQLite DB with WAL enabled. Future migration path to PG.
- Indexes on `source_profile`, `validation_score`, and `revocation_status` for fast queries.
- JSON columns for vector embeddings if needed.

### EXPERIMENTAL DESIGN
1. **Vector Store** – whether to embed every entry using `sqlite_vec` or maintain separate search index.
2. **Conflict Table Schema** – design of conflict resolution flags and user‑review queues.
3. **Hybrid Storage** – test storing some fields in binary blobs for privacy compliance.

---
## 6. ATHENA'S ROLE

Athena is an *interface* profile with read‑only access to the collective DB, plus a local query engine that can correlate Athena’s private memories with collective entries. Operations performed by Athena:
- Query and present validated knowledge.
- Flag potential conflicts for moderator review.
- Request re‑validation on critical updates.

Athena **does not** write directly into the collective layer; its own database remains independent, preserving the single‑point‑of‑failure mitigation recommendation from Boss.

---
## 7. PROFILE‑SPECIFIC LEARNING

The system can tag a proposal with a *target profile* (`audience_profile`). The Mediation Plane will:
1. Extract only the *relevant subset* of the source memory (e.g., textual snippet and metadata).
2. Store this subset under `collective_entries` with an additional column `audience_profile`.
3. When the target profile imports, it receives a new local entry derived from that reference but devoid of the discoverer’s private data.

---
## 8. VISUALIZATION ARCHITECTURE

| View | Data Source | Key Interaction |
|------|-------------|-----------------|
| **Constellation** | `collective_entries` + `conflict_links` + vector embeddings | Graphical representation of inter‑profile relationships; supports filtering by profile, concept or confidence.
| **Table** | Same data, presented in a sortable/filterable grid |
| **Timeline** | Chronological join of `proposed_at`, `validated_at`, `revocation_at` |
| **User‑Management** | Admin endpoint that allows *review*, *edit* (only status fields), *revoke* or *delete* collective entries. Creation disallowed.

Edits to annotations (`notes`, `tags`) are stored in the collective DB and record edit history for provenance.

---
## 9. VECTOR / EMBEDDING ARCHITECTURE

- Vectors currently exist as separate `vec_*` tables via `sqlite_vec`. All vectors share the same embedding model at the moment of discovery.
- Future consistency experiments will test:
   - Cross‑profile embedding alignment (same model vs. different).
   - Merge embeddings into a single shared vector space vs. per‑profile subspaces.
- Current plan: keep vectors *per profile* in their local DBs; only compute similarity for collective entries when requested, using the profile’s own vector space. Experimental design 3 (in §14).

---
## 10. SYNCHRONIZATION

**Recommended initial approach:** Event‑driven **push notifications** via SQLite triggers + lightweight message queue.
- Schema: each profile DB emits a *ROWID* change event that the Mediation Plane subscribes to.
- Benefits: near real‑time updates, scalability with many profiles.
- Alternatives (polling/FS watch) were considered but found less efficient.

---
## 11. REVOCATION / DELETION

- When a source profile deletes or updates a private memory that already has a collective reference, the Mediation Plane must:
   1. Receive an *update event*.
   2. Create a revocation record in `conflict_resolution` and set `collective_entries.is_revoked = 1`.
   3. Retain original data in the source profile for audit.
- The collective layer remains immutable – only a flag changes; no deletion of rows to preserve provenance integrity.

---
## 12. UNRAID / SERVER FUTURE (FUTURE ONLY)

| Component | Location | Notes |
|-----------|----------|-------|
| Profile DBs | Local user home | remain private, optionally encrypted with LUKS or similar.
| Mediation Plane | Server‑side daemon | runs on Unraid; accepts cross‑profile proposals via secure API.
| Collective DB | Unraid array or PostgreSQL | Shared pool; includes WAL and backup snapshots.

Server‑side Athena may exist but will still never have direct write access to the collective layer – it simply consumes read‑only views.

---
## 13. TESTING STRATEGY

| Category | Specific Test |
|---------|---------------|
| Profile isolation | Unit test that writing in one profile DB does not appear in another (SQL queries via `ATTACH`). |
| Privacy boundary | Regression test ensuring `PrivacyFilter` removes all PII columns before write. |
| Promotion pipeline | Mock validation returns success/failure and verifies correct state machine transition. |
| Provenance | Query collective entry and confirm foreign keys trace back to original profile DB file. |
| Conflict resolution | Create duplicate entries, trigger auto‑conflict flag; verify audit log updates. |
| Revocation flow | Delete source memory, ensure collective `is_revoked` set but data remains. |
| Vector handling | Compute similarity between an entry and its vector; test on small sample dataset. |
| Database corruption / recovery | Simulate WAL crash, perform backup/restore cycle and verify no loss of provenance. |
| UI behavior | End‑to‑end GUI test using pytest‑qt or Selenium to navigate constellation/table/timeline and edit metadata successfully.

All tests must pass in a clean environment (python3 -m pytest). After test suite passes, a **Live GUI Test** is mandatory before any code merge; use the `visual-monitor-tests` harness if available.

---
## 14. EXPERIMENTS REQUIRED BEFORE FINAL IMPLEMENTATION

| # | Question | Hypothesis | Test / Metrics | Success Threshold |
|---|-----------|------------|-----------------|--------------------|
| 1 | LLM score threshold for promotion |
   | Scores above 0.90 correlate with low false‑positive rate when cross‑validated by multiple profiles. | Run historical dataset through evaluator; measure precision/recall if ≥ 90 %. | Precision ≥ 0.85 and recall ≥ 0.80 |
| 2 | Privacy scrubber efficacy |
   | A regex‑based whitelist filters > 95 % of PII instances without removing factual info. | Static analysis on synthetic dataset + manual audit on real proposals. | ≤ 5 % false positives, no false negatives in critical columns |
| 3 | Vector space alignment across profiles |
   | Vectors from different models are not directly comparable; cross‑profile similarity using same model yields meaningful clusters. | Train two embedding models (same vs different), compute pairwise cosine similarities, cluster quality via silhouette score. | Silhouette > 0.5 for cross‑profile pairs when same model applied |
| 4 | Push‑trigger synchronization scalability |
   | Trigger mechanism scales to ≥ 50 concurrent profiles with ≤ 1 s latency. | Load test with 50 fake profile DBs emitting events; measure notification time. | Latency ≤ 800 ms avg, no dropped events |
| 5 | Revocation audit trail consistency |
   | After revocation, original source still retains full record and collective entry is flagged but never removed. | Emit delete event; check both tables for content post‑revocation. | Both tables contain unchanged data with revocation flag set.

---
## 15. IMPLEMENTATION PHASES (SEQUENTIAL)

| Phase | Duration | Objective | Key Deliverables |
|-------|----------|-----------|------------------|
| **Phase 1 – Foundations** | 1 w | Validate current discovery scripts, schema inspector, and unit tests. | Updated README, passing test suite. |
| **Phase 2 – Mediation Service** | 2 w | Build the promotion pipeline: proposal object model, privacy filter, validator stub. | API endpoints (`/propose`, `/validate`), in‑memory state machine, logging. |
| **Phase 3 – Collective DB Schema** | 1 w | Implement SQLite schema for `collective_entries`, references, audit log. | DDL scripts, migration helper, integration tests against Mediation service. |
| **Phase 4 – Athena Interface** | 2 w | Athena UI plus read‑only query backend. | Query API, basic web view skeleton (constellation/table). |
| **Phase 5 – Vector & Embedding** | 2 w | Add vector support per profile and optional cross‑profile similarity service. | `sqlite_vec` wrappers, similarity queries. |
| **Phase 6 – Synchronization** | 1 w | Deploy trigger‑based sync for proposals from profiles. | Trigger schema changes, event listener, smoke tests.
| **Phase 7 – Revocation & Conflict** | 1 w | Implement revocation flagging and conflict resolution table. | Endpoints `/revoke`, audit log entries, UI toggle for conflicts. |
| **Phase 8 – Testing & Validation** | 2 w | Full test suite + live GUI test; run experiments to finalize thresholds. | CI pipeline with automated tests, experiment log. |
| **Phase 9 – Documentation & Clean‑up** | 1 w | Final spec revisions, README adjustments, release notes. | Updated docs, changelog entry. |

---
## Conclusions and Outstanding Decisions

- **Confirmed**: Tri‑layer architecture; reference‑based sharing; Athena as read‑only interface; strict privacy filter.
- **Experiment Needed**: LLM score threshold, vector alignment, push sync performance, revocation audit integrity.
- **Rejected/Changed**: Pope’s “0.92 score + 3‑source” rule is replaced by experimental validation logic (see §14). Athena bottleneck claim from Boss addressed by decoupling review logic.

---
> *Note:* This file shall be kept up‐to‐date in the `docs/` directory. Future changes to architecture proposals should be documented here before code modifications.
