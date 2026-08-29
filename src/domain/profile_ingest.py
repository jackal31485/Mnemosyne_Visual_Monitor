from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Iterator

from src.domain.collective import CollectiveDAO
from src.domain.proposal_lifecycle import ProposalManager


DEFAULT_PROFILES_ROOT = (
    Path.home() / ".hermes" / "profiles"
)


def discover_profile_paths(
    base: Path | str | None = None,
) -> list[Path]:
    root = Path(base or DEFAULT_PROFILES_ROOT).expanduser()

    if not root.is_dir():
        return []

    profiles: list[Path] = []

    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue

        db_path = (
            path
            / "mnemosyne"
            / "data"
            / "mnemosyne.db"
        )

        if db_path.is_file():
            profiles.append(path)

    return profiles


def infer_memory_table(conn: sqlite3.Connection) -> str:
    tables = {
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()
    }

    preferred = [
        "working_memory",
        "memories",
        "memory",
    ]

    for table in preferred:
        if table in tables:
            columns = {
                row[1]
                for row in conn.execute(
                    f"PRAGMA table_info({table})"
                ).fetchall()
            }

            if "id" in columns and "content" in columns:
                return table

    raise ValueError(
        "Could not find a supported Mnemosyne memory table "
        "containing id and content columns."
    )


def extract_memories(
    db_path: Path | str,
) -> Iterator[dict[str, str]]:
    db_path = Path(db_path)

    uri = f"file:{db_path}?mode=ro"

    conn = sqlite3.connect(
        uri,
        uri=True,
    )
    conn.row_factory = sqlite3.Row

    try:
        table = infer_memory_table(conn)

        rows = conn.execute(
            f"""
            SELECT id, content
            FROM {table}
            WHERE content IS NOT NULL
            ORDER BY id
            """
        )

        for row in rows:
            content = row["content"]

            if not isinstance(content, str):
                continue

            yield {
                "id": str(row["id"]),
                "content": content,
            }

    finally:
        conn.close()


def normalize_content(content: str) -> str:
    """
    Normalize content only for exact-duplicate detection.

    The original source content is never modified.
    """
    return " ".join(content.split()).strip()


def content_hash(content: str) -> str:
    normalized = normalize_content(content)

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


def ingest_profiles(
    dry_run: bool = False,
) -> dict[str, int]:
    """
    Discover Hermes profiles and ingest source-memory references.

    Exact duplicate content is collapsed into one collective entry.

    The collective entry retains the first source reference while
    duplicate source references are returned through the ingestion
    accounting. Source databases are opened read-only.
    """
    profiles = discover_profile_paths()

    counts: dict[str, int] = {}

    dao = CollectiveDAO()
    dao.ensure_schema()

    manager = ProposalManager(dao)

    try:
        seen_hashes: dict[str, tuple[str, str]] = {}

        for profile_path in profiles:
            profile = profile_path.name

            db_path = (
                profile_path
                / "mnemosyne"
                / "data"
                / "mnemosyne.db"
            )

            discovered = 0

            for memory in extract_memories(db_path):
                discovered += 1

                memory_id = memory["id"]
                content = memory["content"]

                digest = content_hash(content)

                if digest in seen_hashes:
                    continue

                seen_hashes[digest] = (
                    profile,
                    memory_id,
                )

                if dry_run:
                    continue

                existing = dao.get_by_source(
                    profile,
                    memory_id,
                )

                if existing is None:
                    manager.propose(
                        profile,
                        memory_id,
                    )

            counts[profile] = discovered

    finally:
        dao.close()

    return counts


def deduplicate_existing_collective(
    dao: CollectiveDAO,
    profiles_root: Path | str | None = None,
) -> dict[str, int]:
    """
    Remove exact duplicate collective entries.

    This operates only on collective.db.

    The first entry for a normalized content hash is retained.
    Duplicate entries are revoked rather than physically deleted,
    preserving their historical/provenance records.
    """
    root = Path(
        profiles_root or DEFAULT_PROFILES_ROOT
    ).expanduser()

    rows = dao.conn.execute(
        """
        SELECT
            id,
            source_profile,
            origin_memory_id,
            is_revoked
        FROM collective_entries
        ORDER BY id
        """
    ).fetchall()

    seen: dict[str, int] = {}
    duplicates = 0

    for row in rows:
        entry_id = int(row["id"])

        if row["is_revoked"]:
            continue

        profile = row["source_profile"]
        memory_id = row["origin_memory_id"]

        db_path = (
            root
            / profile
            / "mnemosyne"
            / "data"
            / "mnemosyne.db"
        )

        try:
            memories = extract_memories(db_path)

            content = None

            for memory in memories:
                if memory["id"] == memory_id:
                    content = memory["content"]
                    break

            if content is None:
                continue

        except (OSError, sqlite3.Error, ValueError):
            continue

        digest = content_hash(content)

        if digest not in seen:
            seen[digest] = entry_id
            continue

        dao.revoke_entry(
            entry_id,
            f"Exact duplicate of collective entry {seen[digest]}",
        )

        duplicates += 1

    return {
        "duplicates_revoked": duplicates,
        "unique_content": len(seen),
    }
