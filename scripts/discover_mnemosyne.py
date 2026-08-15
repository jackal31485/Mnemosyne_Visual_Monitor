#!/usr/bin/env python3
"""
discover_mnemosyne.py

Phase 1 read-only discovery utility for a local Hermes/Mnemosyne deployment.

Safety guarantees:
- Uses only Python standard-library modules.
- Does not write files.
- Does not modify Hermes configuration.
- Does not modify profiles.
- Does not install packages.
- Opens SQLite databases using read-only mode.
- Performs discovery and reporting only.

The utility reports:
A. Environment
B. Hermes filesystem/configuration layout
C. Hermes virtual environment
D. Mnemosyne package information inside the Hermes venv
E. Candidate profile/database mappings
F. SQLite schema information
G. Initial embedding-structure indicators
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_NAME = "Mnemosyne Visual Monitor"
HERMES_DIR = Path.home() / ".hermes"
HERMES_VENV = HERMES_DIR / "hermes-agent" / "venv"
HERMES_CONFIG = HERMES_DIR / "config.yaml"
HERMES_PROFILES = HERMES_DIR / "profiles"

SQLITE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}


def run_command(command: list[str]) -> str:
    """Run a command without raising and return sanitized stdout."""
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except Exception as exc:
        return f"[EXCEPTION] {type(exc).__name__}: {exc}"

    stdout = result.stdout.strip()

    if result.returncode == 0:
        return stdout or "(no output)"

    return (
        f"[ERROR] command exited with code {result.returncode}: "
        f"{stdout or result.stderr.strip() or 'no diagnostic output'}"
    )


def safe_file_metadata(path: Path) -> dict[str, Any]:
    """Return filesystem metadata without modifying the target."""
    try:
        stat = path.stat()
        return {
            "exists": True,
            "size_bytes": stat.st_size,
            "mtime": stat.st_mtime,
            "ctime": stat.st_ctime,
        }
    except OSError as exc:
        return {
            "exists": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def safe_read_text(path: Path, max_bytes: int = 64 * 1024) -> str:
    """Read a bounded amount of text without modifying the file."""
    try:
        with path.open("rb") as handle:
            raw = handle.read(max_bytes)

        return raw.decode("utf-8", errors="replace")
    except OSError as exc:
        return f"[ERROR] {type(exc).__name__}: {exc}"


def quote_identifier(identifier: str) -> str:
    """Safely quote a SQLite identifier."""
    return '"' + identifier.replace('"', '""') + '"'


def discover_environment() -> dict[str, Any]:
    """Discover basic runtime information."""
    hermes_executable = shutil.which("hermes")

    result: dict[str, Any] = {
        "project": PROJECT_NAME,
        "user": os.environ.get("USER", ""),
        "home": str(Path.home()),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "hermes_executable": hermes_executable or "NOT FOUND",
    }

    if hermes_executable:
        result["hermes_version"] = run_command(
            [hermes_executable, "--version"]
        )

        try:
            result["hermes_executable_resolved"] = str(
                Path(hermes_executable).resolve()
            )
        except OSError:
            result["hermes_executable_resolved"] = hermes_executable
    else:
        result["hermes_version"] = "NOT AVAILABLE"

    return result


def discover_hermes_layout() -> dict[str, Any]:
    """Discover Hermes configuration and profile layout."""
    result: dict[str, Any] = {
        "hermes_directory": str(HERMES_DIR),
        "hermes_directory_exists": HERMES_DIR.is_dir(),
        "config_path": str(HERMES_CONFIG),
        "config_exists": HERMES_CONFIG.is_file(),
        "profiles_directory": str(HERMES_PROFILES),
        "profiles_directory_exists": HERMES_PROFILES.is_dir(),
        "profiles": [],
    }

    if HERMES_CONFIG.is_file():
        result["config_size_bytes"] = safe_file_metadata(
            HERMES_CONFIG
        ).get("size_bytes")

    if HERMES_PROFILES.is_dir():
        try:
            profiles = sorted(
                path.name
                for path in HERMES_PROFILES.iterdir()
                if path.is_dir()
            )
            result["profiles"] = profiles
        except OSError as exc:
            result["profiles_error"] = (
                f"{type(exc).__name__}: {exc}"
            )

    return result


def discover_hermes_venv() -> dict[str, Any]:
    """Discover the expected Hermes virtual environment."""
    python_candidates = [
        HERMES_VENV / "bin" / "python",
        HERMES_VENV / "bin" / "python3",
    ]

    result: dict[str, Any] = {
        "venv_directory": str(HERMES_VENV),
        "venv_exists": HERMES_VENV.is_dir(),
        "python_candidates": [],
    }

    for candidate in python_candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            result["python_candidates"].append(str(candidate))

    if result["python_candidates"]:
        python_path = result["python_candidates"][0]
        result["selected_python"] = python_path
        result["python_version"] = run_command(
            [python_path, "--version"]
        )
    else:
        result["selected_python"] = "NOT FOUND"
        result["python_version"] = "NOT AVAILABLE"

    return result


def inspect_mnemosyne_packages(python_path: str) -> dict[str, Any]:
    """
    Inspect Mnemosyne-related Python packages using the Hermes venv.

    This runs Python's standard-library import machinery inside the target
    environment. It does not install, update, or modify packages.
    """
    if python_path == "NOT FOUND":
        return {"error": "Hermes virtual-environment Python not found"}

    snippet = r"""
