"""Loader — assemble a `CityNetwork` from the explicit per-org on-disk layout.

Layout:

    organizations/
        <org-id>/
            config.yml          # id, name, kind, network_index, description,
                                # networks, services, links
            services/           # optional per-service asset directories
                <svc-id>/
                    nginx.conf
                    certs/
                    ...

Design goals for v2.0:
  * `org_id` is injected from the directory name.
  * Networks and bind_ip are declared explicitly in each config.yml.
  * Loader only assembles and validates; it never allocates resources.
  * Optional `services/<svc-id>/` directories hold runtime assets for a service.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .check import Issue
from .models import SCHEMA_VERSION, CityNetwork, Link, Organization, Service

__all__ = ["NetworkLoader", "find_org_dirs", "load_network"]


class ServiceAssets:
    """Optional on-disk assets attached to a service.

    Assets live under `organizations/<org_id>/services/<svc_id>/`.
    The canonical service description still lives in `config.yml`.
    """

    def __init__(self, svc_id: str, org_id: str, path: Path) -> None:
        self.svc_id = svc_id
        self.org_id = org_id
        self.path = path


class NetworkLoader:
    """Assemble a `CityNetwork` from a per-org directory tree."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root.resolve()
        self._orgs_root = self._repo_root / "organizations"
        self.issues: list[Issue] = []
        self.service_assets: list[ServiceAssets] = []

    @staticmethod
    def find_org_dirs(repo_root: Path) -> list[Path]:
        """Sorted list of org directories containing a config.yml.

        Skips entries whose name starts with '_'.
        """
        orgs_root = repo_root / "organizations"
        if not orgs_root.is_dir():
            raise FileNotFoundError(f"missing directory: {orgs_root}")
        out: list[Path] = []
        for entry in sorted(orgs_root.iterdir(), key=lambda p: p.name):
            if not entry.is_dir() or entry.name.startswith("_"):
                continue
            if (entry / "config.yml").is_file():
                out.append(entry)
        return out

    def load(self) -> CityNetwork:
        """Read every per-org config.yml and return a CityNetwork."""
        if not self._orgs_root.is_dir():
            raise FileNotFoundError(f"missing directory: {self._orgs_root}")

        org_dirs = self.find_org_dirs(self._repo_root)
        if not org_dirs:
            raise FileNotFoundError(f"no organization directories under {self._orgs_root}")

        orgs: list[Organization] = []
        services: list[Service] = []
        links: list[Link] = []

        for org_dir in org_dirs:
            self._load_one_org(org_dir, orgs, services, links)

        try:
            network = CityNetwork(
                version=SCHEMA_VERSION,
                organizations=orgs,
                services=services,
                links=links,
            )
        except ValidationError as exc:
            self._record_validation_errors("<root>", exc, prefix="city")
            raise

        return network

    # ─────────────────────────────────────────────────────────────────
    # Per-org loading
    # ─────────────────────────────────────────────────────────────────
    def _load_one_org(
        self,
        org_dir: Path,
        orgs: list[Organization],
        services: list[Service],
        links: list[Link],
    ) -> None:
        cfg_path = org_dir / "config.yml"
        rel = cfg_path.relative_to(self._repo_root).as_posix()
        org_id = org_dir.name

        try:
            raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            self.issues.append(
                Issue(
                    code="L001",
                    path=rel,
                    level="error",
                    message=f"YAML parse error: {exc}",
                )
            )
            return

        if not isinstance(raw, dict):
            self.issues.append(
                Issue(
                    code="L001",
                    path=rel,
                    level="error",
                    message=f"root must be a mapping, got {type(raw).__name__}",
                )
            )
            return

        if raw.get("id") != org_id:
            self.issues.append(
                Issue(
                    code="L003",
                    path=f"{rel}:id",
                    level="error",
                    message=(
                        f"organization id {raw.get('id')!r} does not match "
                        f"folder name {org_id!r}"
                    ),
                )
            )
            return

        org_only = {k: v for k, v in raw.items() if k not in ("services", "links")}

        networks_raw: list[dict[str, Any]] = []
        for item in org_only.get("networks") or []:
            if isinstance(item, dict):
                item.setdefault("org_id", org_id)
            networks_raw.append(item)
        org_only["networks"] = networks_raw

        try:
            org = Organization.model_validate(org_only)
        except ValidationError as exc:
            self._record_validation_errors(rel, exc, prefix="org")
            return

        orgs.append(org)

        service_ids: set[str] = set()
        for j, item in enumerate(raw.get("services") or []):
            if isinstance(item, dict):
                item.setdefault("org_id", org_id)
            try:
                service = Service.model_validate(item)
                services.append(service)
                service_ids.add(service.id)
            except ValidationError as exc:
                self._record_validation_errors(
                    f"{rel}:services[{j}]", exc, prefix="service"
                )

        for j, item in enumerate(raw.get("links") or []):
            try:
                links.append(Link.model_validate(item))
            except ValidationError as exc:
                self._record_validation_errors(f"{rel}:links[{j}]", exc, prefix="link")

        self._load_service_assets(org_dir, org_id, service_ids)

    # ─────────────────────────────────────────────────────────────────
    # Service assets
    # ─────────────────────────────────────────────────────────────────
    def _load_service_assets(
        self, org_dir: Path, org_id: str, service_ids: set[str]
    ) -> None:
        """Discover optional `services/<svc-id>/` asset directories."""
        assets_root = org_dir / "services"
        if not assets_root.is_dir():
            return

        for entry in sorted(assets_root.iterdir(), key=lambda p: p.name):
            if not entry.is_dir():
                continue
            svc_id = entry.name
            rel = entry.relative_to(self._repo_root).as_posix()
            if svc_id not in service_ids:
                self.issues.append(
                    Issue(
                        code="assets",
                        path=rel,
                        level="warning",
                        message=(
                            f"asset directory {svc_id!r} does not match any service "
                            f"declared in {org_id}/config.yml"
                        ),
                    )
                )
                continue
            self.service_assets.append(
                ServiceAssets(svc_id=svc_id, org_id=org_id, path=entry)
            )

    # ─────────────────────────────────────────────────────────────────
    # Errors
    # ─────────────────────────────────────────────────────────────────
    def _record_validation_errors(
        self, path: str, exc: ValidationError, prefix: str
    ) -> None:
        for err in exc.errors():
            loc = ".".join(str(x) for x in err["loc"]) or "<root>"
            self.issues.append(
                Issue(
                    code="L002",
                    path=f"{path}:{loc}",
                    level="error",
                    message=f"{prefix} schema error: {err['msg']}",
                )
            )


# ─────────────────────────────────────────────────────────────────────
# Backward-compat shims
# ─────────────────────────────────────────────────────────────────────
def find_org_dirs(repo_root: Path) -> list[Path]:
    return NetworkLoader.find_org_dirs(repo_root)


def load_network(repo_root: Path) -> tuple[CityNetwork, list[Issue]]:
    """Load the canonical model.

    For access to discovered service assets use `NetworkLoader` directly.
    """
    loader = NetworkLoader(repo_root)
    network = loader.load()
    return network, list(loader.issues)
