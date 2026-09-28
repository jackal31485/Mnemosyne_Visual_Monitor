# Jarvis Second-Brain Roadmap

**Status:** Proposed architecture and implementation roadmap; no Jarvis implementation exists in this repository.
**Authority:** This document is authoritative for the proposed Jarvis second-brain program. It does **not** renumber, supersede, or falsify the historical Mnemosyne Phase 17/18 records in `docs/PROJECT_ROADMAP.md`.

## Numbering reconciliation

The existing Mnemosyne roadmap already records Phase 17 as completed governance/security hardening and Phase 18 as productionization. The proposed labels “Phase 17–31” in the requested Jarvis program collide with that history.

To preserve both records, this document refers to the requested sequence as the **Jarvis program phases J17–J31**. These are proposed workstream identifiers, not claims that legacy Mnemosyne Phases 17–31 have been implemented, replaced, or reopened. The governing baseline before any J17 implementation is the unresolved Phase 16 runtime-routing gap recorded in `docs/PHASE_16_AUDIT_2026-09-28.md`.

## System architecture

```text
                USER
                  |
             Open WebUI
                  |
                  v
               JARVIS
                  |
      +-----------+-----------+
      |           |           |
  Mnemosyne      Laya     Skills/Tools
      |           |
      |           v
      |       Hermes agents
      |
  Distributed LAN
      |
+------+------+------+
|             |      |
Unraid        Ubuntu  other machines
```

| Component | Responsibility | Explicit boundary |
|---|---|---|
| Open WebUI | Primary user-facing interface; chat first, voice later | Replaceable interface, not Jarvis core |
| Jarvis | Control plane: reasoning, planning, continuity, routing, context assembly, approvals, coordination, evaluation, operational memory, awareness, and notifications | Does not duplicate Mnemosyne governance or Open WebUI presentation |
| Laya | Orchestration component for task graphs, delegation, parallel work, retries, and recovery | Must never become the authority layer |
| Hermes | Worker/agent execution environment: profiles, models, skills, and tools | Executes assigned work under Jarvis-approved task contracts |
| Mnemosyne | Private memory, collective knowledge, retrieval, provenance, lifecycle governance, discovery, distributed routing, and synchronization | Remains the authoritative memory/knowledge substrate |
| Markdown | Human-readable durable second-brain record: tasks, decisions, projects, research, journals, maintenance, and continuity | A record and candidate-knowledge source; not automatic collective knowledge |

## Governing principles

1. Mnemosyne remains the memory/knowledge substrate.
2. Jarvis is the control/orchestration layer.
3. Open WebUI is the primary interface.
4. Laya is an orchestration component, not the authority layer.
5. Hermes remains the worker/agent environment.
6. Distributed Mnemosyne remains intact.
7. Markdown is a first-class second-brain and continuity layer.
8. Markdown is not automatically collective knowledge.
9. Mnemosyne governance remains authoritative for collective knowledge.
10. Discovery does not imply adoption.
11. Detection does not imply authorization.
12. Jarvis requires explicit user authorization before consequential changes.
13. Voice is an interface concern, not a Jarvis-core assumption.
14. Jarvis should not duplicate Mnemosyne functionality unnecessarily.
15. Jarvis should not duplicate Open WebUI functionality unnecessarily.
16. Components should remain replaceable where practical.

## Jarvis authority model

```text
OBSERVE → REASON → RESEARCH → PROPOSE → USER APPROVAL
       → EXECUTE → EVALUATE → COMMIT
```

Jarvis may inspect, reason, research, analyze, and propose without approval. It must obtain explicit user authorization before consequential mutations, including configuration, profiles, prompts, skills, routing, memory or collective-knowledge mutation, deletion, merging, promotion, revocation, adoption, state-mutating synchronization, schedules, Docker, network, and system changes.

Detection and awareness are not authorization. An observation such as “a new Mnemosyne-capable computer was detected” must result in a notification and optional proposal, not automatic configuration or adoption. Every consequential operation must have auditable intent, authority, execution, result, and provenance.

## Awareness and control boundaries

### Future awareness

Jarvis may eventually monitor and notify about new computers, agents, profiles, memories, memory changes, collective changes, conflicts, synchronization events, pending knowledge proposals, revocations, unavailable/stale agents, and health problems. Monitoring produces observations and proposals by default.

### Future Mnemosyne control

With specific authorization, Jarvis may search and inspect memories, retrieve source memory, inspect provenance and collective knowledge, create or update appropriate memories, propose merges/promotions/revocations, inspect relationships and sync state, and perform maintenance. Any mutation remains subject to the existing Mnemosyne lifecycle, provenance, authorization, and audit contracts.

## Markdown second-brain layer

Jarvis should write important work to Markdown as the durable, human-readable continuity record. A proposed structure is:

```text
jarvis/
  tasks/{active,completed,blocked}/
  projects/
  decisions/
  research/
  agent-notes/
  daily/
  journal/
  memory-operations/
  network-events/
  maintenance/
```

This is a proposed architecture, not a committed filesystem layout. Records must make it possible to reconstruct the task, rationale, completed and remaining work, next actions, blockers, decisions, pending approvals, assigned agents, relevant context, and important results.

Markdown-to-Mnemosyne is a governed candidate pipeline:

