# Phase 11B.5 — Temporal Extraction / Promotion Pipeline

**Status:** IMPLEMENTATION

## Purpose

Phase 11B.5 provides the deterministic orchestration boundary between the
explicit temporal extractors and governed temporal-evidence persistence.

The pipeline combines:

1. `TemporalExtractor`
2. `TemporalChangeExtractor`
3. `TemporalPromotionService`

into one caller-facing processing operation.

## Processing Contract

Given caller-supplied source text and provenance context, the pipeline:

```text
source text
    |
    +--> explicit temporal extraction
    |
    +--> explicit state-change extraction
              |
              v
       immutable assertions
              |
              v
      governed promotion service
              |
              v
       temporal evidence
The pipeline does not alter the source text.
Provenance
The caller supplies:
- collective entry ID;
- source memory ID;
- source profile.
Those values are forwarded unchanged to both extraction paths.
Promotion remains responsible for the governed persistence boundary.
Determinism
The pipeline:
- performs no LLM inference;
- performs no chronology inference;
- performs no entity resolution;
- performs no conflict detection;
- performs no retrieval;
- performs no UI operations;
- preserves extractor and promotion ordering;
- produces immutable result containers.
State Changes
Explicit state-change assertions remain distinct from temporal date assertions.
A state change does not acquire an invented timestamp merely because it
passes through the pipeline.
Non-Goals
This phase does not implement:
- interval algebra;
- temporal relationship inference;
- contradiction detection;
- historical reconstruction;
- temporal reranking;
- entity/relationship resolution;
- Browser timeline changes.
Those capabilities remain subsequent Phase 11 work.
