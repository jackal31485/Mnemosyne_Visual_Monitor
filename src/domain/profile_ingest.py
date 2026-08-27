"""
A **bridge** that discovers existing Hermes‑profile-local Mnemosyne databases and turns every memory
into a *proposed* entry in the application collective store.

The module follows the established life‑cycle:

1. Discover profiles under ``~/\.hermes/profiles`` where the path
   ``<profile>/mnemosyne/data/mnemosyne.db`` exists.
2. Open those databases **read‑only** (URI mode ``mode=ro``) – never write or alter.
3. Infer a *memory* table by inspecting ``PRAGMA table_info``.  The logic
   picks the first table that contains a column called ``id`` or
   ``memory_id`` and assumes it stores the raw content in some string
yielding column (``content``, ``text`` or similar). If no suitable table is
found an informative error is logged.
4. For each row, create a reference entry via :class:`ProposalManager`
   – this guarantees that all privacy/sanitisation rules are applied by the
   existing pipeline when the proposal is later validated/promoted.
5. During ``--dry‑run`` the function returns a summary instead of
   creating proposals.

The module deliberately *does not* import any private helper modules or
modify the schema; it only uses the public DAO/proposal interfaces so that it could in
the future be wired into the REST API as POST ``/api/ingest``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Iterable, List
import sqlite3

from .proposal_lifecycle import ProposalManager
from .collective import CollectiveDAO

__all__ = [
    "discover_profile_paths",
    "infer_memory_table",
    "extract_memories",
    "ingest_profiles",
]

# ---------------------------------------------------------------------------
# Discovery utilities – pure data‑only functions so they are easily unit‑testable.
# ---------------------------------------------------------------------------

def discover_profile_paths(base: Path | str = os.path.expanduser("~/.hermes/profiles")) -> List[Path]:
    """Yield a ``Path`` to every profile that bundles a Mnemosyne DB.

    The function checks for ``<profile>/mnemosyne/data/mnemosyne.db`` and skips any
    directories lacking that file. It returns an **ordered list** where each
    element is the *profile directory* (not the DB itself).
    """
    base = Path(base).expanduser()
    profiles: List[Path] = []
    for p in base.iterdir():
        if not p.is_dir():
            continue
        db_path = p / "mnemosyne" / "data" / "mnemosyne.db"
        if db_path.exists() and db_path.is_file():
            profiles.append(p)
    return profiles

# ---------------------------------------------------------------------------
# Schema introspection – minimal but tolerant of unknown layouts.
# ---------------------------------------------------------------------------

def infer_memory_table(conn: sqlite3.Connection) -> str | None:
    """Return the first table that looks like a memory repository.

    The heuristic is simply:

    * Has a column named ``id`` or ``memory_id`` (case‑insensitive).
    * Expects at least one string/text column for content.

    If no such table exists ``None`` is returned so the caller can log an error.
    """
    tables: List[tuple[str]] = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()

    for (tbl,) in tables:
        # fetch column metadata
        cols = conn.execute(f"PRAGMA table_info('{tbl}')").fetchall()
        col_names = [c[1].lower() for c in cols]

        has_id_col = any(c in col_names for c in ("id", "memory_id",))
        has_content_col = any(
            isinstance(c, str)
            and c.lower() in ("content", "text", "data")
            for c in col_names
        )
        if has_id_col and has_content_col:
            return tbl
    return None

# ---------------------------------------------------------------------------
# Extraction helper – yields rows as dicts.
# ---------------------------------------------------------------------------

def extract_memories(db_path: Path) -> Iterable[Dict[str, str]]:
    """Yield every memory row from a read‑only Mnemosyne DB.

    The function constructs a URI ``file:<abs>?mode=ro`` and returns rows as
    dictionaries with keys matching the DB's columns (so we can access the raw
    ID/value). Calling code is responsible for filtering out unnecessary columns.
    """
    uri = f'file:{db_path.as_posix()}?mode=ro'
    conn = sqlite3.connect(uri, uri=True)
    try:
        tbl_name = infer_memory_table(conn)
        if tbl_name is None:
            raise RuntimeError(f"No suitable memory table found in {db_path}")
        cursor = conn.execute(f"SELECT * FROM '{tbl_name}'")
        # ``cursor.description`` contains column metadata after execution.
        columns = [col[0] for col in cursor.description]
        for row in cursor:
            yield dict(zip(columns, row))
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# Orchestration – performs the actual ingestion.
# ---------------------------------------------------------------------------

def ingest_profiles(dry_run: bool = False) -> Dict[str, int]:
    """Discover profiles and propose every memory entry.

    Parameters
    ----------
    dry_run:
        If ``True`` no changes are persisted; instead a dictionary mapping
        profile names to the number of memories that would have been proposed is
        returned.

    Returns
    -------
    Dict[str, int]
        Mapping from *profile* (directory name) to count of proposals made or
        discovered.
    """
    profiles = discover_profile_paths()
    dao = CollectiveDAO()  # uses the project level collective.db
    pm = ProposalManager(dao)
    summary: Dict[str, int] = {}
    for profile_dir in profiles:
        db_path = profile_dir / "mnemosyne" / "data" / "mnemosyne.db"
        try:
            mem_rows = list(extract_memories(db_path))
        except Exception as exc:  # pragma: no cover
            print(f"[ingest] failed to read {db_path}: {exc}")
            continue

        count = len(mem_rows)
        if dry_run:
            summary[profile_dir.name] = count
            continue

        for mem in mem_rows:
            # The legacy schema may use 'id' or 'memory_id'.  We normalise to a string.
            origin_id = str(mem.get("id") or mem.get("memory_id"))
            if not origin_id:
                continue  # skip malformed rows
            # Avoid duplicate proposals – the DAO contains idempotency check via get_by_source.
            existing = dao.get_by_source(profile_dir.name, origin_id)
            if existing:
                continue
            pm.propose(source_profile=profile_dir.name, origin_memory_id=origin_id)
        summary[profile_dir.name] = count
    return summary

# ---------------------------------------------------------------------------
# CLI entry point – used in `scripts/ingest_profiles.py`.
# ---------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover - manual invocation only
    import argparse, json

    parser = argparse.ArgumentParser(description="Ingest Mnemosyne memories from live Hermes profiles")
    parser.add_argument("--dry-raw", action="store_true", dest="dry_run", help="Perform a dry run – report counts but do not write to the collective db.")
    args = parser.parse_args()

    result = ingest_profiles(dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
