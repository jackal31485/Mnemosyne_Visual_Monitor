# Aggregator Visibility and Provenance Rules

## Overview
- **Source Profile**: the `source_profile` field in the contract retains the provenance of each collective entry.
- **Origin Memory ID**: unique identifier of the original memory.
- **Visibility**:
  - Only entries with `is_promoted == True` *and* `is_revoked == False` are returned via ``list_all_promoted``.
  - The DAO may contain many profiles; each profile is represented by its own `CollectiveDAO`.  Aggregation does **not** merge SQLite databases; it merely iterates over the list of DAOs.
- **Lifecycle State**: always set to “promoted” for entries returned from ``list_all_promoted``. Entries that are not promoted or that have been revoked are omitted entirely – no status strings such as "revoked" appear in the contract.

## Key Points for Developers
1. Do *not* expose any SQLite file paths or database identifiers to consumers.
2. Never include raw embedding blobs in `CollectiveContract`; they belong entirely inside DAO storage.
3. If you need a mapping from contract to its source profile, use the ``source_profile`` and ``origin_memory_id`` fields – no database references required.
