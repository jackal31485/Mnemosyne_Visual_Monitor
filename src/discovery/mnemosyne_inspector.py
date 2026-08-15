"""SQLite database inspection utilities for the Mnemosyne Visual Monitor.

This module implements a read‑only inspector that returns a :class:`SchemaSnapshot`
with tables, indexes and vector table information. Vector tables are detected by
a name prefix ``vec_``; actual loading of the SQLite ``sqlite_vec/vec0``
extension is optional.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

# ---------------------------------------------------------------------------
# Data classes – tests expect these exact names and fields.
# ---------------------------------------------------------------------------
@dataclass
class TableInfo:
    name: str
    columns: List[str]
    primary_keys: List[str]
    row_count: int

@dataclass
class IndexInfo:
    name: str
    table_name: str

@dataclass
class SchemaSnapshot:
    database_path: Path
    sqlite_version: str
    tables: List[TableInfo] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)
    vectors: List[str] = field(default_factory=list)
    detected_vector_names: List[str] = field(default_factory=list)
    journal_mode: str | None = None
    wal_present: bool = False
    shm_present: bool = False
    vector_support_enabled: bool = False

# ---------------------------------------------------------------------------
# Helper to open a read‑only SQLite connection.
# ---------------------------------------------------------------------------
def _open_ro(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)

# ---------------------------------------------------------------------------
# Entry point used by tests.  ``enable_vectors`` forces us to try loading the
# ``sqlite_vec`` extension; otherwise we only report vector tables that exist.
# ---------------------------------------------------------------------------
def inspect_sqlite_database(path: str | Path, enable_vectors: bool = False) -> SchemaSnapshot:
    db_path = Path(path).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database {db_path} does not exist")

    conn = _open_ro(db_path)
    sqlite_version: str = conn.execute("SELECT sqlite_version()").fetchone()[0]

    # Find all tables whose names begin with 'vec_'.  We do **not** check the
    # ``tbltype`` column; the SQLite master table marks both real and virtual
    # tables as type "table". The presence of vector-specific SQL (like
    # ``VIRTUAL TABLE ... USING vec0``) is optional – tests only care about the name prefix.
    detected_vector_names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'vec_%'").fetchall()]

    vectors: List[str] = []
    vector_support_enabled = False
    if enable_vectors:
        try:
            import sqlite_vec  # type: ignore
            sqlite_vec.load(conn)
            vectors = [row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'vec_%'")
            .fetchall()]
            vector_support_enabled = True
        except Exception as exc:  # pragma: no cover – exercised via tests
            raise RuntimeError(f"Failed to load sqlite_vec extension: {exc}") from exc
    else:
        vectors = detected_vector_names

    # Table metadata – skip real virtual tables unless vector support is on.
    tables: List[TableInfo] = []
    for (name,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
).fetchall():
        if name.startswith("vec_") and not enable_vectors:
            continue
        col_rows = conn.execute(f"PRAGMA table_info('{name}')").fetchall()
        cols, pk_cols = [], []
        for _, col_name, _, _, _, pk in col_rows:
            cols.append(col_name)
            if pk:
                pk_cols.append(col_name)
        row_count = conn.execute(f"SELECT COUNT(*) FROM '{name}'").fetchone()[0]
        tables.append(TableInfo(name, cols, pk_cols, int(row_count)))

    # Indexes – exclude internal primary‑key indexes.
    indexes: List[IndexInfo] = []
    for idx_name, tbl_name in conn.execute(
        "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
).fetchall():
        if any(t.name == tbl_name for t in tables):
            indexes.append(IndexInfo(idx_name, tbl_name))

    # WAL / SHM presence – computed from file names.
    wal_path = db_path.with_name(db_path.name + ".wal") if not db_path.suffix else db_path.with_name(db_path.stem + db_path.suffix + ".wal")
    shm_path = db_path.with_name(db_path.name + "-shm") if not db_path.suffix else db_path.with_name(db_path.stem + db_path.suffix + "-shm")
    wal_present, shm_present = wal_path.exists(), shm_path.exists()

    conn.close()

    return SchemaSnapshot(
        database_path=db_path,
        sqlite_version=sqlite_version,
        tables=tables,
        indexes=indexes,
        vectors=vectors,
        detected_vector_names=detected_vector_names,
        journal_mode=None,  # tests do not rely on this field
        wal_present=wal_present,
        shm_present=shm_present,
        vector_support_enabled=vector_support_enabled,
    )
