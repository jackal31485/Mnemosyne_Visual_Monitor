# Mnemosyne Visual Monitor — Project Roadmap

**Roadmap revision:** 2026-08-29  
**Current direction:** Browser-first development with Hindsight-inspired retrieval/knowledge improvements  
**Architectural principle:** Preserve Mnemosyne's local-first SQLite architecture, Hermes profile isolation, provenance, mediation/air-lock, collective governance, promotion, and revocation model.

---

## Current Position

Mnemosyne has progressed from a memory-monitoring prototype into a governed, profile-aware collective memory platform.

### Completed / Established

- Phase 1 — Foundations / Discovery — **COMPLETE**
- Phase 2 — Mediation Plane / Air-Lock — **COMPLETE**
- Phase 3 — Collective Knowledge Base — **COMPLETE**
- Phase 4 — Athena Interface / Collective Memory Interaction — **COMPLETE**
- Phase 5 — Semantic Embeddings & Vector Search — **COMPLETE**
- Phase 6 — Collective Visualization data/model foundations — **COMPLETE**
- Phase 6.5A — Read-only graph API foundation — **COMPLETE**
- Phase 6.5B — Graph/constellation UI foundation — **COMPLETE**
- Phase 6.5C — LAN multicast discovery foundation — **COMPLETE**
- Current work — rebuild/recovery architecture and implementation — **IN PROGRESS**

### Important scope decisions

- Local Ubuntu development remains the active scope.
- Unraid/Docker/remote deployment remain out of current implementation scope unless explicitly reopened.
- Profile memory remains isolated.
- Collective knowledge remains governed and provenance-aware.
- Remote discovery does not imply trust or adoption.
- Remote adoption remains explicit and permission-controlled.
- Synchronization remains deferred until its own phase is authorized.
- The constellation is not being rebuilt as a standalone UI; it becomes one visualization inside the broader Browser.

---

# Phase 6.5C — Distributed / Remote-Agent Foundation

**Status: FOUNDATION COMPLETE / EXTENDED IMPLEMENTATION DEFERRED**

### Complete

- UDP multicast discovery
- Discovery registry
- Client identity/hostname/version metadata
- Staleness tracking
- Profile-aware remote-agent architecture
- Provenance model
- Trust/adoption boundary
- Explicit adoption semantics
- Separate trust revocation and adoption revocation

### Deferred

- Full remote synchronization
- Automatic remote memory ingestion
- Continuous change feeds
- Remote write operations
- Full client/server deployment model
- mTLS
- Cross-machine replication

### Invariant

Discovered or trusted remote agents must not automatically become part of the local memory/constellation graph. Only explicitly adopted data can participate in the governed local/collective knowledge system.

---

# Current Engineering Track — Rebuild / Recovery

**Status: IN PROGRESS**

The rebuild work should establish reliable reconstruction of Mnemosyne state from authoritative sources.

### Goals

- Profile memory contract
- Agent rebuild contract
- Collective rebuild
- Distributed rebuild
- Discovered-agent integration
- Deterministic rebuild behavior
- Idempotent rebuild operations
- Provenance preservation
- Revocation preservation
- Safe handling of partial failures
- Rebuild verification and diagnostics

### Browser integration requirement

Rebuild must eventually become a first-class Browser operation with:

- progress
- stage/status
- affected profiles
- affected memory/knowledge counts
- errors
- cancellation where safe
- completion summary
- audit trail

---

# Phase 7 — Mnemosyne Browser

**Priority: NEXT MAJOR PHASE**

The Browser becomes the primary human interface to Mnemosyne.

The Browser is intentionally a three-pane application:

```text
┌──────────────────┬──────────────────────────────┬──────────────────┐
│                  │                              │                  │
│  CONTROL CENTER  │      VISUAL WORKSPACE        │    INSPECTOR     │
│                  │                              │                  │
│  Profiles        │  Constellation              │  Selected object │
│  Memories        │  Graph                      │                  │
│  Entities        │  Timeline                   │  Memory          │
│  Collective      │  Table                      │  Entity          │
│  Evidence        │  Statistics                 │  Profile         │
│                  │  Collective                  │  Relationship    │
│  NUKS             │                              │  Event           │
│  Discovery       │  [ TABS ] [ TILES ]          │  Collective      │
│  Embeddings      │                              │                  │
│  Rebuild         │                              │  [ EDIT ]        │
│  Maintenance     │                              │                  │
│  Diagnostics     │                              │                  │
│                  │                              │                  │
└──────────────────┴──────────────────────────────┴──────────────────┘
```

