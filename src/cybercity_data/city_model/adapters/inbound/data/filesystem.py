"""Filesystem output adapter for build artifacts."""

import shutil
from pathlib import Path


class FileSystemGateway:
    """Write and clean artifacts on disk."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root.resolve()

    def ensure_organizations_root(self, root: Path) -> Path:
        """Return and verify the `organizations/` directory exists under ROOT."""
        orgs_root = (root / "organizations").resolve()
        if not orgs_root.is_dir():
            raise FileNotFoundError(f"missing directory: {orgs_root}")
        return orgs_root

    def ensure_not_exists(self, path: Path) -> None:
        """Raise FileExistsError if the target already exists."""
        if path.exists():
            raise FileExistsError(f"already exists: {path}")

    def create_directory(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def clean_directory(self, target: Path) -> None:
        """Remove all entries inside target (but keep target itself)."""
        target = target.resolve()
        if not target.exists():
            return
        if not target.is_dir():
            raise NotADirectoryError(f"not a directory: {target}")
        for entry in target.iterdir():
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()

    def write_text(self, path: Path, content: str) -> Path:
        path.write_text(content, encoding="utf-8")
        return path.resolve()

    def write_artifacts(self, target: Path, artifacts: dict[str, str]) -> list[Path]:
        """Write a mapping {relative_path -> content} under `target/`.

        Preserves mtime for files whose content did not change.
        """
        target = target.resolve()
        target.mkdir(parents=True, exist_ok=True)
        out: list[Path] = []
        for rel, content in artifacts.items():
            path = target / rel
            if path.exists() and path.read_text(encoding="utf-8") == content:
                out.append(path.resolve())
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            out.append(path.resolve())
        return out

    def repo_root(self, fallback_hint: Path | None = None) -> Path:
        """Best-effort repository root for external commands."""
        if fallback_hint is not None:
            return fallback_hint.resolve()
        return self._repo_root


class InitTemplate:
    """YAML templates for `cybercity-data init`."""

    @staticmethod
    def scaffold(org_id: str, kind: str, empty: bool) -> str:
        name = " ".join(part.capitalize() for part in org_id.split("-"))
        if empty:
            return (
                f"id: {org_id}\n"
                f'name: "{name}"\n'
                f"kind: {kind}\n"
                "\n"
                "description: |\n"
                "  Опиши роль организации, типичные сервисы и связи с другими org.\n"
                "\n"
                "networks: []\n"
                "services: []\n"
                "links: []\n"
            )
        return (
            f"id: {org_id}\n"
            f'name: "{name}"\n'
            f"kind: {kind}\n"
            "\n"
            "description: |\n"
            "  Опиши роль организации, типичные сервисы и связи с другими org.\n"
            "\n"
            "networks:\n"
            f"  - id: {org_id}-dmz\n"
            "    kind: dmz\n"
            "\n"
            "services:\n"
            f"  - id: {org_id}-web\n"
            '    name: "Example web service"\n'
            "    kind: web\n"
            "    exposure: public\n"
            f"    host: www.{org_id}.corp\n"
            f"    network_id: {org_id}-dmz\n"
            "\n"
            "links: []\n"
        )

    @staticmethod
    def write_config(
        fs: FileSystemGateway, target: Path, org_id: str, kind: str, empty: bool
    ) -> Path:
        fs.ensure_not_exists(target)
        fs.create_directory(target)
        config_path = target / "config.yml"
        content = InitTemplate.scaffold(org_id, kind, empty)
        return fs.write_text(config_path, content)
