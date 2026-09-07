# Phase 2 Mediation Plane Design

## 1. Architectural Boundary
**What enters the Mediation Plane**
* **Proposals** – JSON payloads that contain only a *reference* or the sanitized representation of data the user wishes to promote.
* **Authentication metadata** – bearer tokens used to confirm the requesting profile and its permission level.

**What leaves the Mediation Plane**
* **Audit / provenance records** – immutable logs in `audit/` that chronicle each state transition.
* **API responses** – concise JSON indicating status, errors, or next steps.

**What it can access**
* A *Memory Gateway* interface for the originating profile.  The plane requests a single memory via `gateway.get_memory(profile, memory_id)` and receives a sanitized representation; no direct file system or SQLite IO is performed by the plane itself.
* In‑memory state of proposals while they are being processed.

**What it cannot access**
* Raw private Mnemosyne data – the plane never opens any profile database on disk.
* Direct writes to the Collective Knowledge Base; promotion payloads are returned to the caller for eventual storage in Phase 3.

### Rationale
By insisting on a constrained, per‑profile gateway, we enforce that the Mediation Plane can only retrieve memory when explicitly requested by the source profile. This keeps Athena and other profiles isolated from each other’s private data and guarantees the Air‑Lock boundary `Private Profile → Proposal → Mediation Plane → Collective`.

## 2. Proposal Data Model
| Field | Type | Description |
|---|---|---|
| `proposal_id` | UUID v4 | Unique proposal identifier |
| `source_profile` | string | Name of the profile submitting the proposal (must match auth token) |
| `source_memory_id` | string | Primary key of the memory record within that source profile’s database |
| `proposed_at` | ISO 8601 UTC | Timestamp of submission |
| `proposal_type` | enum (`REFERENCE`) | Only reference‑based proposals are supported in Phase 2 |
| `source_reference` | object | `{profile: <name>, memory_id: <id>}` – a lightweight pointer to the source memory |
| `validation_representation` | object | Transient sanitized output produced by the privacy filter; **not** persisted beyond validation. |
| `state` | enum | Current state of processing (see §3) |
| `provenance` | object | Metadata such as tags or user comments |
| `privacy_filter_result` | object | Result of filtering: `{masked_fields: [...], sanitized_content?: string}` |
| `validation_history` | array | Sequence of validation stages (`{stage, result, score?, reason?}`). |

*No field contains raw private memory content.*

## 3. State Machine
```
PROPOSED → PRIVACY_FILTERING → VALIDATING
                ↘             ↙
                 REJECTED     READY_FOR_PROMOTION
                                      ↓
                                 APPROVED / READY_FOR_PROMOTION (final phase‑2 state)
                               (or MANUAL_REVIEW)
```
* `READY_FOR_PROMOTION` is the terminal state for Phase 2.  Actual persistence to the Collective and transformation to a `PROMOTED` entry occur in Phase 3.
* Invalid transitions—e.g., jumping from PROPOSED straight to APPROVED—return an error response (409/422).

## 4. Memory Gateway Interface
```python
class MemoryGateway(Protocol):
    def get_memory(self, profile: str, memory_id: str) -> SanitizedContent:
        """Return a sanitized representation of the specified memory.
        The gateway must perform any necessary read and filtering but never expose raw database files or allow arbitrary SQL.""
```
The Mediation Plane depends solely on this abstraction.  Each Hermes profile implements its own gateway; no direct file access is permitted within the plane’s code path.

## 5. PrivacyFilter Interface
```python
class PrivacyFilter(Protocol):
    def filter(self, content: SanitizedContent) -> PrivacyResult:
        """Apply deterministic PII masking to the supplied content and return a mask report.""
```
The plane calls `filter` on the payload returned by the gateway.  The result feeds into state transition logic.

## 6. Validator Interface
```python
class Validator(Protocol):
    def validate(self, representation: SanitizedContent, proposal: Proposal) -> ValidationOutcome:
        """Perform provenance checks, structural validation, optional LLM scoring, and return approval status.""
```
The validator receives both the sanitized content and the full proposal metadata.

