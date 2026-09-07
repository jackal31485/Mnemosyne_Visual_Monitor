# Phase 6.5C – Hermes Client Discovery and Mnemosyne Collection

## Design-Only / Not Implemented

- This phase contains only high-level architecture; the functionality is not yet built.
- Future implementation will follow the design below.

---

## Architectural Decisions Requiring Human Review

| Area | Assumption / Decision | Key Questions |
|---|---|---|
| Hermes installation/profile discovery | Existence of a standard `~/.hermes/profiles/<profile>` layout containing an SQLite database or sub-folder `mnemosyne.sqlite` | Are all Hermes installations consistent? How is the DB path determined? |
| Client/server communication | LAN clients will expose a REST JSON API (e.g., `/api/graph`, `/api/profiles`) on a known port | Which protocols (HTTP, HTTPS) and endpoint schema should be defined? |
| Authentication & trust | Mutual TLS or token-based auth between central server and client agents | Will we use mutual certificates, OAuth, JWTs? How are secrets distributed? |
| Profile identity | Profiles identified by deterministic lower-case ID derived from folder name; UI names human-readable | Are there collisions if two profiles share the same name? |
| Memory synchronization | Clients push change feeds (e.g., WAL logs or full DB dumps) to central server, filtered by provenance | How are incremental changes detected? What versioning schema? |
| Mediation/privacy filtering | Server is only allowed to query read-only endpoints; raw private memory never leaves client | How do we enforce this via API contracts and tooling? |
| Provenance model | Each memory has metadata (`source_profile`, timestamp) that travels unchanged | Are we retaining the original database primary key or normalizing it? |
| Revocation propagation | Clients periodically report revocation status; server applies “soft delete” rules | How do clients notify of revocations and how long is stale data kept? |
| Duplicate detection | Server merges based on unique memory identifiers and timestamps, dedupe by hash | What algorithm ensures no duplicates across multiple profiles? |
| Offline / reconnect behavior | Clients store unsynced events locally; upon reconnection they replay to server | How do we handle version mismatches or large backlog? |
| LAN discovery | Central service uses UDP multicast or simple DNS-SRV for clients to register | Will we need a heartbeat protocol for liveness detection? |
| Future Unraid deployment | Server will run as Docker container on Unraid; security and resource limits considered | Are the API ports exposed correctly, and is data persisted via volumes? |

## Design Scope

Phase 6.5C is a specification phase only. No networking, client agent, authentication, synchronization, or distributed-memory collection functionality is implemented by this document.

The intended end state is a central Mnemosyne service that can communicate with Hermes clients on the same network while preserving per-profile memory isolation and the existing mediation/privacy boundary.

These architectural decisions must be reviewed before implementation begins.
