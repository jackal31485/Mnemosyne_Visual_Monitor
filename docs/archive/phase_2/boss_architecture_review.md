# Architecture Review: Mnemosyne Visual Monitor
**Reviewer:** Boss (Senior Production-Code Reviewer)
**Date:** August 19, 2026
**Scope:** Overall System Architecture for Mnemosyne Knowledge Management

---

## 1. Verified Observations

The project is currently in **Phase 2A/B**. The current codebase is primarily a **read-only diagnostic and discovery engine**, rather than a full monitoring system.

*   **Runtime Discovery:** `src/discovery/utils.py` successfully maps the Hermes environment, identifying installation paths, venvs, and existing profile directories in `$HOME/.hermes/profiles`.
*   **Schema Inspection:** `src/discovery/mnemosyne_inspector.py` performs non-invasive SQLite introspection using `mode=ro`. It identifies tables, column types, primary keys, and detects vector extensions (`sqlite_vec`).
*   **Isolation Implementation:** The codebase adheres to the "no cross-profile write" constraint by exclusively utilizing read-only connections for discovery.
*   **Dependency Footprint:** The core discovery logic is lightweight, relying on the standard library and `sqlite_vec` where available, avoiding heavy dependencies that would complicate deployment in restricted environments.

## 2. Problems & Architectural Risks

### Gap Between Vision and Implementation
There is a significant "conceptual gap" between the README's goals (Collective Memory, Validation Models, Promotion) and the current source code, which only handles *inspection*. The system lacks the structural scaffolding to move from "seeing what exists" to "managing collective knowledge."

### Privacy Leakage during Proposal
The "Profile-Specific Learning" concept suggests tagging proposals for other profiles. Without a formal **Privacy Filter architecture**, there is a high risk that sensitive private context (embedded in the memory) could be proposed to the collective pool, violating profile isolation boundaries.

### The "Athena" Bottleneck
The README positions "Athena" as the Integrating Profile/Reviewer. Architecturally, if Athena is a standard Hermes profile, her knowledge grows linearly with the collective's success. This creates a single point of failure and a potential performance bottleneck for query resolution in the Collective Knowledge Base.

### Synchronization Staleness
Since the monitor is described as "stand-alone," there is no event-driven mechanism to notify the Monitor when a profile memory changes. The system relies on polling/re-scanning, which will not scale as the number of memories grows into the millions.

## 3. Recommendations

*   **Formalize the Promotion Pipeline:** Move away from "conceptual rules" to a defined **Proposal $\rightarrow$ Validation $\rightarrow$ Promotion** pipeline. This should be implemented as a separate service/module that manages a state machine for every proposed memory.
*   **Implement a Mandatory Privacy Scrubbing Layer:** Introduce a `PrivacyFilter` class that must be executed on any memory *before* it leaves the local profile boundary for the collective pool.
*   **Decouple "Athena" from "Reviewer Logic":** The logic for validation should reside in the Monitor's system architecture (the "Platform"), while Athena remains the "Interface." This prevents the reviewer's private store from becoming a proxy for the entire Collective DB.
*   **Versioned Schema Snapshots:** Instead of just inspecting current schema, implement Versioning for schemas to prevent the Visual Monitor from breaking when Hermes core updates its memory format.

## 4. Proposed Architecture

I propose a **Tri-Layer Knowledge Topology** to resolve the contradictions between isolation and collectivity:

### Layer 1: The Local Vault (Isolated)
*   **Storage:** Private SQLite DBs per profile.
*   **Access:** Strictly local. No external reads except via the RO Discovery engine.
*   **Responsibility:** Raw memory storage, local retrieval, personal context.

### Layer 2: The Mediation Plane (The "Air-lock")
*   **Function:** This is where the "Promotion" logic lives.
*   **Pipeline:** `Local Memory` $\rightarrow$ `Privacy Filter` $\rightarrow$ `Proposal Queue` $\rightarrow$ `Validator (Athena/Logic)` $\rightarrow$ `Cleaned Fact`.
*   **Responsibility:** Ensuring provenance, removing PII, and verifying the value of a fact before it becomes collective.

### Layer 3: The Collective Knowledge Base (Global)
*   **Storage:** A single, dedicated "Collective" SQLite DB (or future server-side PG).
*   **Access:** Read-only for all profiles; write-privileged only to the Mediation Plane.
*   **Responsibility:** Stable, validated truths and cross-profile recommendations.

### Local vs. Server Distribution (Unraid/Server)
| Component | Location | Reasoning |
| :--- | :--- | :--- |
| **Local Vaults** | **Local User Home** | Privacy, latency, and ownership. Must NOT be on server for high-security profiles. |
| **Mediation Plane** | **Local/Server Hybrid**| Logic can be central, but scrubbing *must* happen locally before transmission. |
| **Collective DB** | **Unraid/Server** | Enables persistence across hosts and acts as a "Knowledge Hub" for multiple users/profiles. |

## 5. Open Questions for Investigation

1.  **Trigger Mechanism:** How is a "Proposal" triggered? Does the agent decide to share, or does the Monitor detect "high-value" patterns during scanning?
2.  **Consensus Model:** What constitutes a "Validated" memory? Is it based on frequency (multiple profiles finding the same fact) or authority (Athena's stamp of approval)?
3.  **Revocation Flow:** If a profile deletes a memory that was previously promoted to Collective, does the Collective item trigger a cascading delete? How is this handled without the Collective DB having write-access back to Local Vaults?
4.  **Vector Space Alignment:** If multiple profiles use different embedding models for their vector stores, how will the "Constellation" view align them in a shared visual space?
