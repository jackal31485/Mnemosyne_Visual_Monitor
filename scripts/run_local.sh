#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -f "$PROJECT_ROOT/.venv/bin/activate" ]]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

HOST="${MNEMOSYNE_HOST:-127.0.0.1}"
PORT="${MNEMOSYNE_PORT:-8000}"

exec python3 -m uvicorn app.main:app --host "$HOST" --port "$PORT" --no-access-log