```text
Jarvis activity → Markdown record → candidate extraction → Mnemosyne ingestion
→ PROPOSED → VALIDATED → PROMOTED
```

Raw logs, temporary notes, and transient observations must not automatically become collective knowledge.

## Daily maintenance

A future daily cycle may inspect memory quality, duplicates, staleness, contradictions, weak evidence, orphaned relationships, collective consistency, knowledge gaps, agent health, routing quality, prompts, skills, tools, task performance, Jarvis state, and unfinished work. Its normal output is proposals and a durable Markdown maintenance record. It must not silently rewrite the system.

## Voice

Voice remains replaceable:

```text
STT / Open WebUI / API → Jarvis → TTS
```

No Jarvis-core data model or authority decision may depend on a specific speech provider or interface.

## Proposed program phases

| Program phase | Scope | Exit boundary |
|---|---|---|
| **J17 — Jarvis Control Plane** | 17A Jarvis Core; 17B Open WebUI integration; 17C agent/capability registry; 17D task planning; 17E approval/authority boundary; 17F initial end-to-end validation | A minimal approved-task flow can plan, request approval, dispatch safely, evaluate, and retain auditable continuity without bypassing Mnemosyne governance. |
| **J18 — Laya Orchestration** | 18A Laya evaluation; 18B Jarvis→Laya interface; 18C agent orchestration; 18D parallel/dependent tasks; 18E retry/recovery; 18F validation | Laya performs execution orchestration only; Jarvis remains the authority. |
| **J19 — Mnemosyne Context Intelligence** | 19A context retrieval; 19B packaging; 19C distributed routing; 19D optimization; 19E knowledge-gap detection | Context packages remain attributable, governed, and retrieval-optimized without copying source memory into Jarvis authority state. |
| **J20 — Agent Execution & Result Intelligence** | 20A task contract; 20B collection; 20C validation; 20D contradiction detection; 20E multi-agent synthesis; 20F failed/incomplete handling; 20G provenance | Results have explicit provenance, validation state, and failure handling. |
| **J21 — Jarvis Operational Memory** | Task history; successful/failed plans; routing outcomes; context packages; approvals; recurring workflows | Operational memory supports continuity while remaining distinct from collective knowledge. |
| **J22 — Markdown Second-Brain Layer** | Durable tasks, projects, decisions, research, daily journal, continuity, agent notes, operational history | Human-readable records support restart/reconstruction and respect approval boundaries. |
| **J23 — Mnemosyne Monitoring & Event Awareness** | New machines/agents/memories, changes, conflicts, sync, health, notifications | Awareness produces notifications and proposals; never implicit adoption. |
| **J24 — Jarvis↔Mnemosyne Control Interface** | Query, retrieve, inspect, propose, explicitly authorized mutation, auditability | Every control action preserves Mnemosyne authorization, lifecycle, provenance, and audit contracts. |
| **J25 — Markdown→Mnemosyne Knowledge Pipeline** | Extraction, candidate generation, provenance, proposal lifecycle, validation, promotion | Markdown candidates become governed knowledge only through the existing lifecycle. |
| **J26 — Daily Maintenance & Continuity** | Maintenance cycle, unfinished work, stale knowledge, duplicates, contradictions, agent/routing optimization, proposals | Maintenance is visible, reviewable, and non-silent. |
| **J27 — Jarvis Dashboard** | Current task, plans, approvals, agent status, orchestration, maintenance, events, failures, continuity | Separate from Mnemosyne Visual Monitor, which remains Mnemosyne-focused. |
| **J28 — Voice Interface** | STT, conversation, TTS, interruption handling, voice approval | Voice remains replaceable and approval semantics remain explicit. |
| **J29 — Security & Governance Hardening** | Authentication, authorization, trust, permissions, approvals, boundaries, audit, secret isolation, Docker/network boundaries | Adversarial and operational controls protect the integrated system. |
| **J30 — Production Orchestration** | Containerization, persistence, startup/recovery, health, backup/restore, upgrades, rollback, Unraid readiness | Recoverable, documented operational deployment. |
| **J31 — Full Second-Brain Validation** | End-to-end Open WebUI, Jarvis, Laya, Hermes, Mnemosyne, distributed discovery/memory, Markdown, orchestration, approvals, maintenance, dashboard, recovery, security | A real multi-component validation proves the intended workflow without claiming unchecked features. |

## Preconditions before J17 coding

1. Close or explicitly defer with accepted risk the Phase 16 runtime source-memory federation enforcement gap.
2. Establish a repository and deployment boundary for Jarvis; do not quietly turn Mnemosyne Visual Monitor into the Jarvis dashboard.
3. Define an approval record and task contract before granting any write-capable tool access.
4. Define identity, session, capability, provenance, and audit interfaces between Jarvis and Mnemosyne before distributed operations.
5. Select an Open WebUI integration approach after evaluating interface contracts, not before.
6. Evaluate Laya against the Jarvis task contract and authority boundary; do not make it an implicit system-of-record.
7. Define Markdown record schemas and retention rules before automating any knowledge extraction.

## Explicit non-implementation statement

This repository currently does not implement Jarvis, Laya, Open WebUI integration, an automated Markdown second brain, automated maintenance, a Jarvis dashboard, or voice. This roadmap authorizes architecture and phased planning only; implementation requires separate, explicitly approved work.
