# Mnemosyne UnRAID Production Readiness Checklist

**Document:** `UNRAID_PRODUCTION_READINESS_CHECKLIST.md`  
**Status:** PLANNED — Pre-production validation checklist  
**Purpose:** Validate the complete Mnemosyne system after deployment to UnRAID and before declaring the UnRAID deployment production-ready.

---

## 1. Purpose and Completion Rule

This checklist defines the validation work that must be completed **after Mnemosyne is deployed to UnRAID but before the system is considered production-ready**.

The goal is not merely to demonstrate that the application starts.

Production readiness requires evidence that:

- [ ] the deployed system operates correctly;
- [ ] profile isolation remains intact;
- [ ] collective knowledge governance remains intact;
- [ ] cross-profile learning behaves as designed;
- [ ] user review and deletion are respected;
- [ ] deleted memories do not silently return through later ingestion or consolidation;
- [ ] derived knowledge preserves provenance and governance;
- [ ] the browser interface accurately represents the governed data;
- [ ] the Hermes-Agent integration behaves correctly;
- [ ] persistence survives restart;
- [ ] backup and recovery procedures work;
- [ ] the system remains observable and maintainable.

### Production-readiness rule

**No production-ready declaration should be made until every required section below is either PASS or has a documented, explicitly accepted exception.**

---

## 2. Deployment Baseline

### 2.1 UnRAID Environment

- [ ] Confirm Mnemosyne is running on the intended UnRAID host.
- [ ] Confirm the deployed container/service configuration matches the validated local architecture.
- [ ] Confirm persistent storage locations.
- [ ] Confirm database locations.
- [ ] Confirm configuration/environment variables.
- [ ] Confirm network exposure is intentional and limited.
- [ ] Confirm required ports.
- [ ] Confirm container/service restart policy.
- [ ] Confirm logs are accessible.
- [ ] Confirm health/status monitoring is available.

### 2.2 Version and Source Verification

- [ ] Record the Git commit deployed to UnRAID.
- [ ] Confirm the deployed commit corresponds to the validated `master` state.
- [ ] Record deployment date/time.
- [ ] Record Mnemosyne version/release identifier if one exists.
- [ ] Record relevant Hermes-Agent version/configuration.
- [ ] Record relevant Ollama/model configuration.
- [ ] Record UnRAID/container versions where relevant.

### Deployment record

```text
Deployment commit:
Deployment date:
Mnemosyne version:
Hermes-Agent version:
Ollama version:
Primary model:
UnRAID version:
```

---

## 3. Basic Application Validation

- [ ] Mnemosyne starts successfully.
- [ ] Mnemosyne survives a clean restart.
- [ ] Mnemosyne survives an UnRAID/container restart.
- [ ] Browser interface loads.
- [ ] API responds.
- [ ] Health/status endpoints respond correctly.
- [ ] No unexpected startup errors appear in logs.
- [ ] No unexpected database errors appear in logs.
- [ ] No unexpected permission errors appear in logs.
- [ ] No unexpected network/connectivity errors appear in logs.

---

## 4. Browser Interface Validation

Validate the actual deployed browser interface rather than relying solely on automated tests.

- [ ] Main Mnemosyne browser interface loads.
- [ ] Profile selection works.
- [ ] Profile-specific memory views work.
- [ ] Collective knowledge views work.
- [ ] Entity/relationship views work where applicable.
- [ ] Temporal views work where applicable.
- [ ] Mental-model views work where applicable.
- [ ] Provenance/evidence views work.
- [ ] Revoked/non-eligible information is correctly governed in views.
- [ ] No raw private memory content appears where the architecture prohibits it.
- [ ] Browser labels derived knowledge appropriately.
- [ ] Browser labels evidence/provenance boundaries appropriately.
- [ ] Browser interface remains usable at the expected production dataset size.

---

## 5. Profile Isolation Validation

For every production Hermes profile included in the deployment:

