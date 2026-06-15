"""Git adapter for build change detection."""

import subprocess
from pathlib import Path


class GitChangesGateway:
    """Read previous build state from git."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root.resolve()

    def previous_network_json(self) -> str | None:
        try:
            result = subprocess.run(
                ["git", "show", "HEAD:build/network.json"],
                cwd=self._repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def head_ref(self) -> str | None:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self._repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def head_timestamp(self) -> str | None:
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%cI"],
                cwd=self._repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
