
"""
Runtime data façade combining Hermes and Mnemosyne discovery.
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import discovery.hermes_runtime as hermes_mod
import discovery.mnemosyne_inspector as inspector_mod

# Public types re‑exported for visibility and to avoid circular imports
from discovery.hermes_runtime import HermesRuntimeSnapshot
from discovery.mnemosyne_inspector import SchemaSnapshot

@dataclass
class RuntimeData:
    """Aggregate snapshot of Hermes runtime and Mnemosyne schema."""
    hermes: HermesRuntimeSnapshot
    mnemosyne_schema: Optional[SchemaSnapshot] = None


def get_runtime_data(db_path: Optional[Path] = None) -> RuntimeData:
    """Return a :class:`RuntimeData` instance.

    Parameters
    ----------
    db_path:
        Path to a SQLite Mnemosyne database. If ``None`` the schema field will be
        ``None`` and no inspection takes place.
    """
    hermes = hermes_mod.get_hermes_runtime_snapshot()
    if db_path is None:
        return RuntimeData(hermes)
    # delegate to inspector; it performs read‑only checks.
    schema = inspector_mod.inspect_sqlite_database(db_path, enable_vectors=True)
    return RuntimeData(hermes, schema)
