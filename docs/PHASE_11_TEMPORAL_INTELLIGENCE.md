# Phase 11 — Temporal Intelligence

**Status:** IN PROGRESS — Temporal Intelligence / 11C
**Previous phase:** Phase 10 — Entity & Relationship Intelligence
**Current stage:** 11C.16 — Temporal Change-Point Analysis
**Next phase:** TBD

## Purpose

Extend Mnemosyne's entity and relationship intelligence with temporal
understanding.

The objective is to move from:

**Memory → Retrieval → Entities → Relationships**

toward:

**Memory → Retrieval → Entities → Relationships → Temporal Understanding**

Temporal intelligence must distinguish observed evidence from derived
temporal interpretation. No temporal analysis may silently rewrite,
promote, or replace source evidence.

---

## Initial scope

Phase 11 investigates:

- temporal evidence attached to memories, entities, and relationships;
- explicit event and state-change extraction;
- chronology and temporal ordering;
- valid-from / valid-to semantics where evidence supports them;
- temporal precision and confidence;
- historical entity state;
- relationship state across time;
- time-aware retrieval and reranking;
- temporal graph projection;
- contradiction handling across different time periods;
- temporal history and trajectory analysis.

---

## Governance constraints

Phase 11 must preserve:

- source-memory immutability;
- provenance;
- promotion/revocation enforcement;
- qualified profile identity;
- explicit evidence;
- no fabricated dates;
- no fabricated temporal bounds;
- no silent historical rewriting;
- deterministic rebuildability;
- separation between observed evidence and inferred temporal state.

Temporal analysis is descriptive unless a later specification explicitly
defines an inference boundary.

---

# Phase 11 implementation history

## 11A — Temporal Evidence Foundation

Established the governed `temporal_evidence` foundation in the collective
database.

The layer defines temporal evidence dimensions, controlled vocabularies,
validation, provenance, and governance boundaries.

11A deliberately does not perform temporal extraction or inference.

Specification:

`docs/PHASE_11A_TEMPORAL_EVIDENCE_SPEC.md`

---

## 11B — Temporal Extraction

Established the temporal extraction contract and progressively implemented:

### 11B.1 — Temporal Assertion

Introduced the immutable temporal assertion domain contract.

### 11B.2 — Explicit Temporal Extraction

Extracts explicit dates and simple temporal phrases without inventing
temporal information.

Specification:

`docs/PHASE_11B2_EXPLICIT_TEMPORAL_EXTRACTION_SPEC.md`

### 11B.3 — Explicit State-Change Extraction

Extracts explicit state-change language such as:

- changed from X to Y;
- was X, then became Y;
- became Y;
- was replaced by Y.

No dates are inferred.

### 11B.4 — Temporal Evidence Promotion

Promotes extracted temporal assertions into governed temporal evidence.

State-change assertions may use `during` with unknown precision rather than
fabricating temporal bounds.

### 11B.5 — Temporal Extraction / Promotion Pipeline

Combines explicit temporal extraction, state-change extraction, and governed
promotion into a deterministic pipeline.

---

# Phase 11C — Temporal Reasoning

Phase 11C builds deterministic descriptive reasoning on top of governed
temporal evidence.

## 11C.1 — Temporal Interval Reasoning

Introduced temporal intervals and structural temporal relationship comparison.

## 11C.2 — Precision-Aware Temporal Reasoning

Introduced semantic temporal precision and conservative certainty handling.

## 11C.3 — Temporal Consistency Analysis

Introduced pairwise temporal consistency analysis without treating overlap
alone as contradiction.

## 11C.4 — Semantic Temporal Contradiction Detection

Introduced conservative contradiction detection for incompatible states
belonging to the same subject and definite temporal overlap.

## 11C.5 — Temporal Evidence Aggregation

Groups temporal evidence deterministically by subject and state.

## 11C.6 — Temporal State Timeline

Builds deterministic state timelines and adjacent transition descriptions.

## 11C.7 — Temporal State Transition Analysis

Analyzes changed and unchanged transitions, including definite versus
indeterminate temporal relationships.

## 11C.8 — Temporal State History

Introduces an immutable historical representation containing observations,
states, transition counts, and uncertainty.

## 11C.9 — Temporal History Comparison

