# Documentation for Phase‑2a – Runtime & Data Layer

**What was implemented**
- A discovery package under ``src/discovery`` containing:
    * ``hermes_runtime.py`` – read‑only inspection of Hermes installation, profiles and runtime.
    * ``mnemosyne_inspector.py`` – safe SQLite schema introspection with optional vector support.
    * ``utils.py`` – lightweight helpers for reading text files.
- Minimal dataclasses modelling the discovered state.

**Package responsibilities**
- Keep the interface pure, no side‑effects.
- Expose a single function ``get_hermes_runtime_snapshot`` that returns the full Hermes snapshot.
- Expose ``inspect_sqlite_database`` for reading vector tables with ``enable_vectors=True``.

**Read‑only safety model**
- All filesystem paths are accessed in read mode only. No writes, no ``chmod`` or ``open(_, 'w')``.
- SQLite connections use URI ``?mode=ro`` and `uri=True`; the connection is closed immediately after reading.
- Extension loading via ``conn.enable_load_extension(True)`` is optional and isolated to callers that request vector support.

**SQLite/Vec0 handling**
- If the caller passes ``enable_vectors=True`` we attempt to load the ``sqlite_vec`` extension.  Failure raises a clear ``RuntimeError``; this allows the caller to treat “no vector support” as an error rather than swallowing it silently.
- After loading the extension we can safely query ``vec_*`` virtual tables.

**Data models**
- `HermesProfileInfo`: profile name, path, optional config, db location.
- `HermesRuntimeSnapshot`: executable info, Python, site-packages, profiles, current active profile name.
- `SchemaSnapshot`, `TableInfo`, `IndexInfo`, `ColumnInfo`, `VectorTableMeta` – immutable snapshots of DB metadata.

**Tests**
- Unit tests for each discovery helper using simple SQLite test files.
- Integration test that reads the real Athena Mnemosyne database in read‑only mode and verifies a handful of fields. The integration is skipped if the path does not exist.

**How to run**
```
# Run unit tests only
pytest -q tests/unit

# Run full test suite including integration (requires the local file)
pytest -q tests
```

**Running the original discovery script**
The new modules are independent; no change to ``scripts/discover_mnemosyne.py`` is required. Running it will still produce a diagnostic report.

**Known limitations**
- The code does not attempt to infer or load *any* non‑read‑only configuration – caller must provide the profile name if they wish to read a particular Mnemosyne DB.
- Vector support detection is limited to loading ``sqlite_vec``; it does not verify that the loaded extension actually exposes expected virtual tables. This is intentional to keep the module decoupled from higher‑level domain logic.

**Phase‑2b consumption**
Future monitoring will import `get_hermes_runtime_snapshot` for a baseline, and call `inspect_sqlite_database(..., enable_vectors=True)` on the current Mnemosyne DB when vector metrics are required.