## 7A — Browser Shell

- Three-pane layout
- Persistent left Control Center
- Center Visual Workspace
- Right Universal Inspector
- Responsive layout
- Collapsible left pane
- Collapsible right pane
- Full-screen visualization mode
- Global search
- Application/system status

## 7B — Control Center

All operational controls live on the left.

### Profile controls

- Athena
- Horus
- Odin
- Thoth
- Vulcan
- Other discovered/available profiles
- Profile health
- Memory counts
- Profile selection/filtering

### Knowledge controls

- Memories
- Entities
- Collective
- Evidence
- Proposals
- Promotion/rejection/revocation state

### Visualization controls

- Constellation
- Graph
- Timeline
- Table
- Statistics
- Relationship views

### System controls

- NUKS
- Discovery
- Embeddings
- Rebuild
- Maintenance
- Diagnostics
- Operations

## 7C — Center Visual Workspace

The center is dedicated to visual exploration.

### Visualizations

- Constellation
- Semantic graph
- Entity graph
- Relationship graph
- Timeline
- Memory table
- Collective view
- Statistics/metrics
- Future knowledge-model views

### Tab mode

One visualization occupies the center.

Useful for detailed exploration.

### Tile mode

Multiple visualizations can be displayed simultaneously.

Initial targets:

- 2-tile layout
- 4-tile layout
- 6-tile layout

Future:

- draggable/resizable tiles
- saved workspace layouts
- per-tile filters

## 7D — Universal Inspector

The right side always follows the selected object.

Supported selection types:

- Memory
- Entity
- Profile
- Relationship
- Timeline event
- Collective entry
- Proposal
- Observation
- Knowledge Model
- Operation

### Memory inspector

- Memory ID
- Content
- Profile
- Created/updated timestamps
- Memory type
- Entities
- Relationships
- Embedding status
- Provenance
- Collective status
- Promotion history
- Revision history
- Revocation state
- Related memories
- Edit controls where permitted

### Selection continuity

Selecting an object in any center visualization updates the right inspector.

Navigation must preserve selection context when switching views.

Example:

```text
Constellation
  -> select entity
  -> inspect entity
  -> select related memory
  -> inspect memory
  -> open Timeline
  -> same memory remains selected
```

## 7E — Memory / Table View

- Search
- Filtering
- Sorting
- Pagination
- Profile filtering
- Collective/private filtering
- Lifecycle filtering
- Date filtering
- Entity filtering
- Selection
- Multi-selection
- Right-panel inspection
- Edit workflow
- Provenance display

## 7F — Timeline View

- Chronological memory/event visualization
- Date-range filtering
- Temporal grouping
- Event selection
- Memory-to-event navigation
- Related-memory navigation
- Temporal relationships
- Right-panel inspection

## 7G — Collective Browser

Expose governance directly through the Browser.

- Proposed
- Validated
- Promoted
- Rejected
- Revoked
- Revised
- Superseded
- Evidence
- Provenance
- Promotion chain
- Revocation chain

## 7H — Operations / Diagnostics

Inspired by Hindsight's operational Control Plane.

- Rebuild operations
- Embedding generation
- Graph rebuild
- Collective aggregation
- Discovery
- Ingestion
- Errors
- Warnings
- Progress
- Completion state
- Operation history
- Safe cancellation where supported

Long-running operations should be observable rather than opaque.

---

# Phase 8 — Hybrid Retrieval

**Priority: HIGH**

Move beyond embedding-only retrieval.

Hindsight's current retrieval combines semantic, keyword/BM25, graph, and temporal strategies, followed by fusion and optional reranking. Mnemosyne should adopt this concept while keeping SQLite/local-first architecture.

## 8A — Keyword Retrieval

- SQLite FTS5
- BM25 ranking
- Exact phrase matching
- Identifier/name matching
- Technical-term matching

## 8B — Semantic Retrieval

- Existing embeddings
- Similarity thresholds
- Profile/collective scope filtering
- Embedding health diagnostics

