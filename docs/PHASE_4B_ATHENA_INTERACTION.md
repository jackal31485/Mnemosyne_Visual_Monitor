# Phase 4B – Athena Collective Knowledge Interaction (Design)

## Purpose
The goal of Phase 4B is to **design** how a trained Athena instance will query, reason, and incorporate validated collective knowledge while maintaining strict privacy boundaries. The design focuses on domain‑level abstractions—no GUI implementation.

---

## 1. Athena Query Model

* Athena can express **exact look‑ups**, **filtered searches**, and future **semantic embeddings** queries.
* Queries are expressed over *reference IDs* (`origin_memory_id`) rather than raw memory text.
* Query surface:
+
+```
+class AthenaQueryClient:
+    def get_references(self, *, profile: str | None = None)
+        -> List[CollectiveReference]
+
+    def search_by_text(self, query: str, limit: int = 10) -> List[CollectiveReference]
+        # Future semantic extensions will interpret `query`.
+
+    def get_provenance(self, ref_id: int) -> ProvenanceInfo
+```
+
* No direct mutation methods.
* Parameters are safe; only IDs and metadata exposed.

---

## 2. Context Construction & Sanitation

1. **CollectiveReference** is a lightweight record containing:
   * `id` – the collective entry id.
   * `source_profile` – whose profile originally proposed it.
   * `origin_memory_id` – reference to the source memory.
   * `provenance` – timestamps, validator, status flags.
2. **Sanitization Layer**:
   * An optional gateway that resolves an `origin_memory_id` to a *sanitized summary* (e.g., title, abstract) rather than full private text.
   * Must honor is‑revoked flags and only expose promoted references.
3. The context given to Athena always excludes any field values from the private Mnemosyne store.

---

## 3. Reference Semantics & Privacy Boundary

* Collective DB stores **only** `origin_memory_id` not raw content.
* Retrieval of full memory is *through an approved gateway* that checks: 
  * requester’s privilege level (Athena itself).
  * revocation status.
  * whether the referenced memory has been sanitized.
* The gateway must operate **in a separate security context** to avoid leakage. An isolated `memory_gateway` service can be introduced later; for Phase 4B it is an architectural requirement, not implementation.

---

## 4. Profile Isolation

* Each Hermes profile retains its own private Mnemosyne database. Athena only consumes shared **promoted** references and never writes back to any profile DB.
* Future phases may add *profile‑specific inference layers*, but Phase 4B keeps Athena as a pure consumer of the collective store.

---

## 5. Interaction API Skeleton (Domain Layer)

```python
# src/domain/athena_api.py – proposed skeleton
class AthenaAPI:
    def list_collected(self) -> List[int]: pass         # promoted / not revoked
    def get_entry(self, id: int) -> Tuple[int, ...]: pass  # legacy 9‑field tuple
    def resolve_memory(self, origin_id: str) -> Optional[SanitizedMemory]:
        """Return a sanitized summary; None if revoked or inaccessible."""
```

*No mutation methods are exposed in the API.

---

## 6. Lifecycle Interaction Explanation

Axiom: `PROPOSED → VALIDATED → PROMOTED → REVOKED` remains unchanged.

* The **AthenaAPI** operates only on the `PROMOTED` slice of the chain.
* Revoke operations are *outside* Athena’s responsibility.
* Proposed and validated entries are invisible to Athena due to visibility rules.

---

## 7. Privacy / Security Threat Model

1. **Reference Leak** – someone could reverse‑engineer a sanitized summary into private content. Mitigate by:
   * limiting the amount of contextual data returned in `sanitized_memory`;
   * tracking access logs for any resolve requests.
2. **Unauthorized Resolve** – ensure Athena can only call `resolve_memory()` via an authenticated gateway service.
3. **Replay Attacks** – versioning of sanitized summaries and timestamp checks prevent stale memory leaks.

---

## 8. Future UI Compatibility Mapping

* Designed API returns *structured* objects: references lists, provenance dicts.
* UI layers can transform these into constellation tables, timelines, or editable rows without depending on domain logic.
* No GUI‑specific code lives in the domain package.

---

## 9. Testing Strategy (Pre‑Implementation)

| Test Area | Goal |
|-----------|------|
| *Unit* – AthenaAPI construction | Ensure constructors accept dependency injection, no mutation side‑effects |
| *Integration* – Query flow | Call `list_collected()`, `get_entry()`, and `resolve_memory()` against a test DB; assert that revoked/promoted rules are enforced |
| *Security* – Access control | Verify that resolve requests for revoked or non‑promoted IDs return `None` |
| *Legacy* – DAO compatibility | Confirm `get_by_id()` still returns the original 9‑field tuple when accessed through AthenaAPI |

---

## 10. Phase 4B Implementation Boundaries

### Must be addressed in Phase 4B
- Domain‑level Athena API skeleton.
- Reference model and sanitization contract.
- Security boundary definition (gateway placeholder).

### Wait until Phase 5 (vector/embedding work)
- Semantic/semantic search extensions over references.
- Embedding generation for `origin_memory_id`.

### Wait until Phase 6 (cross‑profile learning)
- Incorporating Athena’s inferences back into individual profiles.
- Shared knowledge feedback loops.

### Wait until Phase 8 (GUI & live testing)
- Constellation/summary visualizations, timeline views.
- User edit/delete management interfaces.

---

> **Unresolved Architectural Decisions**:
> * Exact structure and content of the `SanitizedMemory` object.
> * Authentication model for the gateway service resolving private memory.
> * Whether Athena can *submit* new proposals (future Phase 5+).
>
> These will be decided after stakeholder review.

---

## Summary
Phase 4B lays out how Athena will **query** and **reason** over validated collective knowledge without ever touching private Mnemosyne content. The design keeps the domain layer GUI‑agnostic, introduces a clear reference model, and specifies necessary security boundaries for the future gateway service.
