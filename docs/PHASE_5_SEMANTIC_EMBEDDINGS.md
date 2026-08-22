# Phase 5 – Semantic Embeddings & Vector Search for the Collective

## Objective
Add deterministic embeddings to all **promoted** collective entries and expose a similarity‑search API that Athena can use to retrieve references with maximal semantic relevance, while keeping private Mnemosyne content completely isolated.

---

## Architectural Boundaries
| Element | Scope |
|---------|-------|
| `collective_entries` table | An optional *schema* alteration adding a **binary column** `embedding`. The column is defined **nullable**, defaulting to NULL for pre‑existing rows. No other columns change.
| Athena read‑only interface | Unmodified: `athena_collective_interface.py` continues to provide `list_promoted()`, `get_by_id()`, and `find_by_source()`.
| Privacy gateway & Mediation Plane | Remain unchanged; they only *provide* sanitized outputs and never expose raw memory.
| Vector search engine | Deemed a **separate helper** (Phase 5C) that uses the new column as input. The component may be an in‑process library or a lightweight micro‑service, but it must not alter the database structure beyond storing the vector.

No changes are made to code, tests, or the existing DB schema itself aside from adding the nullable `embedding` column.
---

## Privacy & Security Requirements
1. **Raw private content must never touch the embedding generator**. The only input allowed is an *approved sanitized representation* returned by the Mediation Plane / privacy boundary (a JSON object containing provenance fields, an abstract title/description, and optionally a hash of the original memory).
2. **Embeddings are deterministic but opaque** – they do not reveal underlying text or PII. They may leak high‑level semantics, so Athena is required to enforce *revocation* filtering: revoked entries must never appear in any query or search result.
3.  The embedding column is stored as a *read‑only binary blob*; no direct file or filesystem access is permitted via the Mediation Plane or Athena.
4. **No external API key or secret** is embedded in code – if an external model provider is used, it must be configured at runtime outside of the repository.
---

## Sanitized‑Content → Embedding Boundary
- The *only* data passed to the embedding pipeline is an **approved sanitized representation** produced by the Mediation Plane / privacy boundary. It contains provenance information and an abstract summary but no raw private memory text.
- The embedding generator consumes this representation and outputs a deterministic vector (or equivalent). No private fields beyond the sanitized `summary` are accepted.
---

## Required Components
| Phase | Component | Purpose |
|------|-----------|---------|
| **5A** | Schema migration script | Add a nullable `embedding BLOB` column to `collective_entries`. Ensure pre‑existing rows default to NULL. |
| **5B** | Deterministic embedding generator | Run locally (e.g., with a lightweight sentence‑transformer) or call an external service. Must be deterministic: identical sanitized input → same vector on every run. |
| **5C** | Athena similarity search helper | Lightweight NN lookup that scans the `embedding` column, filters out revoked/promoted checks, and returns nearest neighbors sorted by cosine similarity. Optionally use a simple ANN index for large datasets; this is a *deferred* enhancement. |
| **5D** | Validation & regression test harness | Unit tests to verify: <br>• vectors are stored when an entry is promoted.<br>• `search_by_embedding` returns only non‑revoked/promoted entries sorted correctly.<br>• revocation removes an item from search results.<br>• no raw memory content appears in any exported representation. |
---

## Dependencies
- An optional vector library (e.g., `sentence-transformers`, `faiss-cpu`, or a SQLite FTS5‑vector extension).<br>- A runtime environment capable of running the embedding model (CPU/GPU).
---

## Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| **Storage bloat** – each entry adds ~150 B for a 384‑dim float32 vector. *Mitigate:* monitor table size; consider compression or optional pruning.
| **Embedding cost** – every promotion triggers vector generation, potentially slowing the Mediation Plane. *Mitigate:* batch embeddings offline or cache results per profile.
| **Privacy leakage** – embeddings can reveal high‑level semantics. *Mitigate:* enforce strict revocation filtering and limit Athena’s API to no longer expose raw summaries directly.
| **Compatibility** – older entries without vectors will break naive search code. *Mitigation:* new search helper should handle NULLs gracefully, skipping such rows or raising a warning.
---

## Explicitly Deferred Functionality
* Full ANN index design (FAISS/SQLite).<br>* Integration with an external embedding provider and API key management.<br>* Fine‑grained policy for limiting Athena’s access to embeddings based on profile role.<br>* GUI components or user‑facing documentation showing similarity results – reserved for later phases.
---

## Acceptance Criteria
1. **Schema**: `collective_entries` contains a **nullable** `embedding BLOB` column after migration; existing data remains intact.
2. **Embedding generation**: when an entry is promoted, the system stores a deterministic vector derived only from sanitized output (no raw memory). Unit test confirms that re‑running the generator on the same input yields byte‑identical vectors.
3. **Search API**: `AthenaAPI.search_by_embedding(vector, top_n)` returns IDs of promoted and non‑revoked entries sorted by cosine similarity; tests verify ordering and revocation filtering.
4. **Privacy**: no test or log contains raw private memory text. The embedding generator never receives any field beyond the sanitized `summary` (or equivalent). The search helper never exposes the vector payload to external callers aside from the final ranking response.
5. **Regression tests**: all existing unit tests continue to pass; new Phase 5-specific tests are added and succeed.
6. **Documentation**: this file, along with code comments, fully describes phase architecture and responsibilities of components A‑D.
---

> **Summary** – Phase 5 is a *lightweight* extension that adds semantic search to Athena while keeping private Mnemosyne data safe. It comprises four well‑scoped parts: schema change (5A), deterministic embedding generation (5B), a minimal similarity helper (5C), and thorough testing (5D). All other concerns (ANN indexes, external APIs, UI) are deliberately deferred.
---
