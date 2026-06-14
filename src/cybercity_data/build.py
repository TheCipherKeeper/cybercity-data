"""Build CI/CD artifacts from an assembled `CityNetwork`.

Produces:
    build/network.json        — canonical machine-readable dump
    build/network.md          — human-readable projection
    build/schema.json         — JSON Schema for downstream validation
    build/topology.json       — clean graph (nodes + edges) for UI
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import CityNetwork, OrgKind

__all__ = ["Builder", "build_artifacts"]


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

    def __init__(self, network: CityNetwork) -> None:
        self.network = network

    def build(self) -> dict[str, str]:
        return {
            "network.json": self._build_json(),
            "network.md": self._build_markdown(),
            "schema.json": self._build_schema(),
            "topology.json": self._build_topology(),
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
        import json

        schema = self.network.__class__.model_json_schema()
        return json.dumps(schema, indent=2, ensure_ascii=False)

    # ─────────────────────────────────────────────────────────────────
    # Topology graph
    # ─────────────────────────────────────────────────────────────────
    def _build_topology(self) -> str:
        import json

        org_segment = {o.id: o.segment for o in self.network.organizations}
        org_name = {o.id: o.name for o in self.network.organizations}

        nodes: list[dict[str, Any]] = []
        for s in sorted(self.network.services, key=lambda x: x.id):
            nodes.append(
                {
                    "id": s.id,
                    "kind": s.kind,
                    "org_id": s.org_id,
                    "org_name": org_name.get(s.org_id, ""),
                    "segment": org_segment.get(s.org_id, ""),
                    "network_id": s.network_id,
                    "bind_ip": s.bind_ip,
                    "exposure": s.exposure,
                    "auth": s.auth,
                    "data_classification": s.data_classification,
                    "ports": list(s.ports),
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
                    "bidirectional": link.bidirectional,
                    "label": link.label,
                }
            )

        topology = {
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
        return json.dumps(topology, indent=2, ensure_ascii=False)

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
            "| id | name | kind | segment | networks | services | tags | regulated |"
        )
        parts.append("|---|---|---|---|---|---|---|---|")
        svc_count_by_org = Counter(s.org_id for s in self.network.services)
        for o in sorted(self.network.organizations, key=lambda x: x.id):
            tags = ", ".join(o.tags) if o.tags else ""
            regulated = ", ".join(o.regulated) if o.regulated else ""
            parts.append(
                f"| `{o.id}` | {o.name} | {o.kind} | {o.segment} | "
                f"{len(o.networks)} | {svc_count_by_org.get(o.id, 0)} | "
                f"{tags} | {regulated} |"
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
            "classification | software | ports | mock |"
        )
        parts.append("|---|---|---|---|---|---|---|---|---|---|---|")
        net_by_id = {n.id: n for o in self.network.organizations for n in o.networks}
        for s in sorted(self.network.services, key=lambda x: x.id):
            net = net_by_id.get(s.network_id or "", None)
            sw = ""
            if s.software is not None:
                sw = f"{s.software.vendor}/{s.software.product}"
                if s.software.version:
                    sw += f" {s.software.version}"
            ports = ", ".join(s.ports)
            mock = s.decoy.kind if s.decoy else ""
            bind_ip = s.bind_ip or ""
            parts.append(
                f"| `{s.id}` | `{s.org_id}` | `{s.network_id or ''}` | {bind_ip} | "
                f"{s.kind} | {s.exposure} | {s.auth} | {s.data_classification} | "
                f"{sw} | {ports} | {mock} |"
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
