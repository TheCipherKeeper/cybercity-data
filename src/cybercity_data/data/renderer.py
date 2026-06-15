"""Render build artifacts from an assembled `CityNetwork`.

This module is an output adapter: it turns the domain model and allocation
into string representations, but never writes to disk itself. Writing is the
responsibility of `FileSystemGateway` and `EngineZipWriter`.
"""

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from ..domain.allocator import Allocation, Allocator
from ..domain.models import CityNetwork, OrgKind
from .filesystem import FileSystemGateway
from .git import GitChangesGateway
from .loader import ServiceAssets
from .zip import EngineZipWriter

__all__ = ["ArtifactRenderer", "build_artifacts"]

_STATIC_DIR = Path(__file__).parent.parent / "static"


_KIND_ORDER: tuple[OrgKind, ...] = (
    "government",
    "healthcare",
    "infra-utilities",
    "finance",
    "retail",
    "media-telecom",
    "education",
    "msp",
)


class ArtifactRenderer:
    """Generate artifact content strings from a `CityNetwork`."""

    def __init__(
        self,
        static_dir: Path | None = None,
        git: GitChangesGateway | None = None,
    ) -> None:
        self._static_dir = static_dir or _STATIC_DIR
        self._git = git

    def render(
        self,
        network: CityNetwork,
        allocation: Allocation | None = None,
        service_assets: list[ServiceAssets] | None = None,
    ) -> dict[str, str]:
        """Return a mapping `{artifact_name: content}` for every standard artifact."""
        allocation = allocation or Allocator(network).allocate()
        assets = service_assets or []
        return {
            "network.json": self._build_json(network),
            "network.md": self._build_markdown(network, allocation),
            "schema.json": self._build_schema(network),
            "topology.json": self._build_topology(network, allocation),
            "network.html": self._build_html(network, allocation),
            "attack-surface.json": self._build_attack_surface(network, allocation),
            "inventory.md": self._build_inventory(network, assets),
            "changes.json": self._build_changes(network),
            "runtime/engine.json": self._build_runtime(network, allocation),
        }

    # ─────────────────────────────────────────────────────────────────
    # Canonical dump
    # ─────────────────────────────────────────────────────────────────
    @staticmethod
    def _build_json(network: CityNetwork) -> str:
        return network.model_dump_json(indent=2, by_alias=False)

    # ─────────────────────────────────────────────────────────────────
    # JSON Schema
    # ─────────────────────────────────────────────────────────────────
    @staticmethod
    def _build_schema(network: CityNetwork) -> str:
        schema = network.__class__.model_json_schema()
        return json.dumps(schema, indent=2, ensure_ascii=False)

    # ─────────────────────────────────────────────────────────────────
    # Topology graph
    # ─────────────────────────────────────────────────────────────────
    def _topology_dict(self, network: CityNetwork, allocation: Allocation) -> dict[str, Any]:
        org_name = {o.id: o.name for o in network.organizations}

        nodes: list[dict[str, Any]] = []
        for s in sorted(network.services, key=lambda x: x.id):
            nodes.append(
                {
                    "id": s.id,
                    "kind": s.kind,
                    "description": s.description,
                    "org_id": s.org_id,
                    "org_name": org_name.get(s.org_id, ""),
                    "network_index": allocation.network_index(s.org_id),
                    "network_id": s.network_id,
                    "bind_ip": allocation.bind_ip(s.id),
                    "exposure": s.exposure,
                    "auth": s.auth,
                    "data_classification": s.data_classification,
                    "criticality": s.criticality,
                    "ports": list(s.ports),
                    "os_hint": s.os_hint,
                    "is_mock": s.decoy is not None,
                    "host": s.host,
                }
            )

        edges: list[dict[str, Any]] = []
        for link in sorted(
            network.links,
            key=lambda link: (link.from_service, link.to_service, link.kind),
        ):
            edges.append(
                {
                    "from": link.from_service,
                    "to": link.to_service,
                    "kind": link.kind,
                    "protocol": link.protocol,
                    "encryption": link.encryption,
                    "label": link.label,
                }
            )

        return {
            "schema_version": 1,
            "meta": {
                "source_version": network.version,
            },
            "summary": {
                "organizations": len(network.organizations),
                "networks": sum(len(o.networks) for o in network.organizations),
                "services": len(network.services),
                "links": len(network.links),
                "mock_services": sum(1 for s in network.services if s.decoy is not None),
            },
            "nodes": nodes,
            "edges": edges,
        }

    def _build_topology(self, network: CityNetwork, allocation: Allocation) -> str:
        return json.dumps(self._topology_dict(network, allocation), indent=2, ensure_ascii=False)

    # ─────────────────────────────────────────────────────────────────
    # Interactive HTML viewer
    # ─────────────────────────────────────────────────────────────────
    def _build_html(self, network: CityNetwork, allocation: Allocation) -> str:
        template = (self._static_dir / "network.html.tpl").read_text(encoding="utf-8")
        d3_js = (self._static_dir / "d3.v7.min.js").read_text(encoding="utf-8")
        topology_json = json.dumps(self._topology_dict(network, allocation), ensure_ascii=False)
        return template.replace("{{D3_JS}}", d3_js).replace("{{TOPOLOGY_JSON}}", topology_json)

    # ─────────────────────────────────────────────────────────────────
    # Engine runtime package
    # ─────────────────────────────────────────────────────────────────
    def _build_runtime_dict(self, network: CityNetwork, allocation: Allocation) -> dict[str, Any]:
        """Engine-ready runtime configuration.

        Builds per-service reachability, initial state, and routing hints.
        """
        can_reach: dict[str, list[str]] = defaultdict(list)
        reachable_from: dict[str, list[str]] = defaultdict(list)

        for link in network.links:
            can_reach[link.from_service].append(link.to_service)
            reachable_from[link.to_service].append(link.from_service)

        services: list[dict[str, Any]] = []
        for s in sorted(network.services, key=lambda x: x.id):
            entry: dict[str, Any] = {
                "id": s.id,
                "org_id": s.org_id,
                "name": s.name,
                "host": s.host,
                "ip": allocation.bind_ip(s.id),
                "network_id": s.network_id,
                "kind": s.kind,
                "exposure": s.exposure,
                "auth": s.auth,
                "data_classification": s.data_classification,
                "criticality": s.criticality,
                "ports": list(s.ports),
                "status": "up",
                "decoy": s.decoy is not None,
                "can_reach": sorted(set(can_reach.get(s.id, []))),
                "reachable_from": sorted(set(reachable_from.get(s.id, []))),
            }
            if s.software is not None:
                entry["software"] = {
                    "vendor": s.software.vendor,
                    "product": s.software.product,
                    "version": s.software.version,
                    "cve_id": s.software.cve_id,
                }
            if s.decoy is not None:
                entry["decoy_profile"] = {
                    "kind": s.decoy.kind,
                    "fingerprint": s.decoy.fingerprint,
                    "os_hint": s.decoy.os_hint,
                    "note": s.decoy.note,
                }
            services.append(entry)

        return {
            "schema_version": 1,
            "tick_ms": 1000,
            "services": services,
            "links": [
                {
                    "from": link.from_service,
                    "to": link.to_service,
                    "kind": link.kind,
                    "protocol": link.protocol,
                    "encryption": link.encryption,
                    "label": link.label,
                }
                for link in sorted(
                    network.links,
                    key=lambda link: (link.from_service, link.to_service, link.kind),
                )
            ],
            "state": {
                "tick": 0,
                "events": [],
                "compromised": [],
                "offline": [],
            },
            "helpers": {
                "service_lookup": {s["id"]: s for s in services},
                "org_lookup": {
                    o.id: {
                        "name": o.name,
                        "kind": o.kind,
                        "network_index": allocation.network_index(o.id),
                        "networks": [
                            {
                                "id": n.id,
                                "kind": n.kind,
                                "cidr": allocation.cidr(n.id),
                            }
                            for n in o.networks
                        ],
                    }
                    for o in network.organizations
                },
            },
        }

    def _build_runtime(self, network: CityNetwork, allocation: Allocation) -> str:
        return json.dumps(
            self._build_runtime_dict(network, allocation), indent=2, ensure_ascii=False
        )

    # ─────────────────────────────────────────────────────────────────
    # Attack surface
    # ─────────────────────────────────────────────────────────────────
    def _build_attack_surface(self, network: CityNetwork, allocation: Allocation) -> str:
        org_name = {o.id: o.name for o in network.organizations}
        surface: list[dict[str, Any]] = []
        for s in sorted(network.services, key=lambda x: x.id):
            if s.exposure != "public":
                continue
            entry: dict[str, Any] = {
                "id": s.id,
                "org_id": s.org_id,
                "org_name": org_name.get(s.org_id, ""),
                "network_id": s.network_id,
                "bind_ip": allocation.bind_ip(s.id),
                "host": s.host,
                "kind": s.kind,
                "exposure": s.exposure,
                "auth": s.auth,
                "data_classification": s.data_classification,
                "criticality": s.criticality,
                "ports": list(s.ports),
                "is_mock": s.decoy is not None,
            }
            if s.software is not None:
                entry["software"] = {
                    "vendor": s.software.vendor,
                    "product": s.software.product,
                    "version": s.software.version,
                    "cve_id": s.software.cve_id,
                }
            surface.append(entry)

        return json.dumps(
            {
                "schema_version": 1,
                "meta": {"source_version": network.version},
                "summary": {
                    "public_services": len(surface),
                    "mock_services": sum(1 for s in surface if s["is_mock"]),
                },
                "services": surface,
            },
            indent=2,
            ensure_ascii=False,
        )

    # ─────────────────────────────────────────────────────────────────
    # Asset inventory
    # ─────────────────────────────────────────────────────────────────
    @staticmethod
    def _build_inventory(network: CityNetwork, service_assets: list[ServiceAssets]) -> str:
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        parts: list[str] = []
        parts.append("# CyberCity — Asset Inventory")
        parts.append("")
        parts.append(
            f"_Generated by `cybercity-data build` at {ts} "
            f"from schema version **{network.version}**._"
        )
        parts.append("")

        if not service_assets:
            parts.append("_(no service asset directories discovered)_")
            parts.append("")
            return "\n".join(parts)

        parts.append("| org | service | path | files |")
        parts.append("|---|---|---|---|")
        for asset in sorted(service_assets, key=lambda a: (a.org_id, a.svc_id)):
            rel = asset.path.relative_to(asset.path.parents[1]).as_posix()
            file_count = sum(1 for _ in asset.path.rglob("*") if _.is_file())
            parts.append(f"| `{asset.org_id}` | `{asset.svc_id}` | `{rel}` | {file_count} |")
        parts.append("")
        parts.append("---")
        parts.append(
            "_This file is generated. Edit files under `organizations/<org>/services/<svc>/`._"
        )
        parts.append("")
        return "\n".join(parts)

    # ─────────────────────────────────────────────────────────────────
    # Changes since last build (git-based)
    # ─────────────────────────────────────────────────────────────────
    def _build_changes(self, network: CityNetwork) -> str:
        ts = datetime.now(UTC).isoformat()
        previous = self._previous_network_json()
        if previous is None:
            return json.dumps(
                {
                    "schema_version": 1,
                    "generated_at": ts,
                    "previous_ref": None,
                    "previous_generated_at": None,
                    "summary": {
                        "organizations": {"added": 0, "removed": 0, "modified": 0},
                        "services": {"added": 0, "removed": 0, "modified": 0},
                        "links": {"added": 0, "removed": 0, "modified": 0},
                    },
                    "changes": [],
                },
                indent=2,
                ensure_ascii=False,
            )

        previous_network = CityNetwork.model_validate_json(previous)
        changes = self._diff_networks(previous_network, network)
        return json.dumps(
            {
                "schema_version": 1,
                "generated_at": ts,
                "previous_ref": self._git_head_ref(),
                "previous_generated_at": self._git_head_timestamp(),
                "summary": changes["summary"],
                "changes": changes["changes"],
            },
            indent=2,
            ensure_ascii=False,
        )

    def _previous_network_json(self) -> str | None:
        if self._git is None:
            return None
        return self._git.previous_network_json()

    def _git_head_ref(self) -> str | None:
        if self._git is None:
            return None
        return self._git.head_ref()

    def _git_head_timestamp(self) -> str | None:
        if self._git is None:
            return None
        return self._git.head_timestamp()

    @staticmethod
    def _diff_networks(previous: CityNetwork, current: CityNetwork) -> dict[str, Any]:
        T = TypeVar("T", bound=BaseModel)
        K = TypeVar("K", str, tuple[str, str, str])

        def item_map(items: list[T], key_attr: str) -> dict[str, T]:
            return {getattr(i, key_attr): i for i in items}

        def diff_category(
            prev_map: dict[K, T], curr_map: dict[K, T], name: str
        ) -> tuple[dict[str, int], list[dict[str, Any]]]:
            prev_ids = set(prev_map)
            curr_ids = set(curr_map)
            changes_local: list[dict[str, Any]] = []
            for id_ in sorted(curr_ids - prev_ids):
                changes_local.append({"kind": name, "id": id_, "change": "added"})
            for id_ in sorted(prev_ids - curr_ids):
                changes_local.append({"kind": name, "id": id_, "change": "removed"})
            for id_ in sorted(prev_ids & curr_ids):
                if prev_map[id_].model_dump_json() != curr_map[id_].model_dump_json():
                    changes_local.append({"kind": name, "id": id_, "change": "modified"})
            return {
                "added": len(curr_ids - prev_ids),
                "removed": len(prev_ids - curr_ids),
                "modified": sum(1 for c in changes_local if c["change"] == "modified"),
            }, changes_local

        org_summary, org_changes = diff_category(
            item_map(previous.organizations, "id"),
            item_map(current.organizations, "id"),
            "organization",
        )
        svc_summary, svc_changes = diff_category(
            item_map(previous.services, "id"),
            item_map(current.services, "id"),
            "service",
        )
        link_summary, link_changes = diff_category(
            {(link.from_service, link.to_service, link.kind): link for link in previous.links},
            {(link.from_service, link.to_service, link.kind): link for link in current.links},
            "link",
        )

        return {
            "summary": {
                "organizations": org_summary,
                "services": svc_summary,
                "links": link_summary,
            },
            "changes": org_changes + svc_changes + link_changes,
        }

    # ─────────────────────────────────────────────────────────────────
    # Markdown projection
    # ─────────────────────────────────────────────────────────────────
    def _build_markdown(self, network: CityNetwork, allocation: Allocation) -> str:
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        n_orgs = len(network.organizations)
        n_svcs = len(network.services)
        n_links = len(network.links)
        n_nets = sum(len(o.networks) for o in network.organizations)
        n_mocks = sum(1 for s in network.services if s.decoy is not None)

        parts: list[str] = []
        parts.append("# CyberCity — Network Projection")
        parts.append("")
        parts.append(
            f"_Generated by `cybercity-data build` at {ts} "
            f"from schema version **{network.version}**._"
        )
        parts.append("")

        # ── 1. Сводка ─────────────────────────────────────────────────
        parts.append("## Сводка")
        parts.append("")
        parts.append(f"- **Организаций:** {n_orgs}")
        parts.append(f"- **Сервисов:** {n_svcs}")
        parts.append(f"- **Сетей:** {n_nets}")
        parts.append(f"- **Связей:** {n_links}")
        parts.append(f"- **Имитационных сервисов:** {n_mocks}")
        parts.append("")

        by_kind: Counter[str] = Counter(o.kind for o in network.organizations)
        parts.append("| Блок | Организаций |")
        parts.append("|---|---|")
        for kind in _KIND_ORDER:
            parts.append(f"| {kind} | {by_kind.get(kind, 0)} |")
        parts.append(f"| **Итого** | **{n_orgs}** |")
        parts.append("")

        # ── 2. Сети ───────────────────────────────────────────────────
        parts.append("## Сети")
        parts.append("")
        parts.append("| org | network | kind | cidr | services |")
        parts.append("|---|---|---|---|---|")
        for org in sorted(network.organizations, key=lambda o: o.id):
            for net in sorted(org.networks, key=lambda n: n.id):
                svc_count = sum(1 for s in network.services if s.network_id == net.id)
                parts.append(
                    f"| `{org.id}` | `{net.id}` | {net.kind} | "
                    f"{allocation.cidr(net.id)} | {svc_count} |"
                )
        parts.append("")

        # ── 3. Организации ───────────────────────────────────────────
        parts.append("## Организации")
        parts.append("")
        parts.append("| id | name | kind | networks | services |")
        parts.append("|---|---|---|---|---|")
        svc_count_by_org = Counter(s.org_id for s in network.services)
        for o in sorted(network.organizations, key=lambda x: x.id):
            parts.append(
                f"| `{o.id}` | {o.name} | {o.kind} | "
                f"{len(o.networks)} | {svc_count_by_org.get(o.id, 0)} |"
            )
        parts.append("")

        # ── 4. Сетевая связность ─────────────────────────────────────
        parts.append("## Сетевая связность")
        parts.append("")
        if network.links:
            svc_to_org: dict[str, str] = {s.id: s.org_id for s in network.services}
            parts.append(
                "| from_org | from_service | to_org | to_service "
                "| kind | protocol | encryption | label |"
            )
            parts.append("|---|---|---|---|---|---|---|---|")
            for link in sorted(
                network.links,
                key=lambda link: (link.from_service, link.to_service, link.kind),
            ):
                from_org = svc_to_org.get(link.from_service, "?")
                to_org = svc_to_org.get(link.to_service, "?")
                protocol = link.protocol or ""
                label = link.label or ""
                parts.append(
                    f"| `{from_org}` | `{link.from_service}` | `{to_org}` | "
                    f"`{link.to_service}` | {link.kind} | {protocol} | "
                    f"{link.encryption} | {label} |"
                )
        else:
            parts.append("_(нет)_")
        parts.append("")

        # ── 5. Сервисы ────────────────────────────────────────────────
        parts.append("## Сервисы")
        parts.append("")
        parts.append(
            "| id | org | network | bind_ip | kind | exposure | auth | "
            "classification | criticality | software | ports | os_hint | mock |"
        )
        parts.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for s in sorted(network.services, key=lambda x: x.id):
            sw = ""
            if s.software is not None:
                sw = f"{s.software.vendor}/{s.software.product}"
                if s.software.version:
                    sw += f" {s.software.version}"
            ports = ", ".join(s.ports)
            mock = s.decoy.kind if s.decoy else ""
            bind_ip = allocation.bind_ip(s.id)
            os_hint = s.os_hint or ""
            parts.append(
                f"| `{s.id}` | `{s.org_id}` | `{s.network_id or ''}` | {bind_ip} | "
                f"{s.kind} | {s.exposure} | {s.auth} | {s.data_classification} | "
                f"{s.criticality} | {sw} | {ports} | {os_hint} | {mock} |"
            )
        parts.append("")

        # ── 6. Имитационные сервисы ───────────────────────────────────
        parts.append("## Имитационные сервисы")
        parts.append("")
        mocks = [s for s in network.services if s.decoy is not None]
        if mocks:
            parts.append("| id | org | network | bind_ip | mock_kind | fingerprint | os_hint |")
            parts.append("|---|---|---|---|---|---|---|")
            for s in sorted(mocks, key=lambda x: x.id):
                assert s.decoy is not None
                parts.append(
                    f"| `{s.id}` | `{s.org_id}` | `{s.network_id or ''}` | "
                    f"{allocation.bind_ip(s.id)} | "
                    f"{s.decoy.kind} | {s.decoy.fingerprint} | {s.decoy.os_hint or ''} |"
                )
        else:
            parts.append("_(нет)_")
        parts.append("")

        parts.append("---")
        parts.append("_Этот файл сгенерирован. Правьте `organizations/<org>/config.yml`._")
        parts.append("")
        return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────
# Backward-compat free function
# ─────────────────────────────────────────────────────────────────────
def build_artifacts(
    network: CityNetwork,
    target: Path | str,
    allocation: Allocation | None = None,
    repo_root: Path | str | None = None,
) -> list[Path]:
    """One-shot convenience: render and write artifacts under `target/`.

    This wrapper is preserved for callers that used the historical
    `cybercity_data.build_artifacts()` free function. New code should
    prefer `ArtifactRenderer` + `FileSystemGateway` + `EngineZipWriter`.
    """
    target = Path(target).resolve()
    repo_root = Path(repo_root).resolve() if repo_root is not None else Path.cwd()
    allocation = allocation or Allocator(network).allocate()
    renderer = ArtifactRenderer(git=GitChangesGateway(repo_root))
    artifacts = renderer.render(network, allocation, [])
    fs = FileSystemGateway(repo_root)
    paths = fs.write_artifacts(target, artifacts)
    zip_path = EngineZipWriter().bundle(target, artifacts, network, [])
    return [*paths, zip_path]
