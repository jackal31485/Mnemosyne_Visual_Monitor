# Phase 6 – Collective Visualization
## Overview
Phase 6 builds upon the semantic‑embedding foundation of Phases 1‑5 to create a read‑only view of collective knowledge that
• preserves provenance, privacy and lifecycle integrity,
• exposes only metadata required by Athena, and
• does not merge or duplicate profile databases.

> **Architectural guarantee** – A consumer cannot deduce private profile contents or embedding blobs; only the aggregated contract is exposed.

## 6.1 — Read‑Only Domain Contract
The consumer interface must be a *pure read‑only* data plane backed by an underlying DAO that performs persistence. The contract exposes:

```
id: int
source_profile: str         # originating Hermes profile (immutable)
orign_memory_id: str        # key in the private reference store
proposed_at: str | None     # ISO timestamp of proposal
validated_at: str | None    # ISO timestamp of validation, if any
validator_profile: str | None  # validator identity, if validated
validation_score: float | None
lifecycle_state: Literal["promoted", "rejected", "revoked"]
```

### Why these fields?
* **Provenance** – `source_profile` & `origin_memory_id` are the essential lineage ties; exposing them is mandatory for traceability but they remain immutable.
* **Lifecycle** – The three possible states (`promoted`, `rejected`, `revoked`) summarize the internal flags (`is_promoted`, `is_revoked`).  Exposing an explicit enum simplifies consumer logic while still honouring privacy/merging rules.
* **Temporal metadata** – timestamps and validation data allow consumers to reason about recency while not revealing raw content.

> The contract purposefully omits:
- `is_promoted` / `is_revoked` flags (internal).
- Raw embedding BLOBs stored in the Phase 5 database.
- Private profile memory contents or SQLite/database details.

These implementation details remain internal to the DAO and cannot surface through the consumer API.

## 6.2 – Cross‑Profile Aggregation
(Design only – implementation pending). An aggregator will:
1. Query each profile’s DAO independently.
2. Combine results into a single read‑only stream that respects visibility rules.
3. Ensure *no* profile database is merged or copied.

> The aggregation layer must preserve the privacy boundary: it can only read data already exposed by Athena, never raw private entries.

## 6.3 – Semantic Relationship Querying
(Will be addressed in Phase 6.3). The query surface may provide similarity relationships without exposing embeddings or internal flags.

## 6.4 – Constellation Representation (graph)
(Conceptual design remains for future phases.)

## 6.5 – Tabular View
Consumers can request a plain‑table representation of the contract fields; pagination and caching are left open to later design decisions.

## 6.6 – Timeline Tracking
The aggregator should expose chronological events (`validated_at`, `promoted_at`) for each entry in a separate timeline API – again with no direct database access.

## 6.7 – Provenance & Privacy Guarantees
All data reaching the consumer is sourced from Athena’s read‑only wrapper, which enforces:
* **No access to private memory** – only provenance IDs are exposed.
* **Promotion/Revocation filtering** – only promoted, non‑revoked entries surface via `list_promoted` and related query methods.

## 6.8 – Revision & Revocation Controls
Consumer APIs can *query* the set of revoked or rejected entries but cannot create new collective records – this is strictly read‑only, mirroring Phase 5’s lifecycle management.

## 6.9 – Integration Testing and Coverage
Unit tests will target:
- Visibility rules (promoted & not revoked).
- Correct mapping from internal flags to `lifecycle_state`.
- Exposure of provenance fields.
- Preservation of privacy boundaries.

> Existing `tests/unit/test_athena_interface.py` already exercise the current visibility logic; new tests will validate the mapping into the contract structure.

# Summary of Document‑Only Work
* Replaced Phase 6 sections with a clear read‑only contract definition.
* Removed speculative implementation details (e.g., embedding exposure).
* Left placeholders for future cross‑profile aggregation and relationship querying.

**This document contains only documentation changes; no source code or tests were modified.**