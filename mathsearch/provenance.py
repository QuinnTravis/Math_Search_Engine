"""Facts recorded with every index and every experiment so results can be traced back."""
import os
import platform
import subprocess

from mathsearch.paths import REPO_ROOT


def _git(*args):
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def git_info():
    """Current commit, and whether there were uncommitted changes (a dirty run is not reproducible)."""
    status = _git("status", "--porcelain")
    return {"commit": _git("rev-parse", "HEAD"), "dirty": bool(status) if status is not None else None}


def machine_info():
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "python": platform.python_version(),
    }
