# Phase 12 — Evidence Consolidation & Memory Synthesis

**Status:** READY TO BEGIN  
**Previous phase:** Phase 11 — Temporal Intelligence  
**Next phase:** Phase 13 — Higher-Level Mental Models  
**Phase priority:** MEDIUM-HIGH  
**Architecture role:** Evidence consolidation and memory synthesis

---

# Purpose

Phase 12 moves Mnemosyne from individually governed observations toward
evidence-backed consolidated knowledge.

The phase builds on the entity, relationship, and temporal foundations
completed in Phases 10 and 11.

The central question becomes:

> **Which observations represent the same underlying knowledge, and how can
> they be consolidated without destroying evidence or provenance?**

Phase 12 is therefore a consolidation layer, not a replacement for the
underlying memory system.

---

# Architectural Position

```text
Profile-Local Memories
        |
        v
Governed Promotion
        |
        v
Collective Evidence
        |
        +---- Entities
        |
        +---- Relationships
        |
        +---- Temporal Context
        |
        v
Phase 12
Evidence Consolidation
        |
        +---- Duplicate detection
        |
        +---- Similarity analysis
        |
        +---- Contradiction detection
        |
        +---- Evidence weighting
        |
        +---- Candidate consolidation
        |
        +---- Governed synthesis
        |
        v
Consolidated Knowledge
        |
        v
Phase 13
Higher-Level Mental Models
Phase 12 must never bypass the governed evidence boundary.
Phase 12 Goals
12A — Observation Similarity
Identify observations that may describe the same underlying fact,
state, entity, relationship, or knowledge unit.
Potential signals include:
- normalized textual similarity;
- semantic similarity;
- shared entities;
- shared relationships;
- temporal compatibility;
- shared evidence;
- profile/source overlap;
- explicit identifiers;
- observation type;
- confidence;
- provenance.
Similarity is a signal for review or consolidation.
Similarity alone is not authorization to merge.
12B — Near-Duplicate Detection
Detect observations that are substantially equivalent but differ in wording,
metadata, provenance, or supporting evidence.
Examples:
Observation A:
"SQLite is the authoritative Mnemosyne datastore."

Observation B:
"Mnemosyne uses SQLite as its authoritative storage layer."
These may represent the same underlying observation.
The system should identify them as a consolidation candidate rather than
silently replacing one with the other.
12C — Candidate Consolidation
A candidate consolidation represents a proposed relationship between two or
more observations.
Example:
Observation A
      |
      +---- similarity: 0.94
      |
Observation B
      |
      v
Candidate Consolidation
A candidate should contain enough information to explain:
- which observations are involved;
- why they were considered related;
- similarity evidence;
- entity overlap;
- temporal compatibility;
- supporting evidence;
- contradictory evidence;
- source profiles;
- confidence;
- proposed action.
12D — Evidence Validation
Before consolidation, Mnemosyne must validate the supporting evidence.
Validation must confirm:
- source memory still exists;
- source profile remains consistent;
- source memory is authorized for collective use;
- supporting evidence has not been revoked;
- observation lifecycle permits consolidation;
- provenance remains available;
- temporal information is compatible where relevant;
- contradictory evidence has been considered.
Revoked or unavailable evidence must not silently continue to support a
consolidated result.
12E — Evidence Weighting
Evidence should not be treated as interchangeable merely because it supports
the same statement.
Phase 12 may consider:
- number of supporting memories;
- independent source profiles;
- source reliability metadata where explicitly available;
- confidence;
- evidence precision;
- temporal recency where applicable;
- corroboration;
- contradiction;
- provenance completeness.
The weighting mechanism must remain deterministic and explainable.
No opaque trust score should become authoritative without a defined
governance contract.
12F — Contradiction Handling
Consolidation must distinguish:
Same fact
    |
    +---- reinforcing evidence
    |
    +---- duplicate wording
    |
    +---- refinement
    |
    +---- temporal change
    |
    +---- genuine contradiction
A contradiction must not be erased merely because one observation has higher
similarity or confidence.
Possible outcomes include:
- retain both observations;
- mark a consolidation candidate as conflicted;
- create a refined observation;
- create temporally distinct observations;
- require review;
- reject consolidation.
12G — Evidence-Preserving Synthesis
A consolidated observation must preserve its supporting evidence.
Example:
Consolidated Observation

Statement:
"SQLite remains the authoritative Mnemosyne datastore."

Supporting observations:
  observation-17
  observation-31
  observation-44

Supporting memories:
  Athena / memory-A
  Horus  / memory-B
  Odin   / memory-C

Supporting profiles:
  Athena
  Horus
  Odin

Confidence:
  0.94

Status:
  promoted

History:
  created
  consolidated
  refined
The consolidated object is derived from the evidence.
The evidence is not replaced by the consolidated object.
12H — Consolidation History
Every consolidation must be traceable.
History should capture:
- candidate creation;
- similarity evaluation;
- evidence validation;
- consolidation decision;
- participating observations;
- supporting evidence;
- contradictory evidence;
- resulting observation;
- actor or process responsible;
- timestamp;
- revision;
- revocation effects.
A later reviewer must be able to reconstruct why the consolidation occurred.
12I — Revocation Awareness
If supporting evidence is revoked after consolidation:
Supporting Evidence
        |
        X revoked
        |
        v
Consolidated Observation
        |
        +---- evidence count changes
        +---- confidence may change
        +---- review may be required
        +---- history remains intact
Revocation must not silently delete the consolidated object's history.
The system must be able to distinguish:
Previously supported
from:
Currently supported
12J — Deterministic Rebuildability
Given the same:
- authorized source memories;
- observations;
- entities;
- relationships;
- temporal evidence;
- consolidation rules;
- thresholds;
the consolidation result should be reproducible.
No hidden mutable state should be required to reproduce the result.
Governance Invariants
The following rules are mandatory throughout Phase 12.
1. Source-memory immutability
Source memories are never silently modified or destroyed as part of
consolidation.
2. Provenance preservation
Every consolidated result must retain traceability to its underlying
observations and source memories.
3. Promotion governance
Only evidence that is authorized for collective use may participate in
collective consolidation.
4. Revocation awareness
Revoked evidence must not continue to appear as currently valid support.
5. Profile isolation
Source profile identity must remain attached to provenance.
6. No silent destructive merge
Consolidation must never irreversibly destroy the participating observations.
7. No inference presented as evidence
A synthesized conclusion must remain distinguishable from directly observed
evidence.
8. Contradiction preservation
Conflicting evidence must remain discoverable.
9. Temporal awareness
Observations that differ because facts changed over time must not be treated as
duplicates solely because their wording is similar.
10. Deterministic behavior
Similarity and consolidation decisions must be reproducible.
11. Auditability
Every governed consolidation decision must have an inspectable history.
12. Browser governance
Any future Browser presentation must apply the same authorization and
lifecycle rules as the underlying API.
What Phase 12 Does Not Do
Phase 12 does not:
- create higher-level mental models;
- perform unrestricted inference;
- automatically transfer knowledge between profiles;
- delete source memories;
- erase contradictory observations;
- establish remote synchronization;
- replace temporal intelligence;
- replace entity or relationship intelligence;
- make derived knowledge equivalent to raw evidence.
Those responsibilities belong to later phases or existing governed layers.
Phase 12 Conceptual Flow
  

#chatgpt-mermaid-_r_1h4_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-_r_1h4_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_1h4_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_1h4_ .error-icon{fill:rgb(27, 27, 27);}#chatgpt-mermaid-_r_1h4_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1h4_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-_r_1h4_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-_r_1h4_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-_r_1h4_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-_r_1h4_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-_r_1h4_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-_r_1h4_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1h4_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1h4_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-_r_1h4_ p{margin:0;}#chatgpt-mermaid-_r_1h4_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1h4_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1h4_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1h4_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-_r_1h4_ .label text,#chatgpt-mermaid-_r_1h4_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1h4_ .node rect,#chatgpt-mermaid-_r_1h4_ .node circle,#chatgpt-mermaid-_r_1h4_ .node ellipse,#chatgpt-mermaid-_r_1h4_ .node polygon,#chatgpt-mermaid-_r_1h4_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-_r_1h4_ .rough-node .label text,#chatgpt-mermaid-_r_1h4_ .node .label text,#chatgpt-mermaid-_r_1h4_ .image-shape .label,#chatgpt-mermaid-_r_1h4_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-_r_1h4_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-_r_1h4_ .rough-node .label,#chatgpt-mermaid-_r_1h4_ .node .label,#chatgpt-mermaid-_r_1h4_ .image-shape .label,#chatgpt-mermaid-_r_1h4_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-_r_1h4_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-_r_1h4_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1h4_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1h4_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-_r_1h4_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-_r_1h4_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-_r_1h4_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-_r_1h4_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_1h4_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-_r_1h4_ .cluster rect{fill:rgb(27, 27, 27);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-_r_1h4_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1h4_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1h4_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(27, 27, 27);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-_r_1h4_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1h4_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-_r_1h4_ .icon-shape,#chatgpt-mermaid-_r_1h4_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-_r_1h4_ .icon-shape p,#chatgpt-mermaid-_r_1h4_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-_r_1h4_ .icon-shape .label rect,#chatgpt-mermaid-_r_1h4_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_1h4_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-_r_1h4_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-_r_1h4_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-_r_1h4_ [data-look="neo"].node rect,#chatgpt-mermaid-_r_1h4_ [data-look="neo"].cluster rect,#chatgpt-mermaid-_r_1h4_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-_r_1h4_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1h4_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-_r_1h4_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-_r_1h4_-gradient);stroke-width:1px;}#chatgpt-mermaid-_r_1h4_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1h4_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-_r_1h4_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-_r_1h4_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1h4_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-_r_1h4_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-_r_1h4_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1h4_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-_r_1h4_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1h4_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-_r_1h4_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-_r_1h4_ .node tspan[font-weight="normal"],#chatgpt-mermaid-_r_1h4_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-_r_1h4_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-_r_1h4_ .node rect,#chatgpt-mermaid-_r_1h4_ .node circle,#chatgpt-mermaid-_r_1h4_ .node ellipse,#chatgpt-mermaid-_r_1h4_ .node polygon,#chatgpt-mermaid-_r_1h4_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-_r_1h4_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-_r_1h4_ .node.mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2,2;}#chatgpt-mermaid-_r_1h4_ .edgePaths .flowchart-link{stroke:rgb(26, 62, 95);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-_r_1h4_ .marker{fill:rgb(26, 62, 95);stroke:rgb(26, 62, 95);}#chatgpt-mermaid-_r_1h4_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}Authorized ObservationsSimilarity AnalysisPotentially Equivalent?Retain IndependentlyConsolidation CandidateEvidence ValidationTemporal CompatibilityContradiction AnalysisEvidence WeightingGoverned DecisionRetain ObservationsReview RequiredConsolidated ObservationPreserve Supporting EvidencePreserve ProvenanceRecord Consolidation HistoryGoverned KnowledgeRevocationNoYesRejectReviewConsolidate


100%




Phase 12 Deliverables
The implementation should eventually provide:
- observation similarity service;
- deterministic near-duplicate detection;
- consolidation candidate model;
- evidence validation;
- contradiction analysis;
- evidence weighting;
- governed consolidation;
- consolidation history;
- revocation-aware recalculation;
- provenance-preserving storage;
- unit tests;
- integration tests;
- Browser/API inspection where appropriate;
- completion audit.
Recommended Implementation Sequence
12A
Define consolidation contracts and invariants.
12B
Implement deterministic observation similarity.
12C
Implement candidate consolidation.
12D
Implement evidence validation and contradiction handling.
12E
Implement governed consolidation.
12F
Implement history and revocation-aware behavior.
12G
Integrate consolidated knowledge with retrieval and Browser inspection.
12H
Run full regression and live validation.
Completion Criteria
Phase 12 may be marked COMPLETE only when:
- similarity detection is deterministic;
- near-duplicate candidates are identifiable;
- evidence validation is enforced;
- contradictions are preserved;
- consolidation is governed;
- source memories remain intact;
- provenance remains navigable;
- revocation affects current support;
- consolidation history is auditable;
- profile isolation remains intact;
- no derived statement is represented as raw evidence;
- full regression passes;
- Browser/API behavior is validated where applicable;
- no Athena work is required unless explicitly authorized;
- final documentation is committed;
- Phase 12 completion audit is created;
- Phase 12 completion tag is created;
- roadmap advances to Phase 13.
Phase 12 Exit
The successful completion of Phase 12 should leave Mnemosyne with:
Memories
   ↓
Evidence
   ↓
Observations
   ↓
Entities / Relationships / Time
   ↓
Consolidated Evidence-backed Knowledge
   ↓
Phase 13 Mental Models
The central architectural rule remains:
Consolidation creates a stronger representation of knowledge without
destroying the evidence from which that knowledge was derived.
