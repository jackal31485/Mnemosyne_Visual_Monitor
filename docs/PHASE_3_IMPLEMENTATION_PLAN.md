# Phase 3 Implementation Plan – Updated

---
## 1. Architectural Summary (Stage 0)

| Concept | Definition |
|---------|------------|
| **Private Mnemosyne Vault** | Individual, read‑write SQLite database per Hermes profile (`$HOME/.hermes/profiles/<profile>/mnemosyne.db`). Never merged or shared.
| **Mediation Plane (Mediator Service)** | Stateless application component that:
| | – receives proposals from a private vault,
| | – applies privacy filtering, validation and promotion logic,
| | – writes *reference‑only* rows into the collective knowledge database.
| | The Mediator is the only entity with **write** access to the collective database.
| **Collective Knowledge Database** | Single SQLite file (`data/collective.db`), schema described in §3. Stores reference data, provenance, timestamps, and validation metadata. Never contains raw private memory values.
| **Athena (Read‑Only Client)** | Service that performs **selects** against the collective database via a thin repository layer; no insert/update/delete capabilities.
| **Vector Search / Sync** | Not part of the Phase 3 MVP; only placeholders in the schema for future expansion.

---
## 2. Data‑Flow Diagram (Verbatim)
```text
Private Mnemosyne Vault
        │ proposal/event
        ▼
Mediator Service
   ├─ PrivacyFilter
   ├─ Validator
   └─ Promotion Decision → Collective DB
          ▲
          | read‑only Athena queries
```
---
## 3. Collective Schema (SQLite)
```sql
CREATE TABLE IF NOT EXISTS collective_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_profile TEXT      NOT NULL,
    origin_memory_id TEXT     NOT NULL,
    proposed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP,
    validator_profile TEXT,
    validation_score REAL,
    is_revoked BOOLEAN NOT NULL DEFAULT 0,
    revocation_reason TEXT
);

CREATE TABLE IF NOT EXISTS validation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER REFERENCES collective_entries(id),
    validator_profile TEXT,
    score REAL,
    result_text TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- placeholder for future vector columns and audit trail
```
---
## 4. Privacy / Reference‑Only Guarantees
| Item | What is stored in the collective DB | What is NOT stored |
|------|------------------------------------|--------------------|
| Raw value of a private memory | **Never** | The full text or serialized object from `mnemosyne.db`.
| Source profile, memory ID (UUID) | ✅ | None
| Timestamps (`proposed_at`, `validated_at`) | ✅ | None
| Validation metadata (`validator_profile`, `validation_score`) | ✅ | None
| Revocation flag & reason | ✅ | None
---
If a source memory changes, the reference in the collective DB remains valid; Athena can still resolve it via the stored ID. If the source is deleted, Mediator marks the entry revoked; Athena will see `is_revoked=1` and ignore it for active knowledge.
---
## 5. Staged Implementation Plan
| Stage | Objective | Files / Components Affected | Tests (Scope) | Acceptance Criteria | Review Gate |
|-------|-----------|-----------------------------|--------------|---------------------|------------|
| **0 – Architecture Freeze** | Finalise all architecture docs, schema and privacy definitions. | `docs/PHASE_3_IMPLEMENTATION_PLAN.md` | Documentation linter & SQL‑schema preview | Schema matches spec; diagram correct; all constraints documented. | *Human* review of the plan only |
| **1 – Collective DB Foundation** | Create SQLite store and DAO abstraction. | `src/domain/collective.py`; `scripts/setup_collective_db.py` | 3 tests: create, reopen, basic CRUD (no real data). | DB file created at `$PROJECT_ROOT/data/collective.db`; schema matches; can be reopened; no write access given to other components. | *Human* review of DAO functions and initial tests |
| **2 – Reference & Provenance Layer** | Persist reference‑only entries for proposals. | `src/domain/collective.py` (insert_entry), `tests/integration/test_collective_refs.py` | CRUD tests: insert valid, duplicate, cross‑profile, invalid; verify no raw data stored. | DB contains only allowed columns; foreign keys not required but check integrity; attempts to store raw content fail at code level. | *Human* review of collected database contents |
| **3 – Mediation Promotion Path** | Wire Mediator through privacy filter → validator → collective write. | `src/middleware/mediator.py`, existing API modules | Unit tests for each path branch; integration test promotes a dummy proposal, then checks DB row. | Successful promotion updates the row with correct provenance; privacy rejection or validation reject produce no DB writes. | *Human* review of mediation logic & database state |
| **4 – Revocation and Lifecycle** | Handle deletion/invalidation of source memories; mark entries revoked. | `src/middleware/mediator.py` revocation handlers, DAO update functions. | Integration test deletes a memory, triggers mediator, verifies `is_revoked=1`. Re‑revoke attempt no effect. | Revocation logs updated; no data deleted from collective DB. | *Human* review of lifecycle handling |
| **5 – Athena Read‑Only Interface** | Provide a thin repository for Athena to query the collective DB without write capability. | `src/api/athena.py`, DAO read wrappers | Negative tests: attempt UPDATE, DELETE → raises PermissionError; positive SELECT queries return expected columns. | No writes possible; read‑only integrity maintained. | *Human* review of API surface |
| **6 – Controlled Proposal/Event Interface** | Add an explicit call API for proposals (e.g., `submit_proposal(profile_id, memory_id)`). | `src/api/proposals.py` ; minimal in‑memory queue or synchronous call. | Test: submit proposal, verify it goes through mediation and DB write; duplicate proposal flagged. | Queue receives unique proposals only; idempotent handling.
---
| **7 – Full Phase 3 Integration Validation** | Run a full end‑to‑end scenario with multiple profiles. | All modules (Stage 0‑6) | End‑to‑end tests: create 2 profiles, propose from both, validate promotion, revoke one; Athena queries returns only active knowledge of first profile.
---
| **8 – Final Review and Preparation for Commit** | Package the MVP, run static‑analysis, update docs. | `Makefile`, `pyproject.toml` | Linter passes, tests pass, README updated. | *Human* approval to commit |
---
## 6. Acceptance Criteria Summary (per stage)
1. **DB file** created at the correct location with no write privileges for Athena.
2. **Insert entry** only accepts `source_profile`, `origin_memory_id`, and metadata – all other data is rejected or ignored.
3. **Promotion path** fully functional; no race conditions.
4. **Revocation** flags entries but does not delete them.
5. **Athena** cannot perform any write, every attempt fails with a clear error.
6. **Events / proposals** are idempotent; duplicate proposals are detected and ignored.
7. **End‑to‑end** tests confirm isolation per profile, privacy, provenance and read‑only enforcement.

---
## 7. Unresolved Questions (Pending User Decision)
1. Exact semantics of the `validation_score` threshold for auto‑promotion.
2. Whether Athena should expose a minimal set of columns or the entire reference row.
3. Future vector search placeholder columns / integration hooks.
4. Long‑term migration plan to PostgreSQL – what schema changes beyond SQLite will be required?

---
## 8. Stage 1 Starting Point
* Create `src/domain/collective.py` with a basic SQLite DAO and connection factory.
* Write the bootstrap script `scripts/setup_collective_db.py` that ensures `$PROJECT_ROOT/data/collective.db` exists and runs the schema creation.
* Implement unit tests in `tests/unit/test_collective_init.py` to assert file creation, schema integrity, CRUD ability, and isolation.

**Next action:** Human approval of Stage 0 (architecture) before proceeding to Stage 1 implementation.
