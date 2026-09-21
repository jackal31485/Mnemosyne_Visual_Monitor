# Phase 18 — Productionization Baseline

**Status:** Phase 18A — Baseline established  
**Date:** 2026-09-21  
**Predecessor:** Phase 17 — Governance, Audit & Security Hardening  
**Next:** Phase 18B — Packaging and local production execution

## 1. Purpose

This document establishes the productionization baseline for Mnemosyne Visual
Monitor before deployment packaging or UnRAID changes are introduced.

The baseline is derived from the validated repository at the beginning of
Phase 18. It records the existing runtime, dependency, storage, configuration,
and deployment boundaries that productionization must preserve.

Phase 18 is productionization work, not a new feature-development phase.

## 2. Baseline Repository State

- Branch: `master`
- Baseline commit: `9afeb01cc79b173f7d99c37da68535e46bcdbedb`
- Remote: `origin/master`
- Repository is clean at baseline.
- Local tags: none.
- Remote tags: none.

The baseline is the completed Phase 17 architecture after documentation
cleanup.

## 3. Validation Baseline

The complete regression suite at Phase 18 entry produced:

- 1,660 passed
- 14 skipped
- 4 warnings
- runtime: 19.60 seconds
- `git diff --check`: clean

The warnings are existing FastAPI `on_event` deprecation warnings in the
application startup and shutdown handlers and related FastAPI internals.

No Phase 18 work may reduce the validated regression baseline without an
explicitly documented reason and replacement validation.

## 4. Runtime Baseline

Current application runtime:

- Python 3.12.3
- FastAPI `>=0.141,<1`
- Uvicorn `>=0.52,<1`
- sentence-transformers `==6.0.0`

The application entrypoint currently resides in `app/main.py`.

Phase 18 packaging must reproduce the validated runtime rather than silently
introducing a different Python or dependency environment.

## 5. Application Boundary

The repository contains:

- FastAPI application routes under `app/routes/`
- application services under `app/services/`
- domain architecture under `src/domain/`
- retrieval architecture under `src/retrieval/`
- discovery architecture under `src/discovery/`
- supporting services under `src/services/`
- web entrypoint support under `src/web/`

The deployment package must treat these existing boundaries as authoritative.

## 6. Storage Architecture

The production deployment must preserve the existing storage separation.

### 6.1 Profile-local memory

Each Hermes profile has its own Mnemosyne database:

`<profile>/mnemosyne/data/mnemosyne.db`

These databases contain profile-local memory and remain outside the collective
knowledge storage boundary.

### 6.2 Collective database

The authoritative collective database is:

`data/collective.db`

It contains governed collective knowledge and associated provenance,
evidence, entity, relationship, temporal, lifecycle, transfer, and federation
metadata.

Raw private profile memory must not be introduced into this database by
deployment packaging.

### 6.3 Retrieval database

The retrieval database is:

`data/retrieval.db`

It is a rebuildable retrieval/search cache. The collective database remains
authoritative for lifecycle governance.

Production backup and recovery procedures must therefore distinguish
authoritative databases from rebuildable derived data.

### 6.4 Discovery database

Discovery state currently uses:

`app/db/discovery.db`

Its persistence requirements must be explicitly evaluated during deployment
packaging rather than being treated as disposable container state.

## 7. Configuration Baseline

Existing environment-controlled behavior includes:

- `LAN_DISCOVERY_GROUP`
- `LAN_DISCOVERY_PORT`
- `MNEMOSYNE_EMBEDDING_DEVICE`
- `MNEMOSYNE_HYBRID_RERANK`
- `MNEMOSYNE_RERANK_DEVICE`
- profile-specific graph database mappings through the
  `MNEMOSYNE_GRAPH_DB_<PROFILE>` convention
- Hermes profile environment information including
  `HERMES_CURRENT_PROFILE`

Phase 18 must document all production configuration explicitly before
deployment.

Secrets, credentials, or authentication material must not be embedded in
source-controlled deployment configuration.

## 8. Deployment Packaging Baseline

At Phase 18 entry the repository does not contain:

- Dockerfile
- Docker Compose definition
- systemd service
- Makefile
- production startup script
- production health-check script

These are therefore Phase 18 deliverables rather than assumed existing
infrastructure.

Packaging must be introduced incrementally and validated locally before
UnRAID deployment.

## 9. Productionization Invariants

Productionization must preserve:

1. Profile-local memory isolation.
2. Collective knowledge governance.
3. Provenance and source identifiers.
4. Promoted and non-revoked retrieval authorization.
5. Explicit transfer and adoption authority.
6. Federation authentication and authorization boundaries.
7. Revocation and stale-authority protection.
8. Append-only logical audit history.
9. Source database read-only behavior where already required.
10. Rebuildability of derived indexes and projections.
11. Recovery safety for authoritative data.
12. No automatic trust or automatic knowledge adoption.
13. No implicit Athena participation.
14. The distinction between deployment and governance authority.

## 10. Local-First Productionization Order

Phase 18 follows this order:

1. Establish production architecture baseline.
2. Package the application locally.
3. Validate local production execution.
4. Define persistent storage boundaries.
5. Define backup and restoration procedures.
6. Define monitoring and health checks.
7. Define upgrade, migration, and rollback procedures.
8. Validate performance against the real deployment shape.
9. Deploy to UnRAID.
10. Execute the UnRAID production-readiness checklist.
11. Perform final end-to-end validation.
12. Produce the final production declaration.

UnRAID is the deployment target, not the environment in which architecture
is discovered.

## 11. Existing UnRAID Readiness Boundary

`docs/UNRAID_PRODUCTION_READINESS_CHECKLIST.md` remains the authoritative
pre-production acceptance checklist.

It already covers:

- deployment baseline;
- browser validation;
- profile isolation;
- collective governance;
- cross-profile learning;
- memory deletion;
- resurrection and re-ingestion;
- provenance;
- derived knowledge;
- temporal governance;
- restart persistence;
- backup and recovery;
- security and permissions;
- Hermes integration;
- visual validation;
- performance and stability;
- regression;
- production sign-off.

Phase 18 implementation work must satisfy this checklist rather than replacing
it with a narrower deployment test.

## 12. Explicitly Deferred Until Later Phase 18 Work

The following are not established by this baseline:

- container image construction;
- container filesystem layout;
- persistent volume mapping;
- production startup command;
- health endpoint selection;
- backup implementation;
- restore implementation;
- monitoring implementation;
- migration tooling;
- rollback procedure;
- performance qualification;
- UnRAID deployment;
- final production-readiness declaration.

These require evidence during subsequent Phase 18 work.

## 13. Phase 18A Exit Criteria

Phase 18A is complete when:

- the production runtime boundary is documented;
- the storage boundaries are documented;
- configuration requirements are documented;
- deployment gaps are explicitly identified;
- the existing UnRAID checklist is retained as the acceptance authority;
- no application behavior has been changed;
- the documentation passes `git diff --check`;
- the full regression baseline remains unchanged.

## 14. Phase Boundary

Phase 18A establishes what must be productionized.

It does not itself deploy Mnemosyne, introduce container infrastructure,
modify governance, alter federation behavior, change retrieval semantics, or
declare the system production-ready.
