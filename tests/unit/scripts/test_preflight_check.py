from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "preflight_check.sh"


def test_preflight_script_exists_and_is_executable():
    assert SCRIPT_PATH.exists(), "preflight_check.sh must exist"
    mode = SCRIPT_PATH.stat().st_mode
    assert bool(mode & stat.S_IXUSR), "preflight_check.sh should be executable"


def test_preflight_script_passes_shellcheck_equivalent():
    subprocess.run(["bash", "-n", str(SCRIPT_PATH)], check=True)


def test_preflight_help_runs_without_dependencies(monkeypatch: pytest.MonkeyPatch):
    """--help should not require helm/kubectl so CI can show usage."""
    # Fake PATH to avoid picking helm/kubectl in CI; the script should exit early with usage.
    monkeypatch.setenv("PATH", os.defpath)
    result = subprocess.run(
        [str(SCRIPT_PATH), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Usage: scripts/preflight_check.sh" in result.stdout
