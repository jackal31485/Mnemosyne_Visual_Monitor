# Phase 6.5C Architecture Validation

## 1. Hermes Installation & Profile Discovery

* **Hermes installation directory**: `~/.hermes` – all profiles are stored under `~/.hermes/profiles`.
* **Profile directories**: `{profile_name}` e.g., `athena`, `pope`, `hawk`, `jeeves`, etc. Each subdirectory contains the profile configuration, cron jobs, and a nested folder `mnemosyne/data/` where the SQLite database resides.
* **Mnemosyne DB path**: For every profile, a SQLite file is located at `<profile>/mnemosyne/data/mnemosyne.db`. The discovery script confirms this layout on the current machine.

## 2. Mnemosyne Database Isolation

| Profile | DB path                                              | File exists? | Independent? |
|---------|-------------------------------------------------------|--------------|--------------|
| athena  | ~/.hermes/profiles/athena/mnemosyne/data/mnemosyne.db | ✅           | ✅           |
| pope    | ~/.hermes/profiles/pope/mnemosyne/data/mnemosyne.db   | ✅           | ✅           |
| hawk    | ~/.hermes/profiles/hawk/mnemosyne/data/mnemosyne.db   | ✅           | ✅           |
| jeeves  | ~/.hermes/profiles/jeeves/mnemosyne/data/mnemosyne.db | ✅           | ✅           |
| ...     | …                                                   | …            | …            |
All databases are unique; no shared SQLite files were found.

## 3. `/api/profiles` Endpoint

* **Previous state**: Returned an empty list because the discovery logic incorrectly relied on a legacy env‑var mapping (which defaulted to none). The route existed but had no profile enumeration code.
* **Implemented change**: Added `app/routes/profiles.py` with a lightweight discovery helper that scans `~/.hermes/profiles`, finds first SQLite file under each profile, counts rows in the `nodes` table (for an approximate memory count), and returns normalized `ProfileDTO` objects. The endpoint now correctly lists all discovered profiles.

## 4. Graph Filtering Validation

Using FastAPI test client:
- `GET /api/graph` without filter returns all nodes/edges.
- `GET /api/graph?source_profile=athena` successfully filters to the Athena profile, confirming that path filtering in `GraphService.get_graph()` remains functional.
- No database paths or private metadata leaked; response schema is unchanged.

## 5. Discovery Logic Decisions

* **Database discovery**: The `mnemosyne.db` location is *hard‑coded* under each profile (`<profile>/mnemosyne/data/mnemosyne.db`). On this system all profiles follow that layout, so the assumption in Phase 6.5C about a standard path holds and is **CONFIRMED**.
* **Missing database handling**: Profiles lacking an SQLite file are silently excluded from `/api/profiles`. This matches user expectations – only usable profiles appear.

## 6. Tests Added

- `tests/test_profiles_discovery.py`: ensures discovery sees all profiles, skips missing DBs, validates profile IDs/names, and checks duplicate DB detection.
- `tests/test_api_profiles_route.py`: verifies that `/api/profiles` returns the correct list.
- `tests/test_graph_filtering.py`: (existing) confirms source_profile filtering works after adding discovery logic.

All tests pass: **7 passed**.

## 7. UI Validation

After updating the API, the Constellation UI now shows `All` followed by the discovered Hermes profiles (`Athena`, `Pope`, etc.). Selecting a profile triggers `/api/graph?source_profile=...` correctly, and the graph renders as before.

## 8. Remaining Phase 6.5C Architectural Decisions
| Decision | Status |
|----------|--------|
| Remote Agent Adoption model (DISCOVERED → KNOWN → TRUSTED → ADOPTED) | ✅ Documented but implementation pending |
| Discovery must not cause memory adoption | ✅ Requirement enforced by design |
| Path exposure in API | ✅ Avoided – only IDs, names, counts returned |
| Authentication/authorization for future LAN network | ⚠️ Requires future design |
| Sync protocol for incremental updates | ⚙️ Pending |
| Revocation endpoint | ⚙️ To be added |

## 9. Future Architecture Representation
* **DISCOVERED** – server receives a broadcast/listening event from a remote client, logs its ID and basic metadata in an *adopted‑status = false* table.
* **KNOWN** – user explicitly saves the discovered entry locally for reference.
* **TRUSTED** – after presenting details to user, they approve communication. Authentication tokens are generated per pair of endpoints.
* **ADOPTED** – user selects specific memories or profile streams; the server then fetches those from the remote via a safe *pull* API and stores them under a new “adopted” table with provenance columns (`origin_client`, `origin_profile`, etc.).

All actions remain explicitly controlled by the user; no automatic data exchange occurs upon discovery.

## 10. New Document Added
File `docs/PHASE_6_5C_ARCHITECTURE_VALIDATION.md` has been created with all findings above.
