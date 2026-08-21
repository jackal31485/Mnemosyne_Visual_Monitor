# Athena Architecture Synthesis: Mnemosyne Visual Monitor

## Learning Matrix
| Aspect | Boss | Hawk | Pope |
|--------|------|------|------|
| **Profile Isolation** | Confirmed via read‑only inspection. | Physical separation and unit‑tests affirm isolation. | Accepted; no cross‑profile mutations.
| **Discovery Engine** | Functional `src/discovery/*`. | Same modules, validated by tests. | Acknowledged; no new discovery features proposed.
| **Vector Support** | Detects `sqlite_vec`, tables prefixed `vec_`. | Explicit check of vector tables and WAL/SHM presence. | Not addressed—no contradiction.
| **Collective Layer** | Tri‑layer proposal (Vault → Mediation → Collective DB). | Reference‑based sharing; never copy data. | Proposes reference strategy but leaves implementation open.
| **Privacy Filter** | Mandatory layer before promotion. | Implied by “never copy” principle. | Acceptable; no details for enforcement.
| **Promotion Pipeline** | Formal Proposal → Validation → Promotion state machine. | Consistent with Boss: tracking provenance, validation history. | Suggests 3‑point corroboration and score threshold (0.92) – *investigate*.
| **Athena’s Role** | Reviewer interface; logic decoupled from Athena to avoid bottleneck. | No explicit mention of Athena – implicit by profile‑independence. | Explicitly positions Athena as the review/aggregation profile.

## Agreements
1. **All reviews agree** that each Hermes profile must retain its own private SQLite database; no merging is allowed.
2. Discovery and schema inspection are performed read‑only with WAL/SHM checks, ensuring safety.
3. Collective knowledge must be *referenced*, never copied, to maintain isolation.
4. A privacy filter / scrubber is required before any memory leaves its local store.
5. Validation must record provenance (source profile, timestamp) and support a revocation flow.

## Disagreements & Uncertainties
| Point | Conflicting Claims |
|-------|--------------------|
| Athena as bottleneck | Pope names Athena the reviewer; Boss recommends decoupling logic. | **Recommendation**: keep Athena only as an interface; actual validation runs in a dedicated Mediation service.
| Promotion threshold | Pope proposes 0.92 LLM score, 3‑point corroboration. | No validation evidence – **needs experimentation** to set thresholds and scoring models.
| Reference vs. table storage | Hawk suggests explicit reference tables within collective DB. | Acceptable; Boss's tri‑layer model allows such a table in the Collective layer.

## Architectural Decisions (confident)
- Adopt a **Tri‑Layer Knowledge Topology**: Local Vault → Mediation Plane → Collective Knowledge Base (single DB).
- Enforce **Profile‑Level Privacy Filter** that strips PII and ensures only relevant data is promoted.
- Store **Provenance Metadata** in both local and collective tables (`source_profile`, `validation_history`).
- Use a **Reference‑Based Sharing Model**; the Collective DB will contain *references* (profile:memory_id) rather than raw data.
- Allow Athena to act only as a *user interface* querying the Mediation/Collective layers; Athena's own local store remains separate and untrusted by the collective logic.

## Architectural Decisions Requiring Experimentation
1. **Promotion Scoring** – Validate correlation of LLM score thresholds and multi‑source corroboration against real data.
2. **Privacy Scrubbing Algorithm** – Prototype filter to remove personally identifiable or sensitive content while retaining factual value.
3. **Vector Space Alignment** – Investigate embedding schema compatibility across profiles when visualizing Constellations.
4. **Sync Triggers** – Determine whether a push‑style event system (e.g., SQLite `trigger`) or polling is needed for profile contributions to the collective pool.

## Unresolved Questions
- What exact schema will the Collective DB use? (Reference table structure, validation history, provenance)
- How to handle **revocation** when a source profile deletes memory that has already been promoted.
- Should Athena’s review logic be its own process/service or run within the Mediation Plane?
- What metrics decide when a memory is *high‑value* and should be auto‑proposed versus manual request?

## File Operations
The file **docs/profile_reviews/athena_architecture_synthesis.md** has been created, reflecting the synthesis above. No changes were made to `README.md`.