## 8C — Graph Retrieval

- Entity relationships
- Memory relationships
- Collective relationships
- Profile relationships

## 8D — Temporal Retrieval

- Time-window filtering
- Recency weighting
- Temporal relationships
- Event proximity

## 8E — Rank Fusion

Combine:

```text
Semantic
   +
BM25
   +
Graph
   +
Temporal
   ↓
Rank Fusion
   ↓
Final results
```

Use Reciprocal Rank Fusion or an equivalent deterministic fusion strategy.

## 8F — Optional Reranking

- Local cross-encoder/reranker
- Configurable
- Never required for basic local operation
- Preserve explainability of why an item ranked highly

## 8G — Retrieval Explainability

The Browser should eventually show:

```text
Result surfaced because:

Semantic       0.91
BM25           0.84
Graph          +2 links
Temporal       +0.12
Reranker       0.93
```

---

# Phase 9 — Entity & Relationship Intelligence

**Priority: HIGH**

Hindsight's entity-centric graph is a strong inspiration.

## 9A — Entity Resolution

- Canonical entities
- Aliases
- Entity types
- Confidence
- Profile associations
- Provenance
- Candidate merges
- Merge history

## 9B — Entity Co-occurrence

Track entities that repeatedly occur together.

Browser visualization:

```text
Athena ───── Mnemosyne
   │              │
 SQLite ─────── Hermes
   │              │
   └── embeddings ┘
```

## 9C — Relationship Types

Expand beyond similarity:

- Semantic
- Entity
- Temporal
- Causal
- Supports
- Contradicts
- Revises
- Supersedes
- Evidence-for
- Profile-originated
- Collective

## 9D — Relationship Evidence

Every meaningful relationship should be traceable to supporting memories where practical.

---

# Phase 10 — Evidence-Backed Observations

**Priority: HIGH**

Inspired by Hindsight's evidence-grounded observations, but adapted to Mnemosyne's governance model.

An observation is a consolidated statement supported by multiple source memories.

Example:

```text
Observation
"SQLite remains the authoritative Mnemosyne store."

Confidence: 0.94

Evidence:
  Athena / memory A
  Horus  / memory B
  Odin   / memory C
  Thoth  / memory D

Governance:
  Promoted
```

## Requirements

- Evidence links
- Supporting-memory references
- Confidence/proof count
- Contradicting evidence
- Refinement rather than silent overwrite
- Observation history
- Provenance
- Revocation awareness
- Profile isolation

## Critical Mnemosyne enhancement

If supporting evidence is revoked or becomes unavailable:

- observation confidence may change
- evidence count changes
- observation can become review-required
- audit history remains intact

Underlying source memories are never silently destroyed to create an observation.

---

# Phase 11 — Collective / Knowledge Models

**Priority: MEDIUM-HIGH**

Inspired by Hindsight Mental Models.

Mnemosyne should use a governance-compatible concept such as **Knowledge Models** or **Collective Models**.

A model is a curated/consolidated high-level understanding of a topic.

Example:

```text
Mnemosyne Architecture

Current understanding:

- SQLite is authoritative
- profiles remain isolated
- collective promotion is governed
- revoked memories are excluded
- embeddings are optional
- LAN discovery is metadata-oriented

Evidence:
17 memories
5 profiles
3 observations
```

## Requirements

- Explicit provenance
- Supporting observations
- Supporting memories
- Version history
- Refresh strategy
- Staleness detection
- Manual approval/curation
- Optional automatic refresh
- Revocation-aware refresh
- Browser inspection

---

# Phase 12 — Consolidation & Deduplication

**Priority: MEDIUM**

Inspired by Hindsight's newer deterministic observation deduplication.

## Goals

- Detect near-duplicate observations
- Candidate merge detection
- Similarity thresholds
- Evidence-preserving consolidation
- No destructive source-memory deletion
- Merge history
- Audit trail

Potential flow:

```text
Observation A
      +
Observation B
      ↓
Similarity check
      ↓
Candidate consolidation
      ↓
Evidence validation
      ↓
Governed merge
      ↓
Consolidated observation
```

---

# Phase 13 — Explainability / Provenance Browser

**Priority: HIGH**

This is a signature Mnemosyne capability.