import importlib.util
import json
import sys
from importlib import metadata

names = [
    "mnemosyne-hermes",
    "mnemosyne_hermes",
    "mnemosyne",
]

result = {
    "python": sys.executable,
    "packages": {}
}

for name in names:
    entry = {
        "distribution_available": False,
        "distribution_version": None,
        "module_available": False,
        "module_file": None,
    }

    try:
        entry["distribution_version"] = metadata.version(name)
        entry["distribution_available"] = True
    except metadata.PackageNotFoundError:
        pass
    except Exception as exc:
        entry["distribution_error"] = (
            type(exc).__name__ + ": " + str(exc)
        )

    module_name = name.replace("-", "_")

    try:
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            entry["module_available"] = True
            entry["module_file"] = spec.origin
    except Exception as exc:
        entry["module_error"] = (
            type(exc).__name__ + ": " + str(exc)
        )

    result["packages"][name] = entry

print(json.dumps(result))
"""

    try:
        completed = subprocess.run(
            [python_path, "-c", snippet],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except Exception as exc:
        return {
            "error": f"{type(exc).__name__}: {exc}"
        }

    if completed.returncode != 0:
        return {
            "error": (
                f"package inspection exited with code "
                f"{completed.returncode}: "
                f"{completed.stderr.strip() or 'no diagnostic output'}"
            )
        }

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return {
            "error": f"Invalid JSON from venv inspection: {exc}",
            "raw_output": completed.stdout.strip(),
        }


def discover_profile_databases(
    profiles: list[str],
) -> list[dict[str, str]]:
    """Find SQLite-looking files directly inside Hermes profiles."""
    results: list[dict[str, str]] = []

    for profile_name in profiles:
        profile_path = HERMES_PROFILES / profile_name

        try:
            for entry in sorted(profile_path.iterdir()):
                if (
                    entry.is_file()
                    and entry.suffix.lower() in SQLITE_SUFFIXES
                ):
                    results.append(
                        {
                            "profile": profile_name,
                            "path": str(entry.resolve()),
                        }
                    )
        except OSError:
            continue

    return results


def discover_home_database_candidates() -> list[str]:
    """
    Find likely SQLite files in narrowly scoped Hermes/Mnemosyne locations.

    This intentionally avoids a whole-filesystem scan.
    """
    roots = [
        HERMES_DIR,
        HERMES_VENV,
    ]

    candidates: set[str] = set()

    for root in roots:
        if not root.is_dir():
            continue

        try:
            for entry in root.rglob("*"):
                if (
                    entry.is_file()
                    and entry.suffix.lower() in SQLITE_SUFFIXES
                ):
                    try:
                        candidates.add(str(entry.resolve()))
                    except OSError:
                        candidates.add(str(entry))
        except OSError:
            continue

    return sorted(candidates)


def inspect_sqlite_database(path: Path) -> dict[str, Any]:
    """
    Inspect SQLite metadata using a read-only URI.

    No INSERT, UPDATE, DELETE, CREATE, VACUUM, PRAGMA assignment, or other
    mutating operation is performed.
    """
    if not path.is_file():
        return {
            "error": "Database file does not exist"
        }

    try:
        resolved = path.resolve()
    except OSError:
        resolved = path

    uri = (
        "file:"
        + str(resolved).replace("\\", "/")
        + "?mode=ro"
    )

    result: dict[str, Any] = {
        "path": str(resolved),
        "file": safe_file_metadata(resolved),
    }

    try:
        connection = sqlite3.connect(
            uri,
            uri=True,
            timeout=2.0,
        )
    except sqlite3.Error as exc:
        result["error"] = f"SQLite connection error: {exc}"
        return result

    try:
        cursor = connection.cursor()

        cursor.execute("SELECT sqlite_version()")
        result["sqlite_version"] = cursor.fetchone()[0]

        cursor.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        table_names = [row[0] for row in cursor.fetchall()]

        tables: dict[str, Any] = {}

        for table_name in table_names:
            identifier = quote_identifier(table_name)

            cursor.execute(
                f"PRAGMA table_info({identifier})"
            )

            columns = []
            primary_keys = []

            for row in cursor.fetchall():
                column = {
                    "cid": row[0],
                    "name": row[1],
                    "type": row[2],
                    "not_null": bool(row[3]),
                    "default": row[4],
                    "primary_key_position": row[5],
                }

                columns.append(column)

                if row[5]:
                    primary_keys.append(row[1])

            row_count = None
            try:
                cursor.execute(
                    f"SELECT COUNT(*) FROM {identifier}"
                )
                row_count = cursor.fetchone()[0]
            except sqlite3.Error as exc:
                row_count = f"[ERROR] {exc}"

            tables[table_name] = {
                "columns": columns,
                "primary_keys": primary_keys,
                "row_count": row_count,
            }

        result["tables"] = tables

        cursor.execute(
            "SELECT name, tbl_name, sql "
            "FROM sqlite_master "
            "WHERE type='index' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )

        result["indexes"] = [
            {
                "name": row[0],
                "table": row[1],
                "sql": row[2],
            }
            for row in cursor.fetchall()
        ]

        # This reads the journal mode without assigning a new value.
        cursor.execute("PRAGMA journal_mode")
        row = cursor.fetchone()
        result["journal_mode"] = row[0] if row else "unknown"

        wal_path = Path(str(resolved) + "-wal")
        shm_path = Path(str(resolved) + "-shm")

        result["wal_file_present"] = wal_path.exists()
        result["shm_file_present"] = shm_path.exists()

    except sqlite3.Error as exc:
        result["error"] = f"SQLite inspection error: {exc}"
    finally:
        connection.close()

    return result


def embedding_overview(schema: dict[str, Any]) -> dict[str, Any]:
    """Identify obvious embedding-related schema structures."""
    if "error" in schema:
        return {
            "status": "ERROR",
            "detail": schema["error"],
        }

    tables = schema.get("tables", {})

    matches = []

    for table_name, table_info in tables.items():
        table_lower = table_name.lower()

        for column in table_info.get("columns", []):
            column_name = str(column.get("name", ""))
            column_lower = column_name.lower()

            if (
                "embedding" in table_lower
                or "embedding" in column_lower
                or column_lower in {
                    "vector",
                    "vectors",
                    "embedding",
                }
            ):
                matches.append(
                    {
                        "table": table_name,
                        "column": column_name,
                        "type": column.get("type"),
                    }
                )

    if matches:
        return {
            "status": "POSSIBLE_EMBEDDING_STRUCTURE",
            "matches": matches,
        }

    return {
        "status": "NO_OBVIOUS_EMBEDDING_STRUCTURE",
        "matches": [],
    }


def print_section(title: str) -> None:
    """Print a consistent report section header."""
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_mapping(data: Any, indent: int = 0) -> None:
    """Pretty-print nested discovery data."""
    prefix = " " * indent

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                print(f"{prefix}{key}:")
                print_mapping(value, indent + 2)
            else:
                print(f"{prefix}{key}: {value}")
    elif isinstance(data, list):
        if not data:
            print(f"{prefix}(none)")
        else:
            for item in data:
                if isinstance(item, (dict, list)):
                    print_mapping(item, indent)
                else:
                    print(f"{prefix}- {item}")
    else:
        print(f"{prefix}{data}")


def main() -> int:
    """Run all discovery stages."""
    environment = discover_environment()

    print("=" * 80)
    print(PROJECT_NAME.upper())
    print("PHASE 1 READ-ONLY DISCOVERY REPORT")
    print("=" * 80)

    print_section("A. ENVIRONMENT")
    print_mapping(environment)

    hermes = discover_hermes_layout()

    print_section("B. HERMES FILESYSTEM / CONFIGURATION")
    print_mapping(hermes)

    venv = discover_hermes_venv()

    print_section("C. HERMES VIRTUAL ENVIRONMENT")
    print_mapping(venv)

    python_path = venv.get("selected_python", "NOT FOUND")
    mnemosyne = inspect_mnemosyne_packages(python_path)

    print_section("D. MNEMOSYNE PACKAGE INSPECTION")
    print_mapping(mnemosyne)

    profiles = hermes.get("profiles", [])
    profile_databases = discover_profile_databases(profiles)
    additional_databases = discover_home_database_candidates()

    database_paths = set(
        entry["path"] for entry in profile_databases
    )
    database_paths.update(additional_databases)

    print_section("E. PROFILE / DATABASE DISCOVERY")

    if profile_databases:
        print("Profile database candidates:")
        print_mapping(profile_databases, 2)
    else:
        print("Profile database candidates: none")

    print()
    print("All candidate SQLite databases within scoped Hermes locations:")

    if database_paths:
        for path in sorted(database_paths):
            print(f"- {path}")
    else:
        print("- none")

    print_section("F. SQLITE READ-ONLY SCHEMA INSPECTION")

    inspections: dict[str, dict[str, Any]] = {}

    if database_paths:
        for database_path in sorted(database_paths):
            path = Path(database_path)
            print()
            print(f"Database: {path}")

            inspection = inspect_sqlite_database(path)
            inspections[database_path] = inspection

            if "error" in inspection:
                print(f"ERROR: {inspection['error']}")
                continue

            print(
                f"SQLite version: "
                f"{inspection.get('sqlite_version', 'unknown')}"
            )
            print(
                f"Journal mode: "
                f"{inspection.get('journal_mode', 'unknown')}"
            )
            print(
                f"WAL file present: "
                f"{inspection.get('wal_file_present', False)}"
            )
            print(
                f"SHM file present: "
                f"{inspection.get('shm_file_present', False)}"
            )

            tables = inspection.get("tables", {})

            print(f"Tables: {len(tables)}")

            for table_name, table_info in tables.items():
                print(f"  * {table_name}")
                print(
                    f"    Rows: "
                    f"{table_info.get('row_count', 'unknown')}"
                )
                print(
                    "    Columns: "
                    + ", ".join(
                        str(column["name"])
                        for column in table_info.get("columns", [])
                    )
                )
                print(
                    "    Primary keys: "
                    + (
                        ", ".join(table_info.get("primary_keys", []))
                        or "none"
                    )
                )

            indexes = inspection.get("indexes", [])

            print(f"Indexes: {len(indexes)}")

            for index in indexes:
                print(
                    f"  * {index['name']} "
                    f"(table={index['table']})"
                )

    else:
        print("No SQLite databases discovered in scoped locations.")

    print_section("G. EMBEDDING ARCHITECTURE OVERVIEW")

    if inspections:
        for path, inspection in inspections.items():
            overview = embedding_overview(inspection)

            print()
            print(f"Database: {path}")
            print(f"Status: {overview['status']}")

            matches = overview.get("matches", [])

            if matches:
                for match in matches:
                    print(
                        f"  - table={match['table']} "
                        f"column={match['column']} "
                        f"type={match.get('type')}"
                    )
            else:
                print("  No obvious embedding-related structure detected.")

    else:
        print("No database schemas available for embedding analysis.")

    print_section("FINAL SAFETY / STATUS SUMMARY")

    print("Read-only discovery completed.")
    print("Files modified by this script: NONE")
    print("SQLite databases opened read-only: YES")
    print("Packages installed or modified: NONE")
    print("Hermes configuration modified: NO")
    print("Project files modified by this script: NONE")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