## 7. Identity‑Provider Interface
A minimal test provider is used in Phase 2: an in‑memory mapping of token → profile.  No external authentication service is required.

## 8. Audit Store
Immutable JSON files are written under `audit/` on each state change.  The plane never modifies or deletes audit records.

## 9. API Contracts
### `/propose`
| Method | Path |
|---|---|
| POST | `/propose` |
#### Request Body (example)
```json
{
  "source_profile": "athena",
  "source_memory_id": "123e4567-e89b-12d3-a456-426614174000",
  "proposal_type": "REFERENCE"
}
```
The plane internally invokes the Memory Gateway, runs privacy filtering and validation.  The initial response is `201 Created` with `{"proposal_id": …, "state": "PROPOSED"}`.

### `/validate/{proposal_id}`
| Method | Path |
|---|---|
| POST | `/validate/{proposal_id}` |
#### Response
* **200 OK** – e.g., `{"state": "READY_FOR_PROMOTION", …}`.
* **422 Unprocessable Entity** – validation failure explanation.

### Authentication
Bearer token containing a `sub` claim equals the profile name.  Mismatch → **401 Unauthorized**.

## 10. Phase‑2 Persistence
* Proposals remain in memory until they reach the terminal state (`READY_FOR_PROMOTION`).  Restarting the service drops all pending proposals – *intentional*.  Audit logs survive across restarts for forensic traceability.
* No Collective DB is created yet; promotion payloads are returned to the caller, who will commit them in Phase 3.

## 11. Testing Plan (Pytest)
| Test | Purpose |
|---|---|
| `test_propose_valid()` | POST with correct payload → 201 and PROPOSED state |
| `test_invalid_token()` | Wrong auth token → 401 |
| `test_memory_gateway_access()` | Verify plane can only call `gateway.get_memory` for the source profile; no file/DB IO is performed. |
| `test_privacy_filter_reject()` | Filter produces a failed mask → REJECTED state and audit log. |
| `test_validator_score_fail()` | Validation score below threshold → REJECTED. |
| `test_terminal_state()` | End‑to‑end flow reaches `READY_FOR_PROMOTION` and no further promotion occurs in Phase 2. |
| `test_manual_review_branch()` | Proposal moved to MANUAL_REVIEW then manually approved → `READY_FOR_PROMOTION`. |
| `test_source_mismatch()` | Submit proposal for a profile different from auth token → 401. |
| `test_reference_only_promotion_payload()` | Verify that the promotion payload returned by the API contains only `{profile:memory_id}` – no raw content. |
| `test_restart_drops_in_memory()` | Restart server mid‑proposal; audit logs remain, in‑memory state lost. |

Each test spins up a FastAPI `TestClient`, uses an isolated memory gateway that simulates reading the source profile via an in‑memory SQLite DB, and verifies all assertions.

## 12. Explicit Phase‑2 Scope Boundary
| Feature | Implemented in Phase 2? |
|---|---|
| Collective DB schema & migrations | **No** (Phase 3) |
| Cross‑instance synchronization | **No** |
| Revocation or de‑provisioning of promoted references | **No**, placeholder only |
| Conflict resolution (Phase 7) | **No** |
| Vector sharing / similarity checking | **No** |
| GUI components for Mediation Plane | **No** |
| Deployment on Unraid or other orchestration | **No** |

## 13. Open Decisions & Experiments
* Privacy‑filter algorithm selection (regex vs LLM) and efficacy metrics.
* Determining optimal LLM scoring threshold via empirical data collection.
* Measuring latency for Athena to fetch referenced memories once Phase 3 promotion logic is in place.
* Audit retention duration and archival policy.

---
**Corrections Applied**
1. Added `MemoryGateway` abstraction to eliminate direct database/file access by the plane.
2. Removed redundant `content_ref`; now `source_reference` vs transient `validation_representation` are clearly separated.
3. Renamed terminal state from `PROMOTED` to `READY_FOR_PROMOTION` (marked as Phase‑2 end).
4. Updated tests: replaced collective‑storage test with a reference‑only promotion payload check.
