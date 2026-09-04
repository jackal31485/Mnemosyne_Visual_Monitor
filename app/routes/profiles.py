from fastapi import APIRouter
import pathlib
from typing import NamedTuple

router = APIRouter()

def get_profiles():
    """Return a list of discovered profiles.

    Each element is a dataclass with attributes ``id``, ``name`` and ``memory_count``.
    The tuple is JSON‑serialisable for FastAPI routes.
    """
    from src.domain.profile_ingest import discover_profile_paths, extract_memories

    class Profile(NamedTuple):
        id: str
        name: str
        memory_count: int

    profiles: list[Profile] = []

    for p in sorted(discover_profile_paths()):
        profile_id = p.name
        # The repository always stores the database under <profile>/mnemosyne/data/mnemosyne.db.
        db_path = p / "mnemosyne" / "data" / "mnemosyne.db"
        if not db_path.is_file():
            continue
        count = sum(1 for _ in extract_memories(db_path))
        profiles.append(Profile(profile_id, profile_id, count))
    return profiles

@router.get("/profiles/")
async def _get_profiles():  # FastAPI route
    return get_profiles()

# ------------------------------------------------------------------
# Backward‑compatibility helpers used by legacy unit tests.
# ------------------------------------------------------------------

def _discover_profile(profile_dir: str | pathlib.Path) -> pathlib.Path | None:
    """Return the path to an existing Mnemosyne DB or ``None``.

    This helper is used by legacy unit tests and historical clients. It intentionally
    returns ``None`` instead of raising on malformed input, keeping backwards
    compatibility while still providing clear intent for callers.

    Parameters
    ----------
    path: str | pathlib.Path
        File system location to probe.

    Returns
    -------
    bool | None
        ``True`` if a profile database is present; otherwise ``None``.
    """
    try:
        p = pathlib.Path(profile_dir)
        db_path = p / "mnemosyne" / "data" / "mnemosyne.db"
        if db_path.is_file():
            return db_path
        return None
    except Exception:  # pragma: no cover - defensive fallback
        return None


@router.get("/api/collective/profiles")
async def _get_collective_profiles():
    """
    Return profiles represented by the CURRENT COLLECTIVE.

    This is intentionally different from /profiles/.
    /profiles/ describes local Hermes source profiles.
    This endpoint describes collective.db.

    Therefore Nuke -> [] and Rebuild -> populated profiles.
    """
    from src.domain.collective import CollectiveDAO

    project_root = pathlib.Path(__file__).resolve().parents[2]
    collective_db = project_root / "data" / "collective.db"

    dao = CollectiveDAO(collective_db)

    try:
        dao.ensure_schema()

        rows = dao.conn.execute(
            """
            SELECT
                source_profile,
                COUNT(*) AS memory_count
            FROM collective_entries
            WHERE is_revoked = 0
              AND is_promoted = 1
            GROUP BY source_profile
            ORDER BY source_profile
            """
        ).fetchall()

        return [
            {
                "id": row["source_profile"],
                "name": row["source_profile"],
                "memory_count": int(
                    row["memory_count"] or 0
                ),
            }
            for row in rows
        ]

    finally:
        dao.close()
