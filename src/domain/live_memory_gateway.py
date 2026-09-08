"""Read-only gateway to live Hermes/Mnemosyne profile databases."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class LiveMemoryGateway:
    """Retrieve memory content from live Hermes profile databases.

    Source Mnemosyne databases are opened read-only. No source database is
    modified by this gateway.
    """

    def __init__(
        self,
        profiles_root: Path | str | None = None,
    ) -> None:
        self.profiles_root = Path(
            profiles_root or Path.home() / ".hermes" / "profiles"
        ).expanduser().resolve()

    def _resolve_profile_database(self, profile: str) -> Path:
        """Resolve a local or distributed profile identity to its database."""

        if not isinstance(profile, str) or not profile:
            raise KeyError("profile identity cannot be empty")

        profile_name = profile.rsplit(":", 1)[-1]

        if not profile_name:
            raise KeyError(
                f"invalid profile identity: {profile}"
            )

        db_path = (
            self.profiles_root
            / profile_name
            / "mnemosyne"
            / "data"
            / "mnemosyne.db"
        )

        if not db_path.is_file():
            raise KeyError(
                f"Mnemosyne database not found for profile {profile}: {db_path}"
            )

        return db_path

    def get_memory_metadata(
        self,
        profile: str,
        memory_id: str,
    ) -> dict[str, object]:
        """Retrieve source-memory date metadata read-only.

        Source databases are never modified.
        """
        db_path = self._resolve_profile_database(profile)

        uri = f"file:{db_path}?mode=ro"

        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row

        try:
            row = conn.execute(
                """
                SELECT
                    event_date,
                    event_date_precision,
                    timestamp,
                    created_at
                FROM working_memory
                WHERE id = ?
                LIMIT 1
                """,
                (memory_id,),
            ).fetchone()

            if row is None:
                raise KeyError(
                    f"Memory {memory_id} not found for profile {profile}"
                )

            return {
                "event_date": row["event_date"],
                "event_date_precision": row["event_date_precision"],
                "timestamp": row["timestamp"],
                "created_at": row["created_at"],
            }

        finally:
            conn.close()


    def get_memory(self, profile: str, memory_id: str) -> str:
        db_path = self._resolve_profile_database(profile)

        uri = f"file:{db_path}?mode=ro"

        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row

        try:
            row = conn.execute(
                """
                SELECT content
                FROM working_memory
                WHERE id = ?
                LIMIT 1
                """,
                (memory_id,),
            ).fetchone()

            if row is None:
                raise KeyError(
                    f"Memory {memory_id} not found for profile {profile}"
                )

            content = row["content"]

            if not isinstance(content, str):
                raise KeyError(
                    f"Memory {memory_id} for profile {profile} "
                    "does not contain textual content"
                )

            return content

        finally:
            conn.close()