Every important object should answer:

> Where did this come from?

The Browser should provide a navigable chain:

```text
Knowledge Model
      ↓
Observation
      ↓
Evidence
      ↓
Source Memory
      ↓
Hermes Profile
      ↓
Original Provenance
```

## Features

- "Why does Mnemosyne believe this?"
- Evidence viewer
- Provenance chain
- Promotion history
- Revision history
- Revocation history
- Contradiction viewer
- Source profile navigation
- Original-memory navigation

---

# Phase 14 — Distributed / Remote Memory

**Priority: DEFERRED**

Only begin after the local Browser/retrieval architecture is stable.

Potential future work:

- Remote-agent authentication
- Explicit adoption
- Incremental synchronization
- Offline queues
- Reconnect/replay
- Conflict handling
- Remote revocation propagation
- Cross-instance rebuild
- Provenance-preserving migration

No automatic trust-to-adoption transition.

No remote raw-memory access outside approved boundaries.

---

# Phase 15 — Advanced Browser / Workspace

**Priority: FUTURE**

- Saved workspaces
- Saved filters
- Custom tile layouts
- Drag/resizable visualization tiles
- Multiple synchronized visualizations
- Deep links
- Browser URL state
- Keyboard navigation
- Advanced search builder
- Query history
- Retrieval explanation panel
- Knowledge-model dashboards
- Custom graph relationship filters

---

# Phase 16 — Collective-to-Profile Learning

**Priority: FINAL / CAPSTONE**

The collective database becomes a governed source of learning for individual Hermes profiles. Collective knowledge may improve profile-specific memories, but it must never silently overwrite or bypass profile isolation and governance.

## 16A — Learning Candidate Generation

Identify collective knowledge useful to individual profiles: promoted entries, high-confidence observations, validated entities, established relationships, Knowledge Models, corrections, superseded knowledge, and repeatedly confirmed facts. Not all collective knowledge propagates to every profile.

## 16B — Profile-Specific Relevance

Determine which knowledge is relevant to each target profile. The same collective knowledge may be useful to one profile and irrelevant to another.

## 16C — Governed Learning Proposals

Before changing a profile's memory, create a proposal containing target profile, collective source, supporting evidence, confidence, relevance, proposed transformation, and governance state.

## 16D — Profile Memory Updates

Approved proposals create or update profile-specific memories while preserving provenance and distinguishing learned knowledge from original experience.

## 16E — Conflict Detection and Resolution

Detect conflicts between existing profile memories and collective knowledge. Possible outcomes: update, supersede, preserve both with context, reject for that profile, or mark for review. Existing memories must not be silently destroyed.

## 16F — Learning Provenance

Every learned memory retains a derivation chain: Profile Memory → Learning Proposal → Collective Observation/Knowledge → Supporting Evidence → Source Memories → Source Profiles → Original Provenance.

The Browser should answer: **Why does this profile know this?**

## 16G — Revocation and Learning Reversal

When collective knowledge is revoked, identify derived profile memories, mark potentially stale knowledge, preserve history, and generate reversal/review proposals where appropriate. Never silently erase the historical record.

## 16H — Continuous Feedback Loop

```text
Observe → Profile Memory → Mediation / Air-Lock → Collective Knowledge
       → Governed Learning → Improved Profile Memory → New Experience → Observe
```

## 16I — Learning Effectiveness

Track accepted/rejected learning proposals, conflicts, later corrections, revoked-derived memories, repeated rediscovery avoided, retrieval quality before/after learning, profile-specific relevance, and evidence coverage.

# Phase 17 — Continuous Collective Learning

**Priority: LONG-TERM / OPERATIONAL CAPSTONE**

Turn Phase 16 into an ongoing governed capability. Mnemosyne ultimately becomes a governed collective learning system for a federation of Hermes AI profiles, not merely a memory database or visualization tool.

Core requirements: continuous but governed learning, profile-specific propagation, evidence-backed updates, conflict detection, provenance-preserving transformations, revocation-aware derived knowledge, approval controls, no silent private-memory overwrites, no bypass of mediation/air-lock, and measurable learning effectiveness.

# Ultimate Project Objective

