# Phase 11C.5 — Temporal Evidence Aggregation

**Status:** IMPLEMENTATION

## Purpose

Provide a deterministic way to organize multiple temporal state assertions
without collapsing them into a single truth.

Aggregation is an organizational operation, not a governance decision.

## Grouping Dimensions

The implementation supports:

### Subject grouping

All assertions for:

```text
subject_type + subject_id
are placed into one deterministic evidence group.
State grouping
Assertions may additionally be grouped by:
subject_type + subject_id + state
This allows later analysis to compare observations supporting the same
state separately from observations asserting other states.
Ordering
Assertions within a group are ordered by:
1. semantic temporal start;
2. semantic temporal end;
3. evidence ID.
This guarantees deterministic output independent of input order.
Evidence Preservation
Aggregation never:
- deletes evidence;
- merges evidence IDs;
- changes source provenance;
- changes temporal precision;
- changes confidence;
- modifies governed database records.
Every original evidence ID remains represented.
Relationship to Contradiction Detection
Aggregation does not decide whether observations conflict.
Contradiction detection remains a separate analytical layer.
For example, a subject may have:
active
inactive
maintenance
observations simultaneously represented in the aggregate.
The aggregate preserves those observations so later logic can determine
whether their temporal envelopes actually conflict.
Non-Goals
This phase does not:
- resolve entities;
- infer state equivalence;
- rank evidence;
- choose a winning assertion;
- consolidate memories;
- persist aggregate records;
- modify retrieval;
- modify the UI;
- call an LLM.
Governance
Aggregated evidence remains observational and reversible. Any future
consolidation or conflict-resolution layer must retain the underlying
evidence references.