- [ ] Profile-local database/storage is isolated.
- [ ] Profile A cannot directly retrieve Profile B's private memory.
- [ ] Profile B cannot directly retrieve Profile A's private memory.
- [ ] Profile-local retrieval respects the active profile.
- [ ] Profile-local writes affect only the intended profile.
- [ ] Profile-local deletion affects only the intended profile.
- [ ] Profile-specific derived knowledge remains associated with the correct destination profile.
- [ ] No unintended cross-profile memory leakage is observable.
- [ ] Logs do not expose private memory content across profile boundaries.

### Negative test

Attempt to retrieve Profile A's private memory while operating as Profile B.

**Expected:** no unauthorized private-memory access.

- [ ] PASS

---

## 6. Collective Knowledge Governance

Validate the boundary between profile-local memory and collective knowledge.

- [ ] Collective knowledge contains governed derived information only.
- [ ] Raw private memory content is not unintentionally copied into the collective store.
- [ ] Collective entries retain source profile identifiers.
- [ ] Collective entries retain source memory identifiers where required.
- [ ] Provenance is preserved.
- [ ] Evidence relationships are preserved.
- [ ] Revoked information is excluded from active retrieval/views.
- [ ] Audit history is retained where required.
- [ ] Collective knowledge cannot be used to bypass profile isolation.

---

## 7. Cross-Profile Learning Validation

Validate the complete Phase 14 pipeline:

```text
Profile-Local Memory
       ↓
Governed Collective Knowledge
       ↓
Transfer Candidate
       ↓
Authorization / Applicability / Evidence Validation
       ↓
Explicit Profile Adoption
       ↓
Profile-Specific Derived Knowledge
```

- [ ] A candidate can be identified without automatically becoming learned knowledge.
- [ ] Candidate status is distinguishable from adopted status.
- [ ] Source authorization is enforced.
- [ ] Destination authorization is enforced.
- [ ] Applicability is evaluated.
- [ ] Evidence is preserved.
- [ ] Provenance is preserved.
- [ ] Explicit adoption is required.
- [ ] No implicit cross-profile learning occurs.
- [ ] Source memory remains immutable.
- [ ] Conflicting knowledge is preserved rather than silently overwritten.
- [ ] Temporal applicability is respected.
- [ ] Revocation/rollback behavior is respected.
- [ ] Audit history is retained.

### Negative test

Identify a valid transfer candidate but do not authorize adoption.

**Expected:** the destination profile does not acquire the candidate as adopted knowledge.

- [ ] PASS

---

## 8. User Memory Review and Deletion

This section is a required production-readiness test.

The purpose is to establish that user review and deletion remain authoritative after learning and subsequent ingestion.

### 8.1 Baseline Memory

Create or identify a test memory:

```text
Test memory ID:
Source profile:
Creation date:
```

- [ ] Memory exists in the expected profile-local store.
- [ ] Memory is retrievable before deletion.
- [ ] Memory can participate in the expected governed processing.

### 8.2 Learning Before Deletion

Allow the test memory to participate in the appropriate learning/consolidation pipeline.

- [ ] Memory contributes to an observable governed result where expected.
- [ ] Result contains appropriate provenance.
- [ ] Source memory remains identifiable.
- [ ] Derived knowledge does not become indistinguishable from the original memory.

### 8.3 User Deletion

Perform the user-approved deletion/revocation operation.

- [ ] User review identifies the memory for deletion.
- [ ] Deletion/revocation is recorded.
- [ ] Original memory is no longer eligible for active retrieval.
- [ ] Deleted/revoked memory is no longer eligible for new learning.
- [ ] Appropriate derived knowledge is governed according to its dependency on the deleted source.
- [ ] Historical audit information remains available where required.

### 8.4 Post-Deletion Retrieval

- [ ] Deleted memory does not appear in normal retrieval.
- [ ] Deleted memory does not appear in active browser views.
- [ ] Deleted memory does not appear as active collective knowledge.
- [ ] Deleted memory does not appear as an active transfer candidate.
- [ ] Deleted memory does not silently contribute to newly generated derived knowledge.