> **Provide a local-first, governed collective memory and learning system in which independent Hermes profiles retain isolated memories, contribute validated knowledge to a collective knowledge base, and can selectively learn from that collective knowledge while preserving provenance, authorization, auditability, and revocation.**

The complete lifecycle is: **Individual Experience → Profile Memory → Mediation/Air-Lock → Collective Knowledge → Evidence/Observations → Knowledge Models → Profile-Specific Learning → Improved Profile Memory → New Experience.**

# Hindsight-Inspired Feature Ledger

These ideas are explicitly tracked so they are not lost.

| Hindsight inspiration | Mnemosyne implementation | Status |
|---|---|---|
| Control Plane | Three-pane Mnemosyne Browser | **Phase 7** |
| Constellation | Existing graph integrated into Browser | **Phase 7** |
| Entity co-occurrence graph | Entity relationship visualization | **Phase 9** |
| Semantic retrieval | Existing embeddings | **Complete** |
| BM25 | SQLite FTS5 | **Phase 8** |
| Graph retrieval | Graph-aware retrieval | **Phase 8** |
| Temporal retrieval | Temporal search/relationships | **Phase 8/9** |
| RRF fusion | Hybrid rank fusion | **Phase 8** |
| Cross-encoder reranking | Optional local reranker | **Phase 8** |
| Entity resolution | Canonical entities/aliases | **Phase 9** |
| Observations | Evidence-backed Mnemosyne observations | **Phase 10** |
| Observation deduplication | Governed consolidation | **Phase 12** |
| Mental Models | Knowledge/Collective Models | **Phase 11** |
| Operation monitoring | Browser Operations view | **Phase 7H** |
| Audit/debug traces | Provenance/explainability | **Phase 13** |
| Migration/export | Future distributed phase | **Phase 14** |
| Prompt/query planning | Future retrieval optimization | **Future** |

---

# Mnemosyne-Specific Principles — Do Not Regress

These remain higher priority than any borrowed feature.

1. **Profile isolation**
2. **Local-first operation**
3. **SQLite-first architecture**
4. **Mediation / air-lock boundary**
5. **Privacy filtering**
6. **Explicit promotion**
7. **Explicit adoption**
8. **Provenance preservation**
9. **Revocation support**
10. **Auditability**
11. **No silent destructive consolidation**
12. **No automatic trust-to-adoption transition**
13. **No raw private-memory leakage through visualization**
14. **Browser must respect authorization and lifecycle state**
15. **Remote functionality must not weaken local governance**

---

# Current Priority Order

## NOW

1. Finish current rebuild/recovery implementation.
2. Establish Phase 7 Browser contracts.
3. Build the three-pane Browser shell.
4. Build the left Control Center.
5. Build center tab/tile workspace.
6. Build the universal right Inspector.
7. Integrate table/memory view.
8. Integrate Timeline.
9. Integrate existing Constellation/Graph.
10. Add Rebuild/Discovery/Embedding/NUKS controls.
11. Add selection continuity across views.

## NEXT

12. SQLite FTS5/BM25.
13. Hybrid retrieval.
14. Temporal retrieval.
15. Entity resolution.
16. Entity/co-occurrence graph.
17. Evidence-backed observations.

## THEN

18. Knowledge Models.
19. Deduplication/consolidation.
20. Retrieval reranking.
21. Deep explainability/provenance browser.
22. Advanced workspace capabilities.

## CAPSTONE

23. Collective-to-Profile Learning.
24. Profile-specific learning proposals.
25. Learning provenance and conflict resolution.
26. Revocation-aware learning reversal.
27. Continuous collective learning.
28. Learning effectiveness metrics.

## LATER / DISTRIBUTED

29. Remote synchronization.
30. Cross-instance migration.
31. Advanced distributed-memory features.

---

# Definition of the Browser

The Mnemosyne Browser is not merely a dashboard.

It is the operational environment for:

**Control → Explore → Inspect → Understand → Edit → Govern**

The intended interaction model is:

```text
LEFT
Control Mnemosyne

        ↓

CENTER
Explore Mnemosyne

        ↓

RIGHT
Inspect / Edit selected object

        ↓

Navigate
to related memories, entities,
relationships, evidence, events,
profiles, and collective knowledge

        ↓

Return to any visualization
without losing selection/context
```

This is the primary UI direction for the project going forward.
