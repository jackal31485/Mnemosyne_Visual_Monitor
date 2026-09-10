# Mnemosyne Visual Monitor

Mnemosyne Visual Monitor is the Browser and monitoring layer for the Hermes
distributed memory system.

It provides a governed visual interface for inspecting collective memory,
profiles, relationships, activity, provenance, and retrieval results while
preserving the separation between local profile memory and the collective
reference/provenance layer.

## Current architecture

Each Hermes profile maintains its own local Mnemosyne database.

The collective database:

`data/collective.db`

acts as the central reference, provenance, promotion, revocation, and
retrieval-authorization layer. It is not a replacement for the individual
profile databases.

Athena provides the read-only API boundary used by the Browser.

The Browser does not directly create memories or bypass the governed memory
lifecycle.

## Current capabilities

- Multi-profile collective visualization
- 2D and 3D constellation views
- Profile tiles
- Data and information views
- Activity and timeline views
- Collective status and validation views
- LAN discovery and distributed profile adoption
- Governed collective ingestion
- Semantic retrieval
- Keyword/BM25 retrieval
- Graph expansion
- Temporal filtering/signals
- Reciprocal Rank Fusion
- Optional local CrossEncoder reranking
- Hybrid retrieval explainability
- Controlled source-memory inspection
- Provenance and lifecycle visibility

## Phase status

Phases 1–7 established the core Mnemosyne Visual Monitor, collective
ingestion, visualization, distributed discovery, and Browser infrastructure.

**Phase 8 — Hybrid Retrieval:** Complete

**Phase 9 — Browser-Facing Hybrid Retrieval Integration:** Complete

Phase 9 exposed the governed hybrid retrieval pipeline through the Browser,
including profile/date filtering, explainability, reranking visibility, and
controlled result inspection. Production validation also addressed SQLite
thread safety and qualified collective profile identity resolution.

**Next: Phase 10 — Entity & Relationship Intelligence**

The remaining roadmap covers increasingly capable entity resolution,
relationship intelligence, temporal reasoning, evidence-backed synthesis,
higher-level mental models, controlled cross-profile learning, retrieval
optimization, distributed federation, governance hardening, and final
productionization.

## Development

Activate the project virtual environment before running development tools:

```bash
cd ~/Documents/Hermes/projects/Mnemosyne_Visual_Monitor
source .venv/bin/activate
