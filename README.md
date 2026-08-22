# Mnemosyne Visual Monitor

**Current Status: Phase 3 – Collective Knowledge Base COMPLETE**

The Mnemosyne Visual Monitor provides a visual and operational layer around the independent Mnemosyne memory stores used by Hermes profiles.

The core architecture is:

**Private Mnemosyne Memory → Mediation Plane / Air-Lock → Collective Knowledge Base**

Individual Hermes profiles retain independent private Mnemosyne databases. The collective layer stores validated references and provenance, not copies of private memory content.

---

## Completed Phases

### Phase 1 – Foundations / Discovery
**COMPLETE**

Established the project structure and read-only discovery of the local Hermes/Mnemosyne installation and profile isolation.

### Phase 2 – Mediation Plane / Air-Lock
**COMPLETE**

Established the controlled boundary between private profile memory and collective knowledge.

Implemented:

- Proposal handling
- Privacy filtering
- Validation
- Promotion controls
- Provenance tracking
- Metrics and diagnostics
- Reference-based sharing
- Protection against raw private-memory content crossing the boundary

The mediation layer does not merge the underlying profile memory stores.

### Phase 3 – Collective Knowledge Base
**COMPLETE**

Phase 3 established the domain-level collective knowledge lifecycle.

#### Phase 3A – Proposal Lifecycle
**COMPLETE**

Implemented:

- Collective proposal creation
- Validation lifecycle
- Rejection handling
- Promotion after successful validation
- Lifecycle-state inspection
- Reference-only proposal storage
- Provenance preservation

Lifecycle:

**PROPOSED → VALIDATED → PROMOTED**

Invalid transitions are rejected.

#### Phase 3B – Collective Promotion Semantics
**COMPLETE**

Implemented:

- Persistent `is_promoted` state
- Promoted-entry querying
- `get_by_source(source_profile, origin_memory_id)`
- Promotion-state inspection
- Provenance preservation during promotion
- Protection against duplicate promotion
- Protection against promotion before validation
- Verification that raw private-memory content is not stored

#### Phase 3C – Collective Review & Revocation
**COMPLETE**

Implemented:

- `list_by_state()`
- `list_proposed()`
- `list_validated()`
- `list_rejected()`
- `list_promoted()`
- `list_revoked()`
- Domain-level revocation
- Revocation reasons
- Duplicate-revocation protection
- Revocation of promoted entries
- Preservation of provenance and validation metadata
- Protection against promotion after revocation

Lifecycle semantics now include:

```text
PROPOSED
    |
    v
VALIDATED
    |
    v
PROMOTED
    |
    +-------> REVOKED

PROPOSED --------> REJECTED / REVOKED
VALIDATED -------> REVOKED
PY
