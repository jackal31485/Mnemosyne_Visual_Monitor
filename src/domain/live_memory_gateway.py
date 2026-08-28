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

    def get_memory(self, profile: str, memory_id: str) -> str:
        db_path = (
            self.profiles_root
            / profile
            / "mnemosyne"
            / "data"
            / "mnemosyne.db"
        )

        if not db_path.is_file():
            raise KeyError(
                f"Mnemosyne database not found for profile {profile}: {db_path}"
            )

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