Compares two state histories descriptively, including shared and divergent
state positions.

## 11C.10 — Temporal History Divergence

Summarizes history divergence using deterministic comparison metrics.

## 11C.11 — Temporal History Consensus

Describes agreement and disagreement across multiple state histories.

Majority support remains descriptive and is never promoted to truth.

## 11C.12 — Temporal History Synthesis

Synthesizes multiple histories into a deterministic descriptive summary,
including consensus, divergence, incompleteness, coverage, and uncertainty.

## 11C.13 — Temporal Trajectory Classification

Classifies observed state sequences as:

- empty;
- stable;
- transition;
- reversal;
- oscillation;
- divergent;
- incomplete;
- uncertain.

Classification is descriptive only.

## 11C.14 — Temporal Trajectory Comparison

Compares trajectory classifications and their descriptive metrics without
selecting an authoritative trajectory.

## 11C.15 — Temporal Trajectory Consensus

Describes agreement and disagreement across multiple trajectory
classifications for the same subject.

A majority trajectory is descriptive evidence only and is not treated as
truth.

---

# 11C.16 — Temporal Change-Point Analysis

C.16 analyzes where meaningful state changes occur within an observed
trajectory.

The purpose is to distinguish:

**observations**

from:

**actual state changes**

For example:

```text
active → active → inactive → inactive → active → active
          │               │
       change           change
The layer identifies change points and stable runs without inventing dates,
states, or missing observations.
Planned scope
C.16 will provide:
- ordered change-point positions;
- previous and next state for each change;
- number of observed states;
- number of actual state changes;
- stable-run analysis;
- longest stable run;
- deterministic change-point representation.
An unchanged observation does not constitute a state transition.
For example:
active → inactive → active → active
contains four observations but only two state changes.
Non-goals
C.16 does not:
- infer missing states;
- infer dates;
- select a truthful trajectory;
- modify temporal evidence;
- persist derived analysis;
- resolve provenance conflicts;
- perform entity resolution;
- override governance;
- convert descriptive change points into authoritative historical facts.
Architecture
The current temporal intelligence pipeline is:
Temporal Evidence
       ↓
Temporal Assertion / Extraction / Promotion
       ↓
Temporal Interval Reasoning
       ↓
Temporal Consistency / Contradiction
       ↓
Temporal Evidence Aggregation
       ↓
Temporal State Timeline
       ↓
Temporal State Transition Analysis
       ↓
Temporal State History
       ↓
Temporal History Comparison
       ↓
Temporal History Divergence
       ↓
Temporal History Consensus
       ↓
Temporal History Synthesis
       ↓
Temporal Trajectory Classification
       ↓
Temporal Trajectory Comparison
       ↓
Temporal Trajectory Consensus
       ↓
Temporal Change-Point Analysis
Design principles
Evidence first
Temporal reasoning operates on governed evidence and derived domain
objects. Derived analysis must not silently become evidence.
No fabricated time
Unknown time remains unknown.
The system must never manufacture a date, interval, ordering, or temporal
boundary merely because a downstream algorithm would prefer one.
Descriptive before inferential
The current temporal reasoning layers describe what the evidence supports.
They do not decide which conflicting source is true.
Deterministic
Equivalent input must produce equivalent temporal analysis.
Grouped operations must use deterministic ordering.
Provenance preserving
Every future integration point must remain capable of tracing derived
temporal conclusions back to their underlying evidence.
Separation of concerns
Temporal extraction, evidence promotion, temporal reasoning, retrieval,
graph projection, and UI presentation remain separate layers.
Validation
Phase 11 development is validated incrementally with focused tests and the
full Mnemosyne test suite after each completed stage.
The current baseline following 11C.15 is:
867 passed, 5 skipped, 4 warnings
The four warnings are existing FastAPI on_event deprecation warnings in
app/main.py. They are outside the scope of temporal-intelligence work and
must not be modified as part of C.16.
Future Phase 11 work
After the 11C reasoning chain is complete, remaining Phase 11 candidates
include integration of temporal intelligence with:
- hybrid retrieval and temporal reranking;
- temporal graph projection;
- entity historical state;
- relationship state across time;
- evidence-backed temporal summaries;
- temporal visualization.
These integrations require separate specifications and must not be
implicitly introduced into the C.16 domain layer.
