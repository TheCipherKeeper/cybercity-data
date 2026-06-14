"""Loader — assemble a `CityNetwork` from the per-org on-disk layout.

Layout:

    organizations/
        city.yml                # version + meta {city, allocation}
        <org-id>/
            config.yml          # id, name, kind, segment, networks,
                                # services, links, plus narrative fields

Design goals for v1.0:
  * `org_id` is injected from the directory name.
  * Networks are allocated from city-level `meta.allocation` ranges.
  * bind_ip is auto-assigned from the service's network.
"""

from __future__ import annotations

import ipaddress
from pathlib import Path

import yaml
from pydantic import ValidationError

from .check import Issue
from .models import Allocation, CityNetwork, Link, Meta, Network, NetworkKind, Organization, Service

__all__ = ["NetworkLoader", "find_org_dirs", "load_network"]


# Segment → list of default network kinds.
_DEFAULT_NETWORK_KINDS: dict[str, list[NetworkKind]] = {
    "corp": ["dmz", "lan", "mgmt"],
    "ot": ["ot", "mgmt"],
    "mgmt": ["mgmt"],
    "public": ["internet"],
}

# Exposure → candidate network kinds in priority order (used when inferring network_id).
_EXPOSURE_TO_KIND: dict[str, tuple[NetworkKind, ...]] = {
    "public": ("dmz", "internet"),
    "intranet": ("lan",),
    "ot": ("ot",),
    "mgmt": ("mgmt",),
}


