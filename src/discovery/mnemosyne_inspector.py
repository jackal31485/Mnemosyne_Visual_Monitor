from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import sqlite3


class TableInfo:
    def __init__(self, name: str, columns: List[str], primary_key_columns: List[str], row_count: int):
        self.name = name
        self.columns = columns
        self.primary_key_columns = primary_key_columns
        self.row_count = row_count


class IndexInfo:
    def __init__(self, name: str, table_name: str):
        self.name = name
        self.table_name = table_name


class SchemaSnapshot:
    def __init__(
        self,
        database_path: Path,
        sqlite_version: str,
        tables: List[TableInfo],
        indexes: List[IndexInfo],
        vectors: List[str],
        detected_vector_names: List[str],
        journal_mode: Optional[int],
        wal_present: bool,
        shm_present: bool,
        vector_support_enabled: bool,
    ):
        self.database_path = database_path
        self.sqlite_version = sqlite_version
        self.tables = tables
        self.indexes = indexes
        self.vectors = vectors
        self.detected_vector_names = detected_vector_names
        self.journal_mode = journal_mode
        self.wal_present = wal_present
        self.shm_present = shm_present
        self.vector_support_enabled = vector_support_enabled


def _open_ro(path: Path):
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def inspect_sqlite_database(path: str | Path, enable_vectors: bool = True) -> SchemaSnapshot:
    db_path = Path(path).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Database {db_path} does not exist")

    conn = _open_ro(db_path)
    sqlite_version: str = conn.execute("SELECT sqlite_version()").fetchone()[0]

    # Detect vector tables by name prefix.
    detected_vector_names = [r[0]
                            for r in conn.execute(
                                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'vec_%'"
                            ).fetchall()]

    vectors: List[str] = []
    vector_support_enabled = False
    if enable_vectors:
        try:
            import sqlite_vec  # type: ignore
        except Exception as exc:
            raise RuntimeError("Failed to load sqlite_vec") from exc
        if not hasattr(sqlite3, "enable_load_extension"):
            raise RuntimeError("Failed to load sqlite_vec")
        try:
            sqlite_vec.load(conn)
            vectors = [row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'vec_%'"
                            ).fetchall()]
            vector_support_enabled = True
        except Exception as exc:
            raise RuntimeError("Failed to load sqlite_vec") from exc
    else:
        vectors = detected_vector_names

    # Table metadata.
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

    indexes: List[IndexInfo] = []
    for idx_name, tbl_name in conn.execute(
        "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
    ).fetchall():
        if any(t.name == tbl_name for t in tables):
            indexes.append(IndexInfo(idx_name, tbl_name))

    wal_path = db_path.with_name(f"{db_path.name}.wal") if db_path.suffix else db_path.with_name(f"{db_path.stem}.wal")
    shm_path = db_path.with_name(f"{db_path.name}-shm") if db_path.suffix else db_path.with_name(f"{db_path.stem}-shm")
    wal_present, shm_present = wal_path.exists(), shm_path.exists()

    conn.close()
    return SchemaSnapshot(
        database_path=db_path,
        sqlite_version=sqlite_version,
        tables=tables,
        indexes=indexes,
        vectors=vectors,
        detected_vector_names=detected_vector_names,
        journal_mode=None,
        wal_present=wal_present,
        shm_present=shm_present,
        vector_support_enabled=vector_support_enabled,
    )
