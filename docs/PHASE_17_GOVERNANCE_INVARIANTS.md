# Mnemosyne Visual Monitor — Phase 17 Governance & Security Invariants

**Status:** PLANNING BASELINE
**Phase:** 17 — Governance, Audit & Security Hardening

## Invariant Policy

These invariants extend the completed Phase 16 governance boundary.

They do not replace Phase 14 adoption authority or Phase 16 federation governance. They harden those boundaries.

An invalid governance state must fail closed.

## Identity & Trust

- **INV-17.01** — Participant identity remains explicit.
- **INV-17.02** — Participant identity does not establish trust.
- **INV-17.03** — Discovery does not establish trust.
- **INV-17.04** — Trust does not establish authorization.
- **INV-17.05** — Trust may expire or be revoked.
- **INV-17.06** — Participant type cannot be silently changed.
- **INV-17.07** — Remote agent services remain distinct from local models.

## Authentication & Sessions

- **INV-17.08** — Privileged federation communication requires authentication.
- **INV-17.09** — Authentication failure fails closed.
- **INV-17.10** — Expired sessions cannot perform privileged operations.
- **INV-17.11** — Revoked sessions cannot perform privileged operations.
- **INV-17.12** — Session identity must match the authenticated participant.
- **INV-17.13** — Session validity cannot be inferred from network reachability.

## Authorization

- **INV-17.14** — Capabilities are explicit.
- **INV-17.15** — Capabilities are least-authority grants.
- **INV-17.16** — Capabilities cannot be escalated implicitly.
- **INV-17.17** — Trust cannot substitute for authorization.
- **INV-17.18** — Validation cannot substitute for authorization.
- **INV-17.19** — Unauthorized operations fail closed.
- **INV-17.20** — Remote peers cannot directly mutate authoritative local datastores.

## Exchange & Provenance

- **INV-17.21** — Knowledge exchange remains governed.
- **INV-17.22** — Receipt is not adoption.
- **INV-17.23** — Exchange validation does not create learned state.
- **INV-17.24** — Source participant identity survives exchange.
- **INV-17.25** — Source profile identity survives exchange.
- **INV-17.26** — Source memory identity survives exchange where applicable.
- **INV-17.27** — Exchange lineage cannot be silently replaced.
- **INV-17.28** — Replayed exchange identities remain idempotent.
- **INV-17.29** — Stale lineage fails closed.
- **INV-17.30** — Malformed provenance cannot become authoritative state.

## Adoption & Projection

- **INV-17.31** — Phase 14 remains the sole explicit adoption authority.
- **INV-17.32** — Federation cannot directly bypass Phase 14 adoption.
- **INV-17.33** — Adoption retains attributable lineage.
- **INV-17.34** — Destination state remains destination-owned.
- **INV-17.35** — Agent projections are governed.
- **INV-17.36** — Projection is not database replication.
- **INV-17.37** — External agent memory is not automatically Mnemosyne memory.

## Revocation & Stale Authority

- **INV-17.38** — Revoked participants cannot continue privileged federation operations.
- **INV-17.39** — Revoked knowledge cannot remain valid merely because it was previously synchronized.
- **INV-17.40** — Stale authorization cannot be reused.
- **INV-17.41** — Replayed revocation signals do not create ambiguous state.
- **INV-17.42** — Revocation does not erase historical audit evidence.
- **INV-17.43** — Revocation remains observable.

## Privacy & Profile Isolation

- **INV-17.44** — Raw profile-local private memory remains protected.
- **INV-17.45** — Federation paths do not expose raw private memory by default.
- **INV-17.46** — Audit records do not become a raw-memory side channel.
- **INV-17.47** — Federation projections do not become raw-memory replication.
- **INV-17.48** — Cross-profile access requires explicit governance.
- **INV-17.49** — Remote peers cannot directly access profile-local datastores.

## Replay, Synchronization & Conflicts

- **INV-17.50** — Duplicate synchronization remains idempotent.
- **INV-17.51** — Replay cannot create duplicate authoritative knowledge.
- **INV-17.52** — Stale checkpoints cannot silently overwrite newer state.
- **INV-17.53** — Partial transfer cannot create ambiguous governance state.
- **INV-17.54** — Network failure cannot create unauthorized authority.
- **INV-17.55** — Conflicts remain visible until explicitly resolved.

## Input Validation & State Integrity

- **INV-17.56** — Invalid identifiers fail closed.
- **INV-17.57** — Invalid enum/state values fail closed.
- **INV-17.58** — Impossible state transitions fail closed.
- **INV-17.59** — Missing required provenance fails closed.
- **INV-17.60** — Invalid timestamps fail closed.
- **INV-17.61** — Duplicate authoritative identities are rejected or explicitly represented as conflicts.
- **INV-17.62** — Corrupt persisted state is detectable.
- **INV-17.63** — Incompatible persisted state is detectable.
- **INV-17.64** — Recovery cannot bypass governance.

## Audit & Observability

- **INV-17.65** — Federation security events remain attributable.
- **INV-17.66** — Application-level audit history remains append-only.
- **INV-17.67** — Existing audit records cannot be rewritten through federation APIs.
- **INV-17.68** — Duplicate audit identities do not create duplicate history.
- **INV-17.69** — Audit records do not contain raw private memory payloads.
- **INV-17.70** — Diagnostics remain observational.
- **INV-17.71** — Diagnostics cannot create authorization.
- **INV-17.72** — Security failures remain observable without exposing private memory.

## Migration & Recovery

- **INV-17.73** — Security-sensitive migrations have explicit preconditions.
- **INV-17.74** — Failed migrations do not silently create partially governed state.
- **INV-17.75** — Migration integrity failures are detectable.
- **INV-17.76** — Recovery preserves provenance.
- **INV-17.77** — Recovery preserves audit history.
- **INV-17.78** — Recovery does not grant new authority.

## Project Boundaries

- **INV-17.79** — Phase 14 adoption governance remains intact.
- **INV-17.80** — Phase 16 federation governance remains intact.
- **INV-17.81** — Athena is not an implicit federation participant.
- **INV-17.82** — Phase 17 does not introduce production deployment.
- **INV-17.83** — Phase 18 remains a distinct productionization boundary.

## Completion

- **INV-17.84** — Security hardening claims require executable or otherwise traceable evidence.
- **INV-17.85** — Negative governance tests are required for security-sensitive authority boundaries.
- **INV-17.86** — Full regression must pass before completion.
- **INV-17.87** — GUI applicability must be explicitly reviewed.
- **INV-17.88** — Completion documentation must identify residual risks.
- **INV-17.89** — Phase 17 cannot be marked complete merely because implementation exists.
