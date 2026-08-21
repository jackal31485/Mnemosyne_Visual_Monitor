# Phase 2 Implementation Plan

The following document reconciles the **Phase 2 Mediation Plane** design with concrete implementation requirements for the sub‑phases 2.4–2.10. Each requirement is classified as *ESTABLISHED*, *INFERRED*, *PROPOSED*, or *OPEN* based on evidence found in project files, tests, and documentation.

---

## 2.4 Metrics Panels

### Objective
Expose runtime metrics about the proposal pipeline (counts per state, latency, etc.) while preserving privacy and profile isolation.

### Evidence from Existing Project
- **No explicit mention** of metrics in *docs/PHASE_2_MEDIATION_DESIGN.md*, *IMPLEMENTATION_SPECIFICATION.md*, or code. The design focuses on proposals, privacy, validation, and collective promotion. (Source: the entire spec document; see [Design section §3](#state-machine)).

#### ESTABLISHED Requirements
- None.

#### INFERRED Requirements
- The mediation plane maintains an in‑memory queue of proposals to enforce processing order – this implies that some metrics can be derived from state transitions. (Inference based on state machine, not explicit.)

#### PROPOSED Design
| Requirement | Classification | Evidence |
|-------------|----------------|----------|
| Provide a read‑only JSON endpoint `/metrics` returning aggregated counts of proposals per state and average processing latency. | **PROPOSED** | No existing API endpoints; common in related projects.
| Ensure metrics do not contain any raw proposal data (privacy). | **PROPOSED** | Inferred from privacy constraints.
| Allow authenticated Athena queries only. | **PROPOSED** | Standard for internal monitoring APIs.

#### OPEN Decisions
- Whether to expose metrics as a separate HTTP endpoint or embed them in existing `/health` response.
- Persist the latest metrics snapshot in an out‑of‑process store (e.g., Redis) for high availability.

### Existing Components
- None directly support metrics yet.

## 2.5 Advanced Diagnostics

### Objective
Provide advanced diagnostic information about the mediation plane’s internal state and health (e.g., memory usage, proposal queue depth).

### Evidence from Existing Project
- The current design does not specify diagnostics; there are no tests or modules related to diagnostics.

#### ESTABLISHED Requirements
- None.

#### INFERRED Requirements
- Health monitoring is often required for production deployments (see Project Roadmap, Phase 9).

#### PROPOSED Design
| Requirement | Classification |
|-------------|----------------|
| Expose `/diagnostics` endpoint returning JSON with uptime, queue depth, and recent activity. | **PROPOSED** |
| Provide an optional WebSocket stream for real-time updates. | **PROPOSED** |

#### OPEN Decisions
- Scope of diagnostics data: only high‑level metrics vs. full stack trace.
- Authentication requirements for diagnostic endpoints.

## 2.6 Unit Tests

### Objective
Ensure each component of the mediation plane functions correctly and regressions are caught early.

### Evidence from Existing Project
- **Existing tests** in `tests/` cover profile discovery, isolation, and vector loading (`test_profile_isolation_and_misc.py`).
- No current unit tests target *mediator*, *validator*, or *privacy filter* components yet.

#### ESTABLISHED Requirements
| Test Area | Evidence |
|-----------|----------|
| Validate that the Mediation Plane enforces state transitions as per §3 of the design. | Design explicitly defines PROPOSED → PRIVACY_FILTERING → VALIDATING transitions.
| Confirm privacy filter removes PII fields before promotion. | PrivacyFilter interface defined in spec.

#### INFERRED Requirements
- Test coverage for error handling (e.g., missing memory, invalid proposals).
- Mocking of external dependencies (memory gateway, LLM validator) to avoid network calls in unit tests.

#### PROPOSED Design
- Create a test suite using `pytest` that mocks the **MemoryGateway** and **Validator** interfaces. The test harness will run through the full pipeline for both acceptance and rejection paths.
- Add snapshot tests for JSON responses of each state transition.

## 2.7 Integration Tests

### Objective
Verify end‑to‑end operation of the mediation plane in a simulated runtime environment.

### Evidence from Existing Project
- No integration tests beyond unit level exist. The design requires that a proposal be promoted to the collective after successful validation.

#### ESTABLISHED Requirements
| Test | Evidence |
|------|----------|
| POST /propose with valid token triggers `PROPOSED` state. | Design API spec (§6 of docs/PHASE_2_MEDIATION_DESIGN.md).
| The same proposal eventually reaches the collective `collective_entries` table. | Spec §8 (Collective DB schema) specifies this behavior.

#### INFERRED Requirements
- Proper handling of concurrent proposals.
- Persistence and visibility across service restarts.
- Auditing entries in `audit/` directory.

## 2.8 Performance / Scalability Benchmarks

### Objective
Establish baseline performance characteristics for the mediation plane, particularly how many concurrent proposals can be processed with acceptable latency.

### Evidence from Existing Project
- No performance benchmarks exist. The spec acknowledges that performance analysis is pending (see §14 Experiments). 

#### ESTABLISHED Requirements
- None directly; performance limits are *experimental*.

#### PROPOSED Design
| Benchmark | Classification |
|-----------|----------------|
| Throughput of 100 proposals per second with <200 ms latency target. | **PROPOSED** |
| Memory footprint under peak load. | **PROPOSED** |

## 2.9 Revocation / Deletion Flow

### Objective
Handle revocation events when a source profile deletes a private memory that has already been promoted.

### Evidence from Existing Project
- The design in §11 describes a *revocation event* but there is no implementation. No tests exist for this case.

#### ESTABLISHED Requirements
| Requirement | Evidence |
|-------------|----------|
| When source deletes a memory, the collective entry should be flagged `is_revoked = 1`. | Spec §11 (Revocation).
| Provenance chain must still map to original source profile. | Design section on provenance.

#### INFERRED Requirements
- The mediation plane must receive deletion events from a profile’s DB; currently no such mechanism is described.

## 2.10 Documentation & Release Notes

### Objective
Maintain accurate, up‑to‑date documentation reflecting implemented functionality and decisions.

### Evidence from Existing Project
- Multiple design docs exist but are out of date with respect to actual implementation (see README, Phase 1 Report).
- No structured release notes are in the repo.

#### ESTABLISHED Requirements
| Documentation File | Evidence |
|---------------------|----------|
| `docs/IMPLEMENTATION_SPECIFICATION.md` | Must be updated with final architecture. |
| `CHANGELOG.md` (if present) or equivalent | Not yet existing; should capture changes per commit.

### Open Decisions
- Where to host release notes: a separate `CHANGELOG.md`, section in documentation, or an external wiki?
- Format and level of technical detail required for end users versus developers.

---

## Summary of Requirement Classifications
| Sub‑Phase | ESTABLISHED | INFERRED | PROPOSED | OPEN |
|-----------|-------------|----------|---------|------|
| 2.4 Metrics Panels | 0 | 1 (state queue inference) | 3 | 2 |
| 2.5 Advanced Diagnostics | 0 | 1 (health monitoring) | 2 | 2 |
| 2.6 Unit Tests | 2 (transitions, privacy) | 2 | 0 | 0 |
| 2.7 Integration Tests | 2 | 2 | 0 | 0 |
| 2.8 Performance Benchmarks | 0 | 0 | 2 | 0 |
| 2.9 Revocation Flow | 1 (revocation flag) | 1 | 0 | 0 |
| 2.10 Documentation | 2 (spec updates) | 1 | 0 | 1 |

*Numbers indicate how many items for each classification within that sub‑phase.*
