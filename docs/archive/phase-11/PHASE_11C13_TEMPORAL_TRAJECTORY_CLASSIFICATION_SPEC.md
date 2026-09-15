# Phase 11C.13 — Temporal Trajectory Classification

## Purpose

C.13 provides a deterministic descriptive classification of temporal
histories after the synthesis layer introduced in C.12.

It identifies broad trajectory patterns without selecting a truthful
history or introducing new temporal inference.

## Classification

A trajectory may be classified as:

- `empty` — no temporal observations.
- `stable` — one state is observed throughout.
- `transition` — the state changes without a detected reversal or
  oscillation pattern.
- `reversal` — a state returns after a different intervening state.
- `oscillation` — repeated alternating movement between states.
- `divergent` — multiple histories disagree at one or more positions.
- `incomplete` — one or more histories do not cover the full comparison
  positions.
- `uncertain` — temporal uncertainty is explicitly present.

## Precedence

For multi-history synthesis, classifications are applied conservatively:

1. divergent
2. incomplete
3. uncertain
4. stable
5. oscillation
6. reversal
7. transition
8. empty

Divergence is never converted into consensus merely because one state has
majority support.

## Guarantees

C.13:

- performs no persistence;
- performs no retrieval;
- performs no extraction;
- performs no entity resolution;
- performs no truth selection;
- does not mutate temporal evidence;
- preserves uncertainty;
- keeps incompleteness distinct from disagreement;
- produces deterministic results.

## Relationship to earlier phases

C.13 consumes the outputs of:

- C.8 temporal state history;
- C.9 history comparison;
- C.10 history divergence;
- C.11 history consensus;
- C.12 history synthesis.

The trajectory is a descriptive interpretation of those structures, not a
replacement for them.

## Future use

Later phases may use trajectory classifications to improve:

- temporal retrieval reranking;
- evidence presentation;
- higher-level memory models;
- temporal narrative generation;
- contradiction review.

Those consumers must preserve the distinction between descriptive
classification and factual truth.
