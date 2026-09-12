# Phase 11B.2 — Explicit Temporal Extraction

**Status:** IMPLEMENTED — Phase 11B.2
**Previous stage:** Phase 11B.1 — Temporal Assertion Contract

## Objective

Extract temporal information that is explicitly present in governed source
memory content without inferring missing dates or reconstructing chronology.

## Boundary

```text
source text supplied by caller
        ↓
TemporalExtractor
        ↓
TemporalAssertion
Persistence remains the responsibility of TemporalEvidenceDAO.
Supported explicit information
The extractor recognizes:
- ISO calendar dates;
- written calendar dates;
- month/year expressions;
- year expressions;
- explicit date ranges;
- explicit before, after, during, and ongoing relations.
Precision
Extracted precision is preserved:
- year;
- month;
- day.
The extractor never upgrades an expression to greater precision.
For example:
March 2026
remains month precision. It does not become March 1.
Explicit relations
Expressions such as:
Project A started before Project B.
produce a before temporal assertion without inventing dates.
Similarly:
Project A started after Project B.
produces an after assertion without invented timestamps.
Unsupported inference
11B.2 does not:
- infer missing dates;
- resolve vague relative dates;
- invent interval endpoints;
- perform chronology inference;
- resolve entities;
- decide contradictions;
- authorize source memories;
- persist evidence;
- modify source memories;
- modify TemporalSearcher;
- modify retrieval/reranking.
Governance
Governance is intentionally deferred to 11B.4.
The extractor accepts already-supplied source identifiers and provenance and
returns assertions. It does not decide whether a source is eligible for
processing.
Determinism
Given identical input text and provenance, extraction returns identical
ordered assertions.
Next stage
Phase 11B.3 — explicit state-change extraction.
