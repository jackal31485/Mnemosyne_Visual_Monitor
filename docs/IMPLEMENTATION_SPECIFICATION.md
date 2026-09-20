# Mnemosyne Visual Monitor — Current Architecture & Implementation Specification

> **Status:** Phase 16 complete — Phase 17 Governance, Audit & Security Hardening next
>
> **Last updated:** 2026-09-20
>
> **Authority:** This section records the current implemented architecture
> through completion of Phase 15. Where historical sections below describe
> proposed, experimental, or superseded architecture, the implemented
> repository, `docs/PROJECT_ROADMAP.md`, and current phase-specific governance
> documents take precedence.

## Current Project State

Phase 15 — **Advanced Retrieval Optimization** — is complete.

The implemented architecture now includes the capabilities established through
Phases 1–15, including:

- profile-local memory isolation;
- governed collective knowledge;
- provenance and evidence preservation;
- entity and relationship intelligence;
- temporal evidence and temporal retrieval;
- evidence-preserving consolidation;
- higher-level governed mental models;
- controlled cross-profile learning and explicit transfer;
- hybrid lexical and semantic retrieval;
- query classification and retrieval routing;
- governed candidate generation;
- evidence and temporal retrieval signals;
- reranking diagnostics;
- multilingual retrieval fallback;
- retrieval evaluation and diagnostics.

Phase 15 optimizes retrieval over knowledge that is already eligible under the
existing governance model. Retrieval optimization does not authorize, adopt,
revoke, or synchronize knowledge.

The current repository baseline is:

    master
    75097a3 Phase 15 completion: Advanced Retrieval Optimization
    phase-15-complete

The Phase 15 documentation archive is:

    docs/archive/phase-15/

The authoritative Phase 15 completion audit is:

    docs/PHASE_15_COMPLETION_AUDIT.md

## Phase 15 Architecture

The Phase 15 retrieval pipeline is:

    Query
      |
      v
    Normalization
      |
      v
    Query Classification
      |
      v
    Retrieval Routing
      |
      +--> lexical / BM25 signals
      +--> semantic signals
      +--> exact-match signals
      +--> entity / relationship signals
      +--> temporal signals
      +--> evidence signals
      |
      v
    Governance Filtering
      |
      v
    Reranking / Result Ordering
      |
      v
    Diagnostics / Explanation
      |
      v
    Governed API / Browser Projection

Phase 15 retrieval optimization preserves these governance invariants:

- promoted and non-revoked eligibility;
- profile isolation;
- source profile and source memory provenance;
- evidence provenance;
- temporal meaning and precision;
- conflict visibility;
- deterministic behavior where required;
- safe fallback behavior;
- no raw private content leakage;
- no implicit learning or synchronization.

Query classification is routing information, not authorization.

Retrieval ranking and evaluation metrics cannot authorize, adopt, revoke, or
synchronize knowledge.

## Phase 16 — Distributed Collective / LAN Federation

Phase 16 is **complete**.

Its purpose is to extend controlled collective knowledge exchange across trusted
local Mnemosyne instances without converting the system into an unrestricted
shared memory store.

Phase 16 must establish explicit boundaries for:

- instance identity;
- peer discovery;
- trust establishment;
- authenticated communication;
- capability and authorization checks;
- governed knowledge exchange;
- synchronization state;
- conflict detection and visibility;
- explicit adoption;
- revocation propagation;
- federation observability;
- immutable audit history.

The federation boundary is:

    Mnemosyne Instance A
            |
            | authenticated / governed exchange
            v
    Federation Boundary
            |
            +--> identity
            +--> trust
            +--> authorization
            +--> provenance
            +--> conflict handling
            +--> revocation
            +--> audit
            |
            v
    Mnemosyne Instance B

Phase 16 must preserve the existing architectural invariants:

1. Profile-local memory remains isolated.
2. Raw private memory is not exposed by default.
3. Collective knowledge remains governed.
4. Provenance remains attached to exchanged knowledge.
5. Source and destination identities remain explicit.
6. Authorization remains explicit.
7. Adoption remains explicit.
8. Revocation remains enforceable.
9. Conflicts remain visible.
10. Federation activity remains auditable.
11. Audit history is not destructively deleted.
12. Peer visibility does not constitute adoption.

Phase 16 must not:

- expose profile-local raw memory by default;
- bypass collective governance;
- create implicit cross-profile learning;
- silently synchronize private profile databases;
- erase provenance;
- delete audit history;
- treat peer visibility as adoption;
- bypass revocation;
- introduce unrestricted shared writes;
- make Athena an implicit participant.

Phase 16 is distinct from Phase 17. Phase 16 establishes the federation
architecture and its governance boundaries. Phase 17 performs the broader
governance, audit, adversarial, and security-hardening work.

## Phase 14 — Architectural Lineage

Phase 14 — **Cross-Profile Learning & Controlled Transfer** — is complete.

Its controlled transfer lifecycle established explicit authorization,
applicability analysis, evidence validation, adoption, conflict handling,
revocation, rollback, and immutable transfer audit history.

The Phase 14 architecture remains the foundation for Phase 16 federation:
federation extends governed exchange; it does not replace the controlled
transfer and adoption model.

## Historical / Superseded Architecture

> The material below is retained for architectural history and traceability.
> It predates the current Phase 10–15 implementation state and must not
> override the current repository, roadmap, or phase-specific governance
> documentation.
>
> The original material includes proposed designs, experiments, and a
> sequential Phase 1–9 implementation plan. Those materials are historical
> references, not the active implementation roadmap.

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
