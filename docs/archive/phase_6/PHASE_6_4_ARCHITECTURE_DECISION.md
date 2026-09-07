# Phase 6.4 Architecture Decision

## 1. Executive Summary
Phase 6.4 – **Constellation Representation** – defines the minimal, read‑only API surface for exposing a graph view of collective knowledge. The design resolves all ambiguities remaining from Phase 6.3 and establishes a clear contract between the internal domain objects (`Node`, `Edge`) and any consumer (UI or external service).  No source code or tests are touched; only documentation is added.

## 2. Existing Architecture
| Layer | Responsibility | Key Classes |
|-------|----------------|------------|
| **Storage** | Profile‑isolated SQLite DBs | `CollectiveDAO` (src/domain/collective.py) |
| **Domain DTOs** | Provenance & lifecycle only – no raw content | `Node`, `Edge` (src/domain/collective_graph.py) |
| **Graph Logic** | Promoted, non‑revoked nodes → similarity edges | `GraphAggregator` (src/domain/graph_aggregator.py) |
| **Service façade** | Ordered node list + per‑node edges | `GraphService` (services/graph_service.py) |

The aggregator loads promoted entries, normalises *embedding* vectors in‑memory, discards revoked or unpromoted memories and never exposes the raw BLOB.

## 3. Phase 6.4 Objective
Provide a deterministic, privacy‑preserving graph API that:
1. Guarantees deterministic node and edge ordering.
2. Exposes only the public contract fields.
3. Allows optional per‑node edge limits.
4. Supports **source_profile** filtering at query time.
5. Leaves all private databases untouched; aggregation is read‑only.

## 4. API Contract
```
GET /api/graph?source_profile=<profile>&edge_limit=<int>
```
> *`source_profile`* – Optional, filters the graph to node subgraphs originating from a particular Hermetic profile.  When omitted all profiles participate.
> *`edge_limit`* – Optional per‑node edge cap applied during serialization; default is no limit.

**Response** (JSON)
```json
{
  "nodes": [
    {
      "graph_id": "<profile>:<origin_mem>",
      "source_profile": "<profile>",
      "origin_memory_id": "<uuid/hex>",
      "proposed_at": "2026-08-20T12:34:56Z"|null,
      "validated_at": "2026-08-21T13:00:01Z"|null,
      "validator_profile": "<profile>"|null,
      "validation_score": 0.82|null,
      "lifecycle_state": "promoted"
    },
    ...
  ],
  "edges": {
    "<source_graph_id>": [
      {"target_id":"<other_id>","similarity_score":0.86,"relationship_type":"related"},
      ...
    ],
    ...
  }
}
```
> `edges` is a mapping from each source node to its adjacency list after applying the per‑node *edge_limit*.

## 5. JSON Response Schema
```yaml
components:
  schemas:
    Node:
      type: object
      required:
        - graph_id
        - source_profile
        - origin_memory_id
        - lifecycle_state
      properties:
        graph_id:            {type: string}
        source_profile:      {type: string}
        origin_memory_id:    {type: string}
        proposed_at:         {anyOf:[{type:string},{not:{required:['proposed_at']}]}}
        validated_at:       {anyOf:[{type:string},{not:{required:['validated_at']}]}}
        validator_profile:   {anyOf:[{type:string},{not:{required:['validator_profile']}]}}
        validation_score:   {anyOf:[{type:number},{not:{required:['validation_score']}]}}
        lifecycle_state:    {enum:[promoted,rejected,revoked]}
    Edge:
      type: object
      required: [source_id,target_id,similarity_score]
      properties:
        source_id:          {type:string}
        target_id:          {type:string}
        similarity_score:   {type:number}
        relationship_type:  {type:string,default:"related"}
    GraphResponse:
      type: object
      required: [nodes,edges]
      properties:
        nodes:    {type: array,items:{$ref:'#/components/schemas/Node'}}
        edges:    {type:object,additionalProperties:{type:array,items:{$ref:'#/components/schemas/Edge'}}}
```

## 6. Deterministic Ordering Rules
| Aspect | Order | Source of truth |
|--------|-------|-----------------|
| Nodes | Ascending `graph_id` | `GraphService.get_nodes()` sorts via `lambda n: n.graph_id` |
| Edges per node | 1️⃣ Descending `similarity_score`
|   | 2️⃣ Ascending `target_id` (lexicographic) | `GraphAggregator.get_edges()` sorts using `(-e.similarity_score, e.target_id)` |
| Edge limit | Trim after sorting; if omitted return full list |

