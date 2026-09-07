# Phase 4 – Athena Interface / Collective Memory Interaction

## Phase 4A Status
*Design and implementation are complete.
*Phase 4A provides a **read‑only Athena collective interface**.

**Phase 4A – Design / Read-Only Collective Interface**

## Objective

Provide Athena with a controlled, read-only interface to the validated collective knowledge base while preserving strict isolation between each Hermes profile's private Mnemosyne memory and the collective store.

The read‑only interface exposes *only promoted, non‑revoked* collective entries together with their source profile and origin memory identifiers.
No raw private Mnemosyne memory content is exposed or copied.

## Read‑Only Interface API
+
+```python
+class AthenaCollectiveInterface:
+    def list_promoted(self):  # -> List[int]
+        """Return IDs of all promoted, non‑revoked entries."""
+
+    def get_by_id(self, entry_id: int):
+        """Retrieve the full 9‑field tuple for ``entry_id``.
+        Fields:
+          0 id
+          1 source_profile
+          2 origin_memory_id
+          3 proposed_at
+          4 validated_at
+          5 validation_score
+          6 validator_profile
+          7 is_revoked
+          8 revocation_reason
+        """
+
+    def find_by_source(self, src: str, orig_mem: str):
+        """Return the first matching entry for source profile and origin memory id.
+        Returns ``None`` if no match is found."""
+```
*** End Patch