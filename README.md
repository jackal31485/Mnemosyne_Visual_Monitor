# Mnemosyne Visual Monitor

## Current Status
**Phase 6.5A – Read‑Only Graph HTTP API COMPLETE**

This repository houses the read‑only web layer that serves a deterministic graph representation of the collective knowledge base used by Hermes profiles.

## High‑level Architecture
```
Private Mnemosyne Memory                →   Mediation Plane / Air‑Lock      →   Collective Knowledge Base   →   Graph / Visualization Layer
```
* **Profile Isolation** – Each Hermes profile owns its own private SQLite database; the Visual Monitor never merges these databases.
* **No raw memory exposure** – Every API or graph output deliberately omits embeddings, file paths, and any data that is not explicitly part of the public contract.

## Completed Phases
1. **Phase 1 – Foundations / Discovery** *(COMPLETE)*  – project structure and discovery logic for Hermes/Mnemosyne installations.
2. **Phase 2 – Mediation Plane / Air‑Lock** *(COMPLETE)*  – privacy filtering, proposal/validation lifecycles, promotion controls, provenance tracking.
3. **Phase 3 – Collective Knowledge Base** *(COMPLETE)*  – reference‑only data stores, validation, promotion, revocation, and domain‑level state machine.
4. **Phase 6 – Constellation Graph Generation** *(COMPLETE)*  – `services/graph_service.py` provides deterministic graph generation, node/edge ordering, per‑node edge limits, source‑profile filtering, and embargoed data handling.
5. **Phase 6.4A – Graph Serialization** *(COMPLETE* – commit `b8acafc`)
   * Implements `_to_node_dict`, `_to_edge_dict` and JSON‑compatible contract returned by `GraphService.get_graph()` without leaking private content.
6. **Phase 6.5A – Read‑Only Graph HTTP API** *(COMPLETE)*
   * FastAPI application exposing `/api/graph`.
   * Supports query parameters: `source_profile` (optional) and `edge_limit` (non‑negative integer, optional).
   * Uses Pydantic models (`NodeDTO`, `EdgeDTO`, `GraphResponse`) matching the original serialization.
   * Configuration is environment‑based: each profile’s database path is supplied via a variable of the form
     `MNEMOSYNE_GRAPH_DB_<PROFILE>=/path/to/database.sqlite` – no hardcoded paths are present in source code.
   * The project lists its runtime dependencies in `requirements.txt`:
     ```
     fastapi>=0.141,<1
     uvicorn>=0.52,<1
     ```
   * Manual validation performed: app imports correctly, `/api/graph` returns 200, edge‑limit constraints produce 422 via FastAPI, and an empty graph yields `{"nodes": [], "edges": {}}`.  No formal API test suite has been written yet; it is deferred for later phases.

## Current Repository State
* **Branch**: master
* **Latest Phase 6.5A commit**: `411a07f` – “Implement Phase 6.5A read‑only graph API”
* **Pushed to origin/master**; the only remaining untracked paths are `skills/` and `tmp/`, which are unrelated to this implementation.

## Next Planned Milestone – Phase 6.5B/UI Integration
Phase 6.5B aims to provide a lightweight web UI that consumes `/api/graph` and presents the graph in multiple interactive views:
* **Constellation view:** node‑centric force‑directed layout.
* **Table view:** tabular representation of nodes/edges with sortable columns.
* **Timeline view:** historical snapshot of the graph over time (planned).
All UI components will continue to respect profile isolation and operate only on data exposed by the read‑only API layer.  An eventual All Profiles visualization may display relationships across Hermes profiles, but it must never merge the underlying independent Mnemosyne databases. Profile isolation remains an architectural invariant.

## References
* [Phase 6 Architecture Decision](docs/PHASE_6_ARCHITECTURE_DECISION.md)
* [Phase 6.4A Implementation Detail](docs/PHASE_6_4A_IMPLEMENTATION.md)
* [Next Phase 6 Plan & Roadmap](docs/NEXT_PHASE_6_PLAN.md)

> The project remains firmly grounded in a local‑first development philosophy: Unraid integration, remote synchronization, backup/restore, and server‑side deployment are outside the scope of current and upcoming phases unless explicitly added later.
