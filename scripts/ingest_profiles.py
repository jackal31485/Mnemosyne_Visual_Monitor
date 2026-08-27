#!/usr/bin/env python3
"""
CLI entry point for the Hermes‑profile ingestion bridge.

Usage:
    python scripts/ingest_profiles.py [--dry-run]

The --dry‑run flag performs a safety audit – it walks through every profile, reports how many memories would be proposed and *does not* modify the collective database.
"""
import argparse
import json

# Adjust ``sys.path`` to allow imports from the repository root when executing
# this file directly.  The test environment already sets PYTHONPATH, but a manual
# run via ``python scripts/ingest_profiles.py …`` would fail without it.
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.domain.profile_ingest import ingest_profiles

if __name__ == "__main__":  # pragma: no cover (manual use)
    parser = argparse.ArgumentParser(description="Ingest Hermes profiles into the collective database")
    parser.add_argument("--dry-run", action="store_true", help="Run a dry run – report counts without writing to the DB.")
    args = parser.parse_args()

    result = ingest_profiles(dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