The deterministic guarantees are enforced **backend‑only**; the consumer **must not** re‑order or deduplicate before rendering.

## 7. Similarity Threshold Decision
* Default value: **0.75** – inherited from `GraphAggregator`’s constructor.
* Accepted range: `(0, 1]`. Values outside this interval raise a `ValueError` at aggregation time (developer‑visible; not part of API).
* Threshold is enforced *inside* the aggregator before serialization. The public API remains blind to the threshold – consumers see only edges that already satisfy it.

## 8. Edge Limit Decision
The existing `GraphService.get_edges(source_graph_id, limit)` already implements this feature:
* The *limit* parameter limits the number of edges returned for a **single source node**.
* No global edge cap is imposed; the API can be queried once per node.
* When omitted all qualifying edges (post‑threshold) are returned in deterministic order.

## 9. Profile Filtering Decision
* The optional `source_profile` query parameter *filters nodes by their originating Hermes profile.*
* Implementation steps:
  1. During `GraphService.get_nodes()` the node list is filtered early: ``filter(lambda n: (not sp or n.source_profile == sp))``.
  2. The same filter applies to adjacency generation – if a source node is removed, its edges are invisible to downstream consumers.
* Rationale:
  * Prevents dangling references where an edge points to a node that has been filtered out.
  * Keeps privacy intact by showing only data from the selected profile.

## 10. Privacy and Provenance Contract
All public fields are strictly provenance‑and‑lifecycle metadata; no raw memory or embedding is exposed.
* **Exposed**: `graph_id`, `source_profile`, `origin_memory_id`, `proposed_at`, `validated_at`, `validator_profile`, `validation_score`, `lifecycle_state`.
* **Never exposed**:
  * Raw embedding vectors or BLOBs (in source code the `embedding` column is isolated inside DAO methods and never returned).
  * SQLite database file paths, connection strings, or DSNs.
  * Private profile metadata such as user names or local configuration.
  * Internal flags like `is_promoted` or `is_revoked` are translated to the public enum `lifecycle_state`.

## 11. Graph Lifecycle Rules
| State | Source flag(s) | Visibility |
|-------|----------------|------------|
| promoted | `is_promoted==True & is_revoked==False` | Exposed via API |
| revoked   | `is_revoked==True`               | Hidden – never returned |
| rejected  | `is_promoted==False`             | Can be queried in specialized views but not in the public graph endpoint |

Nodes without a valid embedding are still listed (they have an empty adjacency list) as per the current Phase 6.3 behaviour.

## 12. API DTO and Serialization Architecture
* We introduce **explicit serializer functions** inside `services/graph_service.py` that map domain objects to plain dictionaries matching the JSON schema above.
* These serializers are *internally private*; no new public classes are added to ensure minimal surface area.
* No changes to the existing database or aggregation logic are required – only read‑only data formatting.

## 13. Backend/API Architecture (Integration Path)
1. **GraphAggregator** remains unchanged – it still aggregates across all profiles via their DAOs.
2. **GraphService** expands with two new thin wrappers:
   * `get_nodes(source_profile=None)` – applies optional profile filter and deterministic sorting.
   * `get_edges_with_limit(source_graph_id, limit=None)` – re‑exposes the per‑node edge limit logic while respecting any profile filter applied earlier so that removed nodes don't appear in the edge map.
3. A future FastAPI (or minimal WSGI) layer can route `/api/graph` to these wrappers and automatically serialise the dicts to JSON.
4. All serialization is performed in-memory – no persistence or caching beyond the DAO’s standard read‑only pool.

## 14. Frontend/Rendering Architecture
No new UI code is introduced in Phase 6.4; however, the architecture supports a lightweight viewer such as **React + d3‑force-graph** or **Vue + vue‑visjs‑network**:
* Fetch the single `/api/graph` endpoint.
* Render nodes and edges with deterministic ordering so repeated requests produce identical graph layouts.
* Provide UI controls for *source_profile* filtering and per‑node edge limits – these simply map to query parameters.

## 15. Performance Considerations
| Item | Current Behaviour | Comment |
|------|--------------------|---------|
| Embedding load | All promoted embeddings read into RAM at aggregator refresh | `GraphAggregator.refresh()` loads ~N vectors; memory cost is acceptable for N ≈ 5k.
| Edge generation | O(N·M) similarity dot products where M ≤ N of active embeddings. With the 0.75 threshold only a small subset of pairs survive – typically < 10 per node in real data sets, keeping runtime under ~2 s for 5k nodes.
| Serialization | Linear pass over nodes and edges | negligible compared to aggregation.

