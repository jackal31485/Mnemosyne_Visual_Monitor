"""
Hermes discovery utilities.

Provides types and helpers used by the public API (`src.discovery.hermes_runtime`).
The tests exercise a set of attributes on :class:`HermesRuntimeSnapshot` which are
mirrored below.  No external dependencies beyond the standard library are used.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

# ---------------------------------------------------------------------------
# Helper for running external commands
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class CommandResult:
    output: str
    exit_code: int

    def __repr__(self) -> str:  # pragma: no cover – debugging helper
        return f"CommandResult(exit_code={self.exit_code}, len={len(self.output)})"


def run_command(cmd: Iterable[str], *, cwd: Optional[Path] = None, timeout: Optional[int] = None) -> CommandResult:
    res = subprocess.run(list(cmd), capture_output=True, text=True,
                        cwd=cwd, timeout=timeout)
    return CommandResult(output=res.stdout + res.stderr,
                         exit_code=res.returncode)

# ---------------------------------------------------------------------------
# Data classes used by the tests.
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class HermesProfileInfo:
    name: str
    path: Path
    enabled: bool = True

@dataclass(slots=True)
class HermesRuntimeSnapshot:
    executable_path: Optional[Path] = None
    version: Optional[str] = None
    installation_path: Optional[Path] = None
    venv_path: Optional[Path] = None
    site_packages_paths: List[Path] = field(default_factory=list)
    profile_names: List[str] = field(default_factory=list)
    current_profile: Optional[str] = None
    config_path: Optional[Path] = None

# ---------------------------------------------------------------------------
# Core discovery logic used by the public API and tests.
# ---------------------------------------------------------------------------
def _discover_runtime(tmp_home: Optional[Path] = None) -> HermesRuntimeSnapshot:
    snap = HermesRuntimeSnapshot()

    # Determine executable path via shutil.which
    exe_name = shutil.which("hermes")
    exe_path: Optional[Path] = None
    if exe_name:
        try:
            exe_path = Path(exe_name).expanduser().resolve()
        except Exception:
            pass
    snap.executable_path = exe_path

    # Version extraction from hermes --version
    if exe_path:
        try:
            r = run_command([str(exe_path), "--version"], timeout=5)
            if r.exit_code == 0:
                snap.version = r.output.splitlines()[0].strip()
        except Exception:
            pass

    # Installation path is directory containing the binary
    if exe_path:
        snap.installation_path = exe_path.parent

    # Discover virtual environment and site-packages
    if snap.installation_path:
        venv_candidate = snap.installation_path / "venv"
        lib_dir = venv_candidate / "lib"
        if lib_dir.is_dir():
            snap.venv_path = venv_candidate.resolve()
            for ver in lib_dir.iterdir():
                sp = ver / "site-packages"
                if sp.is_dir():
                    snap.site_packages_paths.append(sp.resolve())

    # Profiles under $HOME/.hermes/profiles or an overridden tmp_home
    home_root = tmp_home or Path(os.environ.get("HOME", Path.home()))
    profiles_root = (home_root / ".hermes" / "profiles")
    if profiles_root.is_dir():
        snap.profile_names = sorted([d.name for d in profiles_root.iterdir() if d.is_dir()])

    # Current profile picking env var if valid
    cur_env = os.environ.get("HERMES_CURRENT_PROFILE")
    if cur_env and cur_env in snap.profile_names:
        snap.current_profile = cur_env
    elif snap.profile_names:
        snap.current_profile = snap.profile_names[0]

    # Config path under $HOME/.hermes/config.yaml
    snap.config_path = (home_root / ".hermes" / "config.yaml").resolve()

    return snap

# Public API wrapper used by tests and hermes_runtime module.

def get_hermes_runtime_snapshot() -> HermesRuntimeSnapshot:  # pragma: no cover – thin wrapper called in tests
    return _discover_runtime()

__all__ = ["CommandResult", "run_command", "HermesProfileInfo",
           "HermesRuntimeSnapshot", "get_hermes_runtime_snapshot"]