---

## 9. Memory Resurrection / Re-ingestion Test

This is a mandatory production-readiness test.

The objective is to verify that deleted memories do not return merely because additional memories are subsequently added.

### Test sequence

```text
Memory A
   ↓
Learning / consolidation
   ↓
User deletes Memory A
   ↓
Verify exclusion
   ↓
Add Memory B
   ↓
Run ingestion
   ↓
Run consolidation
   ↓
Run retrieval
   ↓
Run applicable learning processes
   ↓
Verify Memory A remains excluded
```

### Test

- [ ] Create Memory A.
- [ ] Allow Memory A to participate in normal processing.
- [ ] Delete/revoke Memory A through the intended user workflow.
- [ ] Confirm Memory A is excluded.
- [ ] Add unrelated Memory B.
- [ ] Run normal ingestion.
- [ ] Run normal consolidation.
- [ ] Run normal retrieval.
- [ ] Run applicable collective-learning processing.
- [ ] Recheck Memory A.

### Required result

Memory A must not return as an active memory or become eligible again solely because Memory B was subsequently added.

- [ ] PASS

---

## 10. Deleted-Memory Provenance Test

A deleted source must not accidentally remain active merely because another derived object points to it.

### Test

```text
Memory A
   ↓
Observation
   ↓
Consolidated evidence
   ↓
Collective knowledge
   ↓
Transfer candidate
   ↓
Destination-derived knowledge
```

Then delete/revoke Memory A.

Verify each layer.

- [ ] Original memory becomes ineligible.
- [ ] Observation remains correctly governed.
- [ ] Evidence remains correctly governed.
- [ ] Collective representation is correctly governed.
- [ ] Transfer candidate is correctly governed.
- [ ] Destination-derived knowledge is correctly governed.
- [ ] No downstream object incorrectly resurrects Memory A.
- [ ] Historical audit information is retained where required.

---

## 11. Re-creation vs. Resurrection

The system must distinguish between:

### Resurrection

```text
Deleted Memory A
       ↓
System accidentally recreates Memory A
```

and:

### Explicit re-creation

```text
Memory A deleted
       ↓
User later creates genuinely new Memory C
       ↓
Memory C independently enters the system
```

- [ ] Deleted source identifiers are not silently reused for new memories.
- [ ] New memories receive independent identity/provenance.
- [ ] New information can be processed normally.
- [ ] The system does not incorrectly classify new information as the deleted source.
- [ ] Equivalent information explicitly re-entered by the user is distinguishable from automatic resurrection.

---

## 12. Derived Knowledge and Mental Models

Validate the higher-level knowledge layers introduced before Phase 14.

- [ ] Mental models remain derived rather than being presented as raw memories.
- [ ] Mental models preserve evidence/provenance.
- [ ] Mental models respect promoted/non-revoked governance.
- [ ] Mental models do not expose private memory content.
- [ ] Revoked source evidence is handled correctly.
- [ ] Cross-profile transfer does not bypass mental-model governance.
- [ ] Browser presentation clearly distinguishes derived knowledge from observed memory.

---

## 13. Temporal Governance Validation

- [ ] Temporal evidence remains correctly associated with its source.
- [ ] Temporal applicability is respected during transfer.
- [ ] Historical information is not incorrectly presented as current.
- [ ] Revoked information is not treated as currently eligible solely because it has historical temporal evidence.
- [ ] Temporal views respect profile and governance boundaries.

---

## 14. Restart and Persistence Validation

Perform controlled restarts.

- [ ] Stop Mnemosyne cleanly.
- [ ] Restart Mnemosyne.
- [ ] Verify profile-local memories remain intact.
- [ ] Verify collective knowledge remains intact.
- [ ] Verify provenance remains intact.
- [ ] Verify derived knowledge remains intact.
- [ ] Verify deletion/revocation state remains intact.
- [ ] Verify deleted memories do not return after restart.
- [ ] Verify configuration remains correct.
- [ ] Verify browser/API behavior after restart.

