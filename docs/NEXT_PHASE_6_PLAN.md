# Next Phase 6 Plan

## Phase 6.4A
Status: COMPLETE

Commit:
b8acafc

Commit message:
"Implement Phase 6.4A constellation graph serialization"

Forgejo:
Successfully pushed to origin/master.

## Next planned phase

Phase 6.5 – UI/API integration for the constellation viewer.

* The next stage is not started yet.
* Intended approach: expose `GraphService.get_graph()` through a read‑only API endpoint (`/api/graph`).
* Preserve all existing features:
  - optional `source_profile` filtering
  - per‑node `edge_limit`
  - deterministic ordering (nodes by graph_id, edges by similarity then target ID)
  - strict privacy boundary.
* Begin the constellation viewer/API integration only after the Phase 6.4A implementation has been accepted.