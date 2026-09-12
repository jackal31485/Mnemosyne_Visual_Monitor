# Phase 11C.4 — Semantic Temporal Contradiction Detection

**Status:** IMPLEMENTATION

## Purpose

Introduce a conservative semantic layer that can identify temporal
contradictions between explicit state assertions.

The phase builds on:

- Phase 11B.3 state-change extraction;
- Phase 11C.1 interval reasoning;
- Phase 11C.2 precision-aware reasoning;
- Phase 11C.3 temporal consistency analysis.

## Contradiction Rule

Two assertions may be considered a temporal contradiction only when all
of the following are true:

1. They refer to the same subject.
2. They explicitly assert different states.
3. Their temporal relationship establishes definite overlap.

Example:

```text
Entity A was active during January 10.
Entity A was inactive during January 10.
This is a contradiction because the same subject is assigned incompatible
explicit states over the same definite temporal interval.
Non-Contradictions
The following are deliberately not contradictions:
Different subjects
Entity A active
Entity B inactive
Same state
Entity A active
Entity A active
Sequential states
Entity A active during January 10.
Entity A inactive during January 11.
This may represent a legitimate state transition.
Indeterminate overlap
If the temporal evidence is too imprecise to establish a definite
relationship, no contradiction is emitted.
State Semantics
This phase treats distinct explicit state labels as incompatible.
It does not attempt to infer state taxonomies or semantic equivalence.
For example, it does not decide whether:
active
running
online
are equivalent states.
That requires a later governed semantic model.
Provenance
Every contradiction retains both source evidence identifiers and the
original state values.
No source evidence is modified, merged, revoked, or promoted.
Non-Goals
This phase does not:
- persist contradiction records;
- revoke evidence;
- resolve entities;
- infer states from arbitrary text;
- infer missing temporal information;
- modify retrieval;
- modify ranking;
- modify the UI;
- use an LLM;
- decide which source is correct.
Governance
A contradiction is an analytical finding, not an authoritative verdict.
A later governance layer may decide how contradictory evidence should be
presented, weighted, reviewed, or retained.