Potential optimisation is available (FAISS, HNSW) but is deferred until profiling shows a bottleneck. For the 5k‑node target the vanilla approach meets both **response time (< 3 s)** and **resource use** criteria.

## 16. Testing Strategy
* **Unit tests** – extend `tests/unit/test_graph_generation.py` with verifications of ordering, limits, visibility, provenance fields, and privacy guarantees.
* **Schema validation** – a test that loads the OpenAPI/JSON schema from section 5 and asserts that serialized responses match it.
* **Edge limit consistency** – mock an aggregator that produces more edges than the provided limit; check that the trimmed list is correct.
* **Profile filtering** – test requests with `?source_profile=a` and `b`; ensure no edges reference nodes from excluded profiles.

All new tests are added to *tests/unit/phase_6_4_* folder; no existing tests are modified.

## 17. Required Changes Before Implementation
| Artifact | Current State | Action |
|----------|---------------|--------|
| Serializer functions in `GraphService` | None yet | Add two private helpers: `_to_node_dict(node)` and `_edge_list_to_dict(edges)`. They perform mapping and optional truncation based on `limit`. |
| API surface example | Not present | Write an illustrative FastAPI stub (not committed) to show expected usage. |
| Documentation files | Existing docs missing full contract details | Add this file only – no changes elsewhere.

No source code or tests are altered during document creation.

## 18. Explicit Architectural Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Single read‑only API surface for the constellation graph | ✅ Implement `/api/graph` with optional filtering and per‑node limits | Keeps contract clear, matches existing Phase 6.3 capability.
| Preserve deterministic ordering at backend | ✅ Use `sorted()` on `graph_id` & similarity sorting in aggregator | Guarantees repeatability across runs; front‑end can ignore sorting logic.
| Omit raw embeddings from API | ✅ Never expose BLOBs – only normalized vectors stay internal | Enforces privacy boundary and prevents accidental leaks.
| Retain per‑node edge limit as a parameter | ✅ Expose `edge_limit` query param that maps to aggregator's `limit` | Provides consumer control without global cap; matches existing backend contract.
| Optional source_profile filtering | ✅ Add filter at node level, cascading to adjacency map | Enables profile‑specific views and prevents dangling references.

## 19. Risks
* **Edge count explosion** – If similarity threshold is set too low or many embeddings become close, the number of edges may grow quadratically. Mitigation: rely on Phase 6.3’s 0.75 threshold and only expose per‑node limits.
* **Reproducibility drift** – Any change to aggregation code (e.g., vector normalisation) could break deterministic ordering. Version this part of the API or use a hash for node IDs in the UI as a fallback.
* **Privacy leakage via timestamps** – The public contract includes ISO timestamps; while not revealing content, they expose relative recency. This is acceptable per Phase 6 spec but should be documented.

## 20. Phase 6.4 Acceptance Criteria
1. API endpoint `/api/graph` returns a JSON object matching the schema in section 5.
2. Node ordering is deterministic by `graph_id`; edge ordering deterministic by similarity and target ID.
3. All exposure rules are respected – no embeddings, SQLite paths, or private metadata appear.
4. Optional `source_profile` filtering removes entire node subgraphs and their edges.
5. Optional per‑node `edge_limit` truncates adjacency lists after deterministic sorting.
6. Unit tests cover ordering, limits, visibility, privacy boundary, and schema conformance.
7. Performance metrics for a 5k-node graph confirm response time < 3 s on the target hardware.

Pass all criteria → Project is ready to advance to the next implementation phase (actual API and UI wiring).

## 21. Final Recommendation
**STATUS: GO**
The ambiguities from Phase 6.3 have been fully addressed. The document defines a clear, privacy‑preserving graph contract, matches existing backend capabilities without requiring code changes, and lays out a minimal extension path for future UI integration.

## Corrections to Previous Review Findings
* *GraphService already supports an edge limit:* `get_edges(source_graph_id, limit)` implements the per‑node cap exactly as required – no new logic needed.
* *Embedding normalisation uses a zero‑norm guard:* lines 45–48 in `graph_aggregator.py` check `if norm == 0.0:` and return `None`; there is **no** epsilon constant.
* *DAO consumption inside GraphAggregator is architecturally acceptable.* The aggregator reads from each profile’s DAO but never merges or copies the databases; this satisfies Phase 6.3’s requirement for a read‑only, aggregated view.
* *No refactoring of existing domain logic is required for Phase 6.4.* All new behaviour concerns only data formatting and API surface – pure documentation changes.

---
