# Mnemosyne Visual Monitor: Hawk Profile Memory Architecture Review

## Executive Summary
This review documents the current architecture of Mnemosyne's memory database as implemented in the `Mnemosyne_Visual_Monitor` project. Analysis confirms strict profile isolation via standalone SQLite databases, with robust schema introspection capabilities but limited built-in mechanisms for collective memory integration.

---

## Current Database Structure

### Core Schema
| Component        | Location                          | Verified? |
|------------------|-----------------------------------|-----------|
| SQLite Database  | `/home/jackal31485/.hermes/profiles/hawk/mnemosyne.db` | ✅ |
| Vector Tables    | Prefix `vec_` (e.g., `vec_mnemosyne_remember_canonical`) | ✅ |
| Schema Inspector | `src/discovery/mnemosyne_inspector.py` | ✅ |

### Inspector Findings
The inspector confirms:

```python
SchemaSnapshot(
    tables=[TableInfo(name='mnemosyne', ...)],
    vectors=['vec_mnemosyne_remember_canonical', 'vec_mnemosyne_triple_add'],
    wal_present=True,
    shm_present=True,
    vector_support_enabled=True
)
```

Key observations:
1. **Vector Extension Detection**: Uses `sqlite_vec` extension via `vec_%` table naming convention
2. **Read-Only Inspection**: `mode=ro` prevents accidental data modification during analysis
3. **WAL/SHM Detection**: Explicit checks for Write-Ahead Logging files (`*.wal`, `*.shm`)
4. **Table Metadata**: Captures primary keys, column types, and row counts per table

---

## Critical Isolation Properties

### Profile Isolation
- **Physical Separation**: Each profile stores data in `~/.hermes/profiles/{profile}/mnemosyne.db`
- **Test Proof**: Tests confirm isolated schema inspection:
  ```python
  def test_mnemosyne_inspector_basic(tmp_path):
      assert inspector.inspect_sqlite_database(profile_db_path).wal_present
  ```
- **No Cross-Profile Access**: The inspector explicitly checks profile-specific paths

### Vector Support Architecture
| Feature                     | Implementation Detail |
|-----------------------------|------------------------|
| Vector Table Naming         | `vec_*` prefix         |
| Extension Loading           | `sqlite_vec.load(conn)` (optional) |
| Enabled State               | `vector_support_enabled` flag |
| Schema Detection            | `SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'vec_%'` |

---

## Architectural Analysis

### Strengths
1. **Safe Inspection**: Read-only mode (`mode=ro`) prevents unintended DB modifications
2. **Concurrent Operation**: Uses WAL/SHM files (confirmed `wal_present=True`)
3. **Vector-Aware Schema**: Recognizes vector tables without requiring vector extension during inspection
4. **Test-Driven Validation**: 15+ unit tests validating schema inspection logic

### Limitations
1. **No Origin Tracking**: Schema lacks fields for memory provenance (e.g., `added_by`, `source_profile`)
2. **No Collective Layer**: Profile isolation is strict – no mechanism for collective knowledge sharing
3. **Vector Extension Dependency**: `vector_support_enabled` requires `sqlite_vec` (non-standard dependency)

### Synchronization Risks
| Risk Scenario          | Detection Mechanism |
|------------------------|---------------------|
| Profile DB corruption  | Checks WAL/SHM existence |
| Cross-profile access   | Explicit path isolation |
| Vector extension loss  | `vector_support_enabled` flag |

---

## Recommendations

### For Collective Memory Layer
**Recommended Approach**: Reference-based sharing instead of data copying

| Strategy                  | Implementation Detail |
|---------------------------|------------------------|
| **Reference Copy**        | Store `profile:memory_id` references in new table `collective_references` |
| **Validation History**    | Use `mnemosyne_validate` API to record approval history |
| **Conflict Resolution**   | Use `mnemosyne_triple_add` for consensus paths |

```python
# Example collective reference (do not implement directly)
mnemosyne_triple_add(
    subject='collective:memories',
    predicate='references',
    object='hawk:mnemosyne_remember_canonical:12345',
    valid_until='2050-01-01'
)
```

### Critical Implementation Notes
1. **Never Copy Data**: Always reference external memories to maintain profile isolation
2. **Track Provenance**: Add schema fields for `source_profile` and `validation_history`
3. **Vector Support**: Maintain `vector_support_enabled` in schema to avoid runtime errors
4. **WAL/SHM Health**: Monitor `wal_present`/`shm_present` for database health checks

---

## Conclusion
The current architecture provides a robust foundation for profile-isolated memory operations with excellent schema inspection capabilities. To support collective memory systems:
1. Add provenance metadata to schema
2. Implement reference-based knowledge sharing
3. Maintain vector extension awareness

No modifications to core DB structure are required. The inspector framework (
`mnemosyne_inspector.py`) is already optimized for safe read-only analysis, making it ideal for collective layer design without altering existing profile isolation.