# Mnemosyne Visual Monitor

Phase 1 establishes a safe, read-only discovery and inspection foundation for the
local Hermes/Mnemosyne deployment.

## Phase 1 Goals

The discovery utility:

- Detects the local operating-system and Python environment.
- Locates the Hermes executable when available.
- Identifies the Hermes installation and user configuration.
- Discovers Hermes profiles.
- Detects the Hermes virtual environment.
- Inspects Mnemosyne installation information from the Hermes environment.
- Identifies candidate Mnemosyne/Hermes SQLite databases.
- Inspects SQLite databases strictly in read-only mode.
- Reports database tables, columns, primary keys, indexes, journal mode, and WAL state.
- Provides an initial overview of possible embedding-related database structures.

## Safety

The Phase 1 discovery utility is intentionally read-only.

It must:

- Never create or modify project files.
- Never modify Hermes configuration.
- Never modify Hermes profiles.
- Never modify Mnemosyne databases.
- Never install or update packages.
- Open SQLite databases using SQLite read-only mode.
- Report discovery failures rather than attempting repairs or changes.

## Usage

From the project root:

```bash
python3 scripts/discover_mnemosyne.py