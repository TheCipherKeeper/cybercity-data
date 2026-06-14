"""Build CI/CD artifacts from an assembled `CityNetwork`.

Produces:
    build/network.json        — canonical machine-readable dump
    build/network.md          — human-readable projection
    build/schema.json         — JSON Schema for downstream validation
    build/topology.json       — clean graph (nodes + edges) for UI
    build/network.html        — self-contained interactive graph viewer
    build/engine.zip          — bundled runtime package for cybercity-engine
"""

from __future__ import annotations

import json
import subprocess
import zipfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from .loader import ServiceAssets
from .models import CityNetwork, OrgKind

__all__ = ["Builder", "build_artifacts"]

_STATIC_DIR = Path(__file__).parent / "static"


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


class Builder:
    """Build artifacts from a `CityNetwork`."""

    def __init__(
        self,
        network: CityNetwork,
        service_assets: list[ServiceAssets] | None = None,
    ) -> None:
        self.network = network
        self.service_assets = service_assets or []

    def build(self) -> dict[str, str]:
        return {
            "network.json": self._build_json(),
            "network.md": self._build_markdown(),
            "schema.json": self._build_schema(),
            "topology.json": self._build_topology(),
            "network.html": self._build_html(),
            "attack-surface.json": self._build_attack_surface(),
            "inventory.md": self._build_inventory(),
            "changes.json": self._build_changes(),
        }

    def render(self, target: Path | str) -> list[Path]:
        target = Path(target)
        target.mkdir(parents=True, exist_ok=True)
        out: list[Path] = []
        for rel, content in self.build().items():
            path = target / rel
            if path.exists() and path.read_text(encoding="utf-8") == content:
                out.append(path.resolve())
                continue
            path.write_text(content, encoding="utf-8")
            out.append(path.resolve())
        zip_path = self._render_engine_zip(target)
        out.append(zip_path.resolve())
        return out

    # ─────────────────────────────────────────────────────────────────
    # Canonical dump
    # ─────────────────────────────────────────────────────────────────
    def _build_json(self) -> str:
        return self.network.model_dump_json(indent=2, by_alias=False)

    # ─────────────────────────────────────────────────────────────────
    # JSON Schema
    # ─────────────────────────────────────────────────────────────────
    def _build_schema(self) -> str:
        schema = self.network.__class__.model_json_schema()
        return json.dumps(schema, indent=2, ensure_ascii=False)

    # ─────────────────────────────────────────────────────────────────
    # Topology graph
    # ─────────────────────────────────────────────────────────────────
    def _topology_dict(self) -> dict[str, Any]:
        org_name = {o.id: o.name for o in self.network.organizations}
        org_index = {o.id: o.network_index for o in self.network.organizations}

        nodes: list[dict[str, Any]] = []
        for s in sorted(self.network.services, key=lambda x: x.id):
            nodes.append(
                {
                    "id": s.id,
                    "kind": s.kind,
                    "description": s.description,
                    "org_id": s.org_id,
                    "org_name": org_name.get(s.org_id, ""),
                    "network_index": org_index.get(s.org_id, 0),
                    "network_id": s.network_id,
                    "bind_ip": s.bind_ip,
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
            self.network.links,
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
                "source_version": self.network.version,
            },
            "summary": {
                "organizations": len(self.network.organizations),
                "networks": sum(len(o.networks) for o in self.network.organizations),
                "services": len(self.network.services),
                "links": len(self.network.links),
                "mock_services": sum(1 for s in self.network.services if s.decoy is not None),
            },
            "nodes": nodes,
            "edges": edges,
        }

    def _build_topology(self) -> str:
        return json.dumps(self._topology_dict(), indent=2, ensure_ascii=False)

    # ─────────────────────────────────────────────────────────────────
    # Interactive HTML viewer
    # ─────────────────────────────────────────────────────────────────
    def _build_html(self) -> str:
        template = (_STATIC_DIR / "network.html.tpl").read_text(encoding="utf-8")
        d3_js = (_STATIC_DIR / "d3.v7.min.js").read_text(encoding="utf-8")
        topology_json = json.dumps(self._topology_dict(), ensure_ascii=False)
        return template.replace("{{D3_JS}}", d3_js).replace("{{TOPOLOGY_JSON}}", topology_json)

    # ─────────────────────────────────────────────────────────────────
    # Engine runtime package
    # ─────────────────────────────────────────────────────────────────
    def _build_runtime_dict(self) -> dict[str, Any]:
        """Engine-ready runtime configuration.

        Builds per-service reachability, initial state, and routing hints.
        """
        can_reach: dict[str, list[str]] = defaultdict(list)
        reachable_from: dict[str, list[str]] = defaultdict(list)

        for link in self.network.links:
            can_reach[link.from_service].append(link.to_service)
            reachable_from[link.to_service].append(link.from_service)

        services: list[dict[str, Any]] = []
        for s in sorted(self.network.services, key=lambda x: x.id):
            entry: dict[str, Any] = {
                "id": s.id,
                "org_id": s.org_id,
                "name": s.name,
                "host": s.host,
                "ip": s.bind_ip,
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
                    self.network.links,
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
                        "network_index": o.network_index,
                        "networks": [
                            {"id": n.id, "kind": n.kind, "cidr": n.cidr}
                            for n in o.networks
                        ],
                    }
                    for o in self.network.organizations
                },
            },
        }

    def _build_runtime(self) -> str:
        return json.dumps(self._build_runtime_dict(), indent=2, ensure_ascii=False)

    def _render_engine_zip(self, target: Path) -> Path:
        """Bundle every artifact plus optional service assets into engine.zip."""
        zip_path = target / "engine.zip"
        ts = datetime.now(UTC).isoformat()
        manifest = {
            "schema_version": 1,
            "generated_at": ts,
            "source_version": self.network.version,
            "summary": {
                "organizations": len(self.network.organizations),
                "networks": sum(len(o.networks) for o in self.network.organizations),
                "services": len(self.network.services),
                "links": len(self.network.links),
                "asset_dirs": len(self.service_assets),
            },
            "files": {
                "model/network.json": "canonical CityNetwork dump",
                "model/topology.json": "clean graph for UI/simulator",
                "model/schema.json": "JSON Schema for validation",
                "runtime/engine.json": "engine runtime configuration",
                "security/attack-surface.json": "publicly exposed services",
                "views/network.md": "human-readable projection",
                "views/network.html": "self-contained interactive viewer",
                "views/inventory.md": "asset inventory",
                "changes.json": "diff against previous build",
                "manifest.json": "this file",
            },
        }

        with zipfile.ZipFile(
            zip_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
            zf.writestr("model/network.json", self._build_json())
            zf.writestr("model/topology.json", self._build_topology())
            zf.writestr("model/schema.json", self._build_schema())
            zf.writestr("runtime/engine.json", self._build_runtime())
            zf.writestr("security/attack-surface.json", self._build_attack_surface())
            zf.writestr("views/network.md", self._build_markdown())
            zf.writestr("views/network.html", self._build_html())
            zf.writestr("views/inventory.md", self._build_inventory())
            zf.writestr("changes.json", self._build_changes())

            for asset in self.service_assets:
                for file in sorted(asset.path.rglob("*")):
                    if file.is_file():
                        rel_path = file.relative_to(asset.path).as_posix()
                        arcname = f"assets/services/{asset.org_id}/{asset.svc_id}/{rel_path}"
                        zf.write(file, arcname=arcname)

        return zip_path

    # ─────────────────────────────────────────────────────────────────
    # Attack surface
    # ─────────────────────────────────────────────────────────────────
    def _build_attack_surface(self) -> str:
        org_name = {o.id: o.name for o in self.network.organizations}
        surface: list[dict[str, Any]] = []
        for s in sorted(self.network.services, key=lambda x: x.id):
            if s.exposure != "public":
                continue
            entry: dict[str, Any] = {
                "id": s.id,
                "org_id": s.org_id,
                "org_name": org_name.get(s.org_id, ""),
                "network_id": s.network_id,
                "bind_ip": s.bind_ip,
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
                "meta": {"source_version": self.network.version},
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
    def _build_inventory(self) -> str:
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        parts: list[str] = []
        parts.append("# CyberCity — Asset Inventory")
        parts.append("")
        parts.append(
            f"_Generated by `cybercity-data build` at {ts} "
            f"from schema version **{self.network.version}**._"
        )
        parts.append("")

        if not self.service_assets:
            parts.append("_(no service asset directories discovered)_")
            parts.append("")
            return "\n".join(parts)

        parts.append("| org | service | path | files |")
        parts.append("|---|---|---|---|")
        for asset in sorted(self.service_assets, key=lambda a: (a.org_id, a.svc_id)):
            rel = asset.path.relative_to(asset.path.parents[1]).as_posix()
            file_count = sum(1 for _ in asset.path.rglob("*") if _.is_file())
            parts.append(f"| `{asset.org_id}` | `{asset.svc_id}` | `{rel}` | {file_count} |")
        parts.append("")
        parts.append("---")
        parts.append(
            "_This file is generated. Edit files under "
            "`organizations/<org>/services/<svc>/`._"
        )
        parts.append("")
        return "\n".join(parts)

    # ─────────────────────────────────────────────────────────────────
    # Changes since last build (git-based)
    # ─────────────────────────────────────────────────────────────────
    def _build_changes(self) -> str:
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
        changes = self._diff_networks(previous_network, self.network)
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
        try:
            result = subprocess.run(
                ["git", "show", "HEAD:build/network.json"],
                cwd=self._repo_root(),
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def _git_head_ref(self) -> str | None:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self._repo_root(),
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def _git_head_timestamp(self) -> str | None:
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%cI"],
                cwd=self._repo_root(),
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def _repo_root(self) -> Path:
        """Best-effort repository root for git commands."""
        # Prefer the directory of the first service asset; fall back to cwd.
        if self.service_assets:
            return self.service_assets[0].path.parents[2]
        return Path.cwd()

    def _diff_networks(
        self, previous: CityNetwork, current: CityNetwork
    ) -> dict[str, Any]:
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
                    changes_local.append(
                        {"kind": name, "id": id_, "change": "modified"}
                    )
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
            {
                (link.from_service, link.to_service, link.kind): link
                for link in previous.links
            },
            {
                (link.from_service, link.to_service, link.kind): link
                for link in current.links
            },
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
    def _build_markdown(self) -> str:
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        n_orgs = len(self.network.organizations)
        n_svcs = len(self.network.services)
        n_links = len(self.network.links)
        n_nets = sum(len(o.networks) for o in self.network.organizations)
        n_mocks = sum(1 for s in self.network.services if s.decoy is not None)

        parts: list[str] = []
        parts.append("# CyberCity — Network Projection")
        parts.append("")
        parts.append(
            f"_Generated by `cybercity-data build` at {ts} "
            f"from schema version **{self.network.version}**._"
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

        by_kind: Counter[str] = Counter(o.kind for o in self.network.organizations)
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
        for org in sorted(self.network.organizations, key=lambda o: o.id):
            for net in sorted(org.networks, key=lambda n: n.id):
                svc_count = sum(
                    1 for s in self.network.services if s.network_id == net.id
                )
                parts.append(
                    f"| `{org.id}` | `{net.id}` | {net.kind} | {net.cidr} | {svc_count} |"
                )
        parts.append("")

        # ── 3. Организации ───────────────────────────────────────────
        parts.append("## Организации")
        parts.append("")
        parts.append(
            "| id | name | kind | network_index | networks | services |"
        )
        parts.append("|---|---|---|---|---|---|")
        svc_count_by_org = Counter(s.org_id for s in self.network.services)
        for o in sorted(self.network.organizations, key=lambda x: x.id):
            parts.append(
                f"| `{o.id}` | {o.name} | {o.kind} | {o.network_index} | "
                f"{len(o.networks)} | {svc_count_by_org.get(o.id, 0)} |"
            )
        parts.append("")

        # ── 4. Сетевая связность ─────────────────────────────────────
        parts.append("## Сетевая связность")
        parts.append("")
        if self.network.links:
            svc_to_org: dict[str, str] = {s.id: s.org_id for s in self.network.services}
            parts.append(
                "| from_org | from_service | to_org | to_service "
                "| kind | protocol | encryption | label |"
            )
            parts.append("|---|---|---|---|---|---|---|---|")
            for link in sorted(
                self.network.links,
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
        for s in sorted(self.network.services, key=lambda x: x.id):
            sw = ""
            if s.software is not None:
                sw = f"{s.software.vendor}/{s.software.product}"
                if s.software.version:
                    sw += f" {s.software.version}"
            ports = ", ".join(s.ports)
            mock = s.decoy.kind if s.decoy else ""
            bind_ip = s.bind_ip or ""
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
        mocks = [s for s in self.network.services if s.decoy is not None]
        if mocks:
            parts.append("| id | org | network | bind_ip | mock_kind | fingerprint | os_hint |")
            parts.append("|---|---|---|---|---|---|---|")
            for s in sorted(mocks, key=lambda x: x.id):
                assert s.decoy is not None
                parts.append(
                    f"| `{s.id}` | `{s.org_id}` | `{s.network_id or ''}` | {s.bind_ip or ''} | "
                    f"{s.decoy.kind} | {s.decoy.fingerprint} | {s.decoy.os_hint or ''} |"
                )
        else:
            parts.append("_(нет)_")
        parts.append("")

        parts.append("---")
        parts.append("_Этот файл сгенерирован. Правьте `organizations/<org>/config.yml`._")
        parts.append("")
        return "\n".join(parts)


def build_artifacts(network: CityNetwork, target: Path | str) -> list[Path]:
    """One-shot build: write artifacts under `target/`."""
    return Builder(network).render(target)
