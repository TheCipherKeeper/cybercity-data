"""Init use case: scaffold a new organization under organizations/<id>/."""

from pathlib import Path

from ..data.filesystem import FileSystemGateway, InitTemplate
from ..dto import InitResult


class InitUseCase:
    """Create a new organization directory and config.yml template."""

    def __init__(self, fs: FileSystemGateway) -> None:
        self._fs = fs

    def execute(self, root: Path, org_id: str, kind: str, empty: bool) -> InitResult:
        try:
            orgs_root = self._fs.ensure_organizations_root(root)
        except FileNotFoundError as exc:
            return InitResult(ok=False, error=str(exc))

        target_dir = orgs_root / org_id
        try:
            self._fs.ensure_not_exists(target_dir)
        except FileExistsError as exc:
            return InitResult(ok=False, error=str(exc))

        config_path = InitTemplate.write_config(self._fs, target_dir, org_id, kind, empty)
        return InitResult(ok=True, config_path=config_path)
