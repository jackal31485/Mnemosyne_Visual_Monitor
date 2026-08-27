# Phase 6: Collective Ingestion Bridge

## Purpose
The bridge discovers real Hermes‑profile Mnemosyne databases and turns each raw memory into a *proposed* entry in the **collective** store.

All privacy, validation, and promotion logic remains untouched – the bridge only submits *references* to the existing `ProposalManager`/`CollectiveDAO` pipeline.

## Workflow Overview
```
Hermes Profile   ←  read‑only Mnemosyne DB (mnemosyne.db)
 |                     │
 |                     ▼
+---------------------+     +-------------------+
|  profile_ingest.py  | →   |  ProposalManager  |
+---------------------+     +-------------------+
        ▲                              │
        │                              ▼
      collection (collective.db)   state machine
```
* **Discovery** – iterate over `~/.hermes/profiles/*/mnemosyne/data/mnemosyne.db`.
* **Schema introspection** – pick the first table containing an ID‑like column and a string/text field. All other columns are ignored.
* **Row extraction** – read each row as a dictionary, keep only `(id, content)`.
* **Reference creation** – call `ProposalManager.propose(source_profile=…, origin_memory_id=…)`.
  * Existing entries are idempotently skipped via `CollectiveDAO.get_by_source()`.
* **Dry‑run support** – a command line flag reports how many memories would be ingested without touching the collective DB.

## CLI Usage
```bash
octopus@hermes:~$ python scripts/ingest_profiles.py --dry-run
{
  "default_profile": 128,
  "developer_profile": 64
}
```
Running it without `--dry-run` creates proposals in the collective database.

## Tests (outline)
* **Profile discovery** – fake profile directories and assert that only those with a valid DB are returned.
* **Schema inference** – create a minimal SQLite file with various table shapes; verify that the helper selects the correct one.
* **Row extraction** – confirm that records yield Python dictionaries mapping column names to values.
* **Duplicate handling** – ingest once, re‑run, and assert no additional entries are added.
* **Dry‑run reporting** – ensure counts match the number of rows in each synthetic DB.

All tests live under `tests/unit` and use temporary directories via `tmp_path` from `pytest`.