class NetworkLoader:
    """Assemble a `CityNetwork` from a per-org directory tree."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root.resolve()
        self._orgs_root = self._repo_root / "organizations"
        self.issues: list[Issue] = []
        self._allocation: Allocation | None = None

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
        """Read city.yml + every per-org config.yml and return a CityNetwork."""
        if not self._orgs_root.is_dir():
            raise FileNotFoundError(f"missing directory: {self._orgs_root}")

        city_yml = self._orgs_root / "city.yml"
        if not city_yml.is_file():
            raise FileNotFoundError(f"missing file: {city_yml}")

        city_raw = yaml.safe_load(city_yml.read_text(encoding="utf-8"))
        if not isinstance(city_raw, dict):
            raise FileNotFoundError(
                f"city.yml must be a mapping, got {type(city_raw).__name__}"
            )

        meta_raw = city_raw.get("meta")
        if not isinstance(meta_raw, dict):
            raise FileNotFoundError("city.yml meta must be a mapping")

        try:
            meta = Meta.model_validate(meta_raw)
        except ValidationError as exc:
            self._record_validation_errors("organizations/city.yml", exc, prefix="city")
            raise

        self._allocation = meta.allocation

        org_dirs = self.find_org_dirs(self._repo_root)
        if not org_dirs:
            raise FileNotFoundError(f"no organization directories under {self._orgs_root}")

        orgs: list[Organization] = []
        services: list[Service] = []
        links: list[Link] = []

        for org_dir in org_dirs:
            self._load_one_org(org_dir, orgs, services, links)

        orgs = self._allocate_networks(orgs)
        services = self._assign_service_networks(orgs, services)
        services = self._assign_bind_ips(orgs, services)

        try:
            network = CityNetwork(
                version=city_raw.get("version", ""),
                meta=meta,
                organizations=orgs,
                services=services,
                links=links,
            )
        except ValidationError as exc:
            self._record_validation_errors("organizations/city.yml", exc, prefix="city")
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
        org_only.setdefault("networks", [])

        networks_raw: list[dict] = []
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

        for j, item in enumerate(raw.get("services") or []):
            if isinstance(item, dict):
                item.setdefault("org_id", org_id)
            try:
                services.append(Service.model_validate(item))
            except ValidationError as exc:
                self._record_validation_errors(
                    f"{rel}:services[{j}]", exc, prefix="service"
                )

        for j, item in enumerate(raw.get("links") or []):
            try:
                links.append(Link.model_validate(item))
            except ValidationError as exc:
                self._record_validation_errors(f"{rel}:links[{j}]", exc, prefix="link")

    # ─────────────────────────────────────────────────────────────────
    # Auto-allocation
    # ─────────────────────────────────────────────────────────────────
    def _allocate_networks(self, orgs: list[Organization]) -> list[Organization]:
        """Add default networks to organizations that did not declare any."""
        assert self._allocation is not None

        out: list[Organization] = []
        # One global index per network kind so mgmt/ot/etc never collide across segments.
        indices: dict[str, int] = {}
        sorted_orgs = sorted(orgs, key=lambda o: o.id)

        for org in sorted_orgs:
            if org.networks:
                out.append(org)
                continue

            default_networks: list[Network] = []
            for kind in _DEFAULT_NETWORK_KINDS[org.segment]:
                idx = indices.get(kind, 0)
                indices[kind] = idx + 1
                default_networks.append(
                    _allocate_network(org.id, kind, idx, self._allocation)
                )
            out.append(org.model_copy(update={"networks": default_networks}))

        return out

    def _assign_service_networks(
        self, orgs: list[Organization], services: list[Service]
    ) -> list[Service]:
        """Infer network_id for services that omitted it."""
        org_networks: dict[str, dict[NetworkKind, str]] = {}
        for org in orgs:
            org_networks[org.id] = {n.kind: n.id for n in org.networks}

        out: list[Service] = []
        for svc in services:
            if svc.network_id is None:
                kinds = _EXPOSURE_TO_KIND.get(svc.exposure)
                if not kinds:
                    out.append(svc)
                    continue
                nets = org_networks.get(svc.org_id, {})
                net_id = next((nets[k] for k in kinds if k in nets), None)
                if net_id is None:
                    out.append(svc)
                    continue
                svc = svc.model_copy(update={"network_id": net_id})
            out.append(svc)
        return out

    def _assign_bind_ips(
        self, orgs: list[Organization], services: list[Service]
    ) -> list[Service]:
        """Assign bind_ip from the service network if omitted."""
        net_by_id = {n.id: n for o in orgs for n in o.networks}
        # Count already assigned IPs per network to avoid collisions.
        used: dict[str, set[str]] = {}
        for svc in services:
            if svc.bind_ip and svc.network_id:
                used.setdefault(svc.network_id, set()).add(svc.bind_ip)

        out: list[Service] = []
        for svc in services:
            if svc.bind_ip is not None or svc.network_id is None:
                out.append(svc)
                continue
            net = net_by_id.get(svc.network_id)
            if net is None:
                out.append(svc)
                continue
            try:
                ip = _allocate_ip(net.cidr, used.get(net.id, set()))
            except ValueError as exc:
                self.issues.append(
                    Issue(
                        code="L004",
                        path=f"services:{svc.id}:bind_ip",
                        level="error",
                        message=f"cannot allocate IP for service {svc.id!r}: {exc}",
                    )
                )
                out.append(svc)
                continue
            used.setdefault(net.id, set()).add(ip)
            out.append(svc.model_copy(update={"bind_ip": ip}))
        return out

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
# Helpers
# ─────────────────────────────────────────────────────────────────────
def _allocate_network(org_id: str, kind: str, index: int, allocation: Allocation) -> Network:
    """Allocate a single default network for an organization."""
    cidr = _allocate_cidr(kind, index, allocation)
    return Network(
        id=f"{org_id}-{kind}",
        org_id=org_id,
        name=f"{org_id} {kind}",
        kind=kind,  # type: ignore[arg-type]
        cidr=cidr,
        description=f"Auto-allocated {kind} network for {org_id}",
    )


def _allocate_cidr(kind: str, index: int, allocation: Allocation) -> str:
    """Allocate a deterministic subnet from city ranges."""
    if kind == "dmz":
        return _nth_subnet(allocation.corp, index, 24)
    if kind == "lan":
        return _nth_subnet(allocation.corp, index + 128, 24)
    if kind == "ot":
        return _nth_subnet(allocation.ot, index, 24)
    if kind == "mgmt":
        return _nth_subnet(allocation.mgmt, index, 24)
    if kind == "internet":
        return _nth_subnet(allocation.internet, index, 28)
    raise ValueError(f"cannot allocate CIDR for kind={kind}")


def _nth_subnet(base_cidr: str, index: int, prefix: int) -> str:
    """Return the index-th subnet of `prefix` length inside `base_cidr`."""
    base = ipaddress.ip_network(base_cidr, strict=False)
    subnets = list(base.subnets(new_prefix=prefix))
    if index >= len(subnets):
        raise ValueError(
            f"cannot allocate subnet {index}/{prefix} from {base_cidr}"
        )
    return str(subnets[index])


def _allocate_ip(cidr: str, used: set[str]) -> str:
    """Return first available host IP in the network, skipping .0 and .1."""
    net = ipaddress.ip_network(cidr, strict=False)
    hosts = list(net.hosts())
    # Reserve first 9 addresses (.1-.9) for infrastructure/gateways.
    candidates = [str(h) for h in hosts[9:]]
    for ip in candidates:
        if ip not in used:
            return ip
    raise ValueError(f"no available IP in {cidr}")


# ─────────────────────────────────────────────────────────────────────
# Backward-compat shims
# ─────────────────────────────────────────────────────────────────────
def find_org_dirs(repo_root: Path) -> list[Path]:
    return NetworkLoader.find_org_dirs(repo_root)


def load_network(repo_root: Path) -> tuple[CityNetwork, list[Issue]]:
    loader = NetworkLoader(repo_root)
    network = loader.load()
    return network, list(loader.issues)