### Critical test

Delete Memory A → restart container → verify Memory A remains excluded.

- [ ] PASS

---

## 15. Backup and Recovery

Before production declaration:

- [ ] Identify all persistent Mnemosyne data.
- [ ] Identify all databases.
- [ ] Identify configuration requiring backup.
- [ ] Confirm backup destination.
- [ ] Perform a backup.
- [ ] Verify backup contents.
- [ ] Test restoration in a controlled environment.
- [ ] Verify restored databases open correctly.
- [ ] Verify provenance survives restoration.
- [ ] Verify deletion/revocation state survives restoration.
- [ ] Verify collective knowledge survives restoration.
- [ ] Verify profile isolation survives restoration.
- [ ] Document recovery procedure.

---

## 16. Security and Access Validation

- [ ] Confirm only intended interfaces are exposed.
- [ ] Confirm UnRAID network access rules.
- [ ] Confirm container permissions.
- [ ] Confirm database files are not unintentionally exposed.
- [ ] Confirm logs do not expose private memory content.
- [ ] Confirm browser endpoints enforce intended access boundaries.
- [ ] Confirm profile selection cannot be manipulated to bypass authorization.
- [ ] Confirm collective endpoints cannot expose private source content.

---

## 17. Hermes-Agent Integration Validation

Validate the deployed Hermes-Agent integration.

- [ ] Hermes-Agent can communicate with Mnemosyne as designed.
- [ ] Correct profile identity is preserved.
- [ ] Profile isolation is maintained.
- [ ] Memory operations use the intended governed interface.
- [ ] Collective knowledge is accessed only through permitted paths.
- [ ] No unintended raw private-memory access occurs.
- [ ] Restart/reconnect behavior works.
- [ ] Errors are handled without corrupting memory state.

---

## 18. Future Hermes-Agent Skill Review

This is a future extension and not a prerequisite for declaring the current Phase 14 implementation complete, unless the roadmap later incorporates it into the production definition.

A natural next capability is:

```text
Collective Knowledge
       ↓
Hermes-Agent Skill Review
       ↓
Evidence / Applicability Analysis
       ↓
Skill Improvement Proposal
       ↓
Validation
       ↓
Explicit Adoption
```

The future system should be able to:

- [ ] Inspect the current Hermes-Agent skill inventory.
- [ ] Identify skills relevant to collective knowledge.
- [ ] Compare current skills against validated collective knowledge.
- [ ] Identify potential improvements to existing skills.
- [ ] Identify potential new skills.
- [ ] Preserve evidence supporting each proposal.
- [ ] Require explicit validation before modifying a skill.
- [ ] Require explicit adoption before a skill changes.
- [ ] Preserve provenance for skill changes.
- [ ] Preserve audit history.
- [ ] Ensure collective knowledge cannot silently modify agent capabilities.

### Architectural principle

Knowledge should inform skill proposals; knowledge should not silently mutate agent capabilities.

---

## 19. Visual Documentation / Demonstration

After the deployed system is stable, capture screenshots for the project-level documentation.

**Primary document:**

`docs/PROJECT_DATA_SCIENCE_DATA_ENGINEERING_POSITIONING.md`

**Recommended demonstration sequence:**

### 19.1 Live Deployment

- [ ] Capture the deployed Mnemosyne browser interface.
- [ ] Capture the production UnRAID/Hermes-Agent architecture where useful.
- [ ] Record the deployment context.

### 19.2 Before Learning

- [ ] Capture profile-local memories before cross-profile learning.
- [ ] Clearly identify which profile owns each memory.
- [ ] Show the initial state.

### 19.3 Learning / Transfer

- [ ] Capture the relevant collective/transfer view.
- [ ] Show evidence/provenance where appropriate.
- [ ] Demonstrate that candidate ≠ adoption.

### 19.4 After Learning

