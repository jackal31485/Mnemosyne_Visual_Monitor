import os
import sys
import shutil
from pathlib import Path, PurePath
from typing import List

# Ensure the src is in path when tests run
sys.path.append(str(Path(__file__).parent.parent / "src"))

from discovery.hermes_runtime import get_hermes_runtime_snapshot, HermesRuntimeSnapshot

def test_no_executable_and_default_paths(tmp_path, monkeypatch):
    # Set HOME to temp dir where no .hermes exists
    home = tmp_path
    monkeypatch.setenv("HOME", str(home))
    # Ensure hermes not found
    def fake_which(name: str): return None
    monkeypatch.setattr(shutil, "which", fake_where) if False else None  # just placeholder
    # Actually we patch shutil.which to always return None
    monkeypatch.setattr(shutil, "which", lambda name: None)

    snap = get_hermes_runtime_snapshot()
    assert isinstance(snap, HermesRuntimeSnapshot)
    assert snap.executable_path is None
    assert snap.version is None
    assert snap.installation_path is None
    assert snap.venv_path is None
    assert snap.site_packages_paths == []
    assert snap.profile_names == []
    assert snap.current_profile is None
    # config_path should resolve to $HOME/.hermes/config.yaml
    expected_config = Path(home) / ".hermes" / "config.yaml"
    assert snap.config_path.resolve() == expected_config.resolve()


def test_full_runtime_snapshot_detection(tmp_path, monkeypatch):
    # Set HOME to temp dir
    home = tmp_path / "home_user"
    home.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))

    # create dummy hermes executable
    exec_dir = tmp_path / "bin"
    exec_dir.mkdir()
    hermes_script = exec_dir / "hermes"
    hermes_script.write_text("#!/usr/bin/env bash\necho \"Hermes 1.2.3\"")
    hermes_script.chmod(0o755)

    # monkeypatch shutil.which to locate it
    monkeypatch.setattr(shutil, "which", lambda name: str(hermes_script) if name == "hermes" else None)

    # create venv with site-packages
    venv_dir = exec_dir / "venv"
    (venv_dir / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages").mkdir(parents=True)

    # create profiles
    profiles_root = home / ".hermes" / "profiles"
    profiles_root.mkdir(parents=True)
    (profiles_root / "profileA").mkdir()
    (profiles_root / "profileB").mkdir()

    monkeypatch.setenv("HERMES_CURRENT_PROFILE", "profileB")

    snap = get_hermes_runtime_snapshot()
    assert isinstance(snap, HermesRuntimeSnapshot)
    # executable path resolution
    assert snap.executable_path.resolve() == hermes_script.resolve()
    # version extracted
    assert snap.version.strip() == "Hermes 1.2.3"
    # installation path
    assert snap.installation_path.resolve() == exec_dir.resolve()
    # venv discovered correctly
    assert snap.venv_path.resolve() == venv_dir.resolve()
    # site_packages should include the created site-packages dir
    sp = (venv_dir / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages").resolve()
    assert any(p.resolve() == sp for p in snap.site_packages_paths)
    # profile names list contains both profiles
    assert set(snap.profile_names) == {"profileA", "profileB"}
    # current_profile matches env var
    assert snap.current_profile == "profileB"
    # config_path location under HOME/.hermes/config.yaml
    expected_cfg = Path(home) / ".hermes" / "config.yaml"
    assert snap.config_path.resolve() == expected_cfg.resolve()

