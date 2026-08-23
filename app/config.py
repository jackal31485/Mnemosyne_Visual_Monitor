"""Runtime configuration for the read-only graph API."""

from __future__ import annotations

import os
from pathlib import Path


ENV_PREFIX = "MNEMOSYNE_GRAPH_DB_"


def get_profile_db_paths() -> dict[str, Path]:
    """Return configured profile -> SQLite database mappings.

    Configuration is supplied through environment variables named:

        MNEMOSYNE_GRAPH_DB_<PROFILE>=/path/to/database.sqlite

    Profile names are normalized to lowercase.
    """
    result: dict[str, Path] = {}

    for key, value in os.environ.items():
        if not key.startswith(ENV_PREFIX):
            continue

        profile = key[len(ENV_PREFIX):].strip().lower()
        path = value.strip()

        if not profile or not path:
            continue

        result[profile] = Path(path).expanduser()

    return result