- [ ] Capture the destination profile after explicit adoption.
- [ ] Show the resulting derived knowledge.
- [ ] Show provenance/evidence where appropriate.
- [ ] Demonstrate what changed.

### 19.5 Deletion Demonstration

Where practical:

- [ ] Capture a memory before deletion.
- [ ] Capture the user review/deletion action.
- [ ] Capture the post-deletion state.
- [ ] Add a new memory.
- [ ] Capture the post-ingestion state.
- [ ] Demonstrate that the deleted memory does not return.

### Visual documentation principle

Use screenshots to demonstrate system behavior, not merely system appearance.

---

## 20. Performance and Stability

- [ ] Measure normal response times.
- [ ] Test browser responsiveness.
- [ ] Test retrieval at representative dataset size.
- [ ] Test collective retrieval at representative size.
- [ ] Test graph/temporal views at representative size.
- [ ] Test consolidation at representative workload.
- [ ] Monitor CPU usage.
- [ ] Monitor memory usage.
- [ ] Monitor disk usage.
- [ ] Monitor database growth.
- [ ] Monitor container stability.
- [ ] Confirm no unexplained resource growth during normal operation.

---

## 21. Regression Testing

Run the complete automated test suite against the final deployment code before production declaration.

- [ ] Unit tests pass.
- [ ] Integration tests pass.
- [ ] API tests pass.
- [ ] Browser/interface tests pass.
- [ ] Governance tests pass.
- [ ] Cross-profile tests pass.
- [ ] Deletion/revocation tests pass.
- [ ] Re-ingestion/resurrection tests pass.
- [ ] Persistence/restart tests pass where automated.
- [ ] No unexpected warnings/errors remain.

### Final test result

```text
Tests passed:
Tests skipped:
Warnings:
Failures:
Commit:
Date:
```

---

## 22. Production Readiness Sign-Off

### Required Gates

| Area | Status | Evidence |
|---|---|---|
| Deployment | ☐ | |
| Application startup | ☐ | |
| Browser interface | ☐ | |
| Profile isolation | ☐ | |
| Collective governance | ☐ | |
| Cross-profile learning | ☐ | |
| User deletion | ☐ | |
| Re-ingestion resistance | ☐ | |
| Derived knowledge | ☐ | |
| Temporal governance | ☐ | |
| Restart persistence | ☐ | |
| Backup | ☐ | |
| Recovery | ☐ | |
| Security/access | ☐ | |
| Hermes-Agent integration | ☐ | |
| Performance/stability | ☐ | |
| Automated regression | ☐ | |
| Visual documentation | ☐ | |

### Exceptions

Document any item that is not complete but has been explicitly accepted:

```text
Item:
Reason:
Risk:
Mitigation:
Accepted by:
Date:
```

---

## 23. Final Production Declaration

Mnemosyne may be declared production-ready on UnRAID only after:

- [ ] all required validation gates pass;
- [ ] all critical deletion/revocation tests pass;
- [ ] the memory resurrection/re-ingestion test passes;
- [ ] profile isolation passes;
- [ ] collective governance passes;
- [ ] cross-profile learning passes;
- [ ] persistence and restart tests pass;
- [ ] backup and recovery have been demonstrated;
- [ ] security/access validation passes;
- [ ] automated regression passes;
- [ ] all exceptions are explicitly documented and accepted.

### Final declaration

```text
Mnemosyne UnRAID Production Readiness:

Deployment commit:

Validation completed:

Outstanding exceptions:

Final decision:

Date:
```

---

## 24. Guiding Principle

The production system should demonstrate not only that Mnemosyne can learn, but that it can also respect what the user tells it not to retain or use.

The critical lifecycle is:

```text
Observe
   ↓
Govern
   ↓
Learn
   ↓
Review
   ↓
Adopt
   ↓
Revoke/Delete
   ↓
Continue Operating
   ↓
Do Not Resurrect
```

A production-ready memory system must demonstrate both sides of the lifecycle:

**controlled learning and controlled forgetting.**