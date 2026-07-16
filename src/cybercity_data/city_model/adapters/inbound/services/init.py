"""Init service: facade for scaffolding a new organization.

The service wires the filesystem adapter and exposes a single ``run()`` entry
point.  Internally it is split into named pipeline steps (``_ensure_root``,
``_ensure_target``, ``_write_template``) so that each step can be exercised
independently in tests.
"""

from pathlib import Path

from ..data.filesystem import FileSystemGateway, InitTemplate
from ..dto import InitResult


class InitService:
    """Facade for scaffolding a new organization."""

    def __init__(self, fs: FileSystemGateway) -> None:
        self._fs = fs

    def run(self, path: Path, org_id: str, kind: str, empty: bool) -> InitResult:
        """Create a new organization directory under ``path/organizations``."""
        try:
            orgs_root = self._ensure_root(path)
            target_dir = self._ensure_target(orgs_root, org_id)
            config_path = self._write_template(target_dir, org_id, kind, empty)
            return InitResult(ok=True, config_path=config_path)
        except FileNotFoundError as exc:
            return InitResult(ok=False, error=str(exc))
        except FileExistsError as exc:
            return InitResult(ok=False, error=str(exc))

    def _ensure_root(self, root: Path) -> Path:
        """Return and verify the ``organizations/`` directory exists under ROOT."""
        return self._fs.ensure_organizations_root(root)

    def _ensure_target(self, orgs_root: Path, org_id: str) -> Path:
        """Return the target org directory, raising if it already exists."""
        target_dir = orgs_root / org_id
        self._fs.ensure_not_exists(target_dir)
        return target_dir

    def _write_template(self, target_dir: Path, org_id: str, kind: str, empty: bool) -> Path:
        """Write the scaffolded ``config.yml`` under the target directory."""
        self._fs.create_directory(target_dir)
        config_path = target_dir / "config.yml"
        content = InitTemplate.scaffold(org_id, kind, empty)
        return self._fs.write_text(config_path, content)


def create_init_service(path: Path) -> InitService:
    """Wire the filesystem adapter for ``init``."""
    return InitService(fs=FileSystemGateway(path))
