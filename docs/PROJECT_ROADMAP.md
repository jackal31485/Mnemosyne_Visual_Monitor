# Mnemosyne Visual Monitor

## Project Roadmap (Long‑Term)

### Overview
The Mnemosyne Visual Monitor is a multi‑phase system that provides a visual and operational layer around the independent Mnemosyne memory stores used by Hermes profiles. The project evolves through nine distinct phases, each building on the architecture validated in the previous one.

1. **Foundations / Discovery** – Confirmed, read‑only discovery of Hermes/Mnemosyne installations and profile isolation.
2. **Mediation Plane / Air‑Lock** – Controlled boundary that accepts, filters, validates and promotes proposals from profiles before they reach the collective knowledge base.
3. **Collective Knowledge Base** – Reference‑based persistence layer for validated knowledge.
4. **Athena Interface / Collective Memory Interaction** – Enables Athena to query, explore and react to the collective store.
5. **Vector / Embedding / Knowledge Relationships** – Adds semantic similarity and relationship graphs over collective memories.
6. **Cross‑Profile Synchronization / Organic Learning** – Profiles learn from each other through validated collective references while maintaining isolation.
7. **Revocation / Conflict Resolution** – Handles stale, contradictory or revoked knowledge in the collective.
8. **Full Testing / Validation / Live GUI** – End‑to‑end integration and live UI validation.
9. **Documentation / Cleanup / Production Readiness** – Final polish for long‑term maintenance.

### Long‑Term Goals
| Goal | Why it matters |
|------|----------------|
| Organic Cross‑Profile Learning | Allows profiles to enrich each other's knowledge without merging private memories. |
| Profile‑Specific Recommendations | Athena can suggest relevant knowledge tailored to a target profile based on provenance and confidence. |
| Collective Memory Visualization | Provide constellation, table, timeline, and user‑management views so users understand how collective knowledge evolves and who created it. |
| User Management without Creation | Users may inspect/edit/delete entries but cannot create memories directly in the collective; they must come from Hermes profiles. |
| Athena Collective‑Knowledge Interaction | In future phases Athena will read and reason over both private and validated collective knowledge, enabling advanced assistance. |

### Phase Transition Rules
A phase is complete only when:
* All design documents are finalized and aligned.
* Implementation matches the document.
* Automated tests pass.
* Security/privacy boundaries are verified.
* Integration tests succeed.
* Documentation reflects reality.
* GUI (if applicable) has passed user‑scenario tests.

### Current Status
| Phase | Status |
|---|---|
| Foundations / Discovery | **COMPLETE** |
| Mediation Plane / Air-Lock | **COMPLETE** |
| Collective Knowledge Base | **COMPLETE** |
| Athena Interface / Collective Memory Interaction | **NEXT — PHASE 4** |
| Vector / Embedding / Knowledge Relationships | NOT STARTED |
| Cross-Profile Synchronization / Organic Learning | NOT STARTED |
| Revocation / Conflict Resolution | NOT STARTED |
| Full Testing / Validation / Live GUI | NOT STARTED |
| Documentation / Cleanup / Production Readiness | NOT STARTED |

Phase 3 was completed through the following domain milestones:

- **Phase 3A — Proposal Lifecycle:** proposal, validation, rejection, and promotion state enforcement.
- **Phase 3B — Collective Promotion Semantics:** promoted-reference querying, provenance preservation, and promotion-state enforcement.
- **Phase 3C — Collective Review & Revocation:** lifecycle state queries, revocation, audit-preserving provenance, and revoked-state handling.

The collective layer remains reference-based. Private Mnemosyne memory content is never copied into the collective database.

---
For the most up‑to‑date details see the individual Phase files: `docs/PHASE_1_FOUNDATIONS_REPORT.md`, `docs/PHASE_2_MEDIATION_DESIGN.md` and `docs/IMPLEMENTATION_SPECIFICATION.md`.
