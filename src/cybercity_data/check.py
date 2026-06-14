"""Cross-field validation for the CyberCity digital-twin network model.

Rules are semantic, never short-circuit, and return a stable `Issue` object.
v0.3 codes are short words instead of V00n numbers — easier to read in CI.
"""

from __future__ import annotations

import ipaddress
import re
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import CityNetwork


@dataclass(frozen=True)
class Issue:
    """A single validation finding.

    code  — short semantic identifier, e.g. "ids" or "ip-in-network".
    path  — JSONPath-like locator inside the assembled CityNetwork.
    level — "error" blocks build, "warning" is informational.
    message — human-readable explanation.
    """

    code: str
    path: str
    level: str
    message: str


@dataclass(frozen=True)
class Report:
    issues: list[Issue]

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


_CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$")


class NetworkChecker:
    """Run every cross-field rule against an assembled `CityNetwork`."""

    def check(self, network: CityNetwork) -> Report:
        return Report(
            issues=[
                *self._ids(network),
                *self._refs(network),
                *self._network_belongs(network),
                *self._ip_in_network(network),
                *self._network_overlap(network),
                *self._exposure_network(network),
                *self._self_loop(network),
                *self._software(network),
            ]
        )

    # ─────────────────────────────────────────────────────────────────
    # ids
    # ─────────────────────────────────────────────────────────────────
    def _ids(self, network: CityNetwork) -> list[Issue]:
        out: list[Issue] = []

        for label, items, attr in (
            ("organizations", network.organizations, "id"),
            ("networks", [n for o in network.organizations for n in o.networks], "id"),
            ("services", network.services, "id"),
        ):
            ids = [getattr(x, attr) for x in items]
            for value, n in Counter(ids).items():
                if n > 1:
                    out.append(
                        Issue(
                            code="ids",
                            path=label,
                            level="error",
                            message=f"duplicate id {value!r} in {label} ({n} occurrences)",
                        )
                    )

        link_keys = [(link.from_service, link.to_service, link.kind) for link in network.links]
        for (frm, to, kind), n in Counter(link_keys).items():
            if n > 1:
                out.append(
                    Issue(
                        code="ids",
                        path="links",
                        level="error",
                        message=(
                            f"duplicate link ({frm!r} -> {to!r}, kind={kind!r}) "
                            f"({n} occurrences)"
                        ),
                    )
                )
        return out

    # ─────────────────────────────────────────────────────────────────
    # refs
    # ─────────────────────────────────────────────────────────────────
    def _refs(self, network: CityNetwork) -> list[Issue]:
        out: list[Issue] = []
        org_ids = {o.id for o in network.organizations}
        svc_ids = {s.id for s in network.services}

        for i, svc in enumerate(network.services):
            if svc.org_id not in org_ids:
                out.append(
                    Issue(
                        code="refs",
                        path=f"services[{i}].org_id",
                        level="error",
                        message=f"service {svc.id!r} references unknown org {svc.org_id!r}",
                    )
                )

        for i, link in enumerate(network.links):
            if link.from_service not in svc_ids:
                out.append(
                    Issue(
                        code="refs",
                        path=f"links[{i}].from_service",
                        level="error",
                        message=f"link refers to unknown service {link.from_service!r}",
                    )
                )
            if link.to_service not in svc_ids:
                out.append(
                    Issue(
                        code="refs",
                        path=f"links[{i}].to_service",
                        level="error",
                        message=f"link refers to unknown service {link.to_service!r}",
                    )
                )
        return out

    # ─────────────────────────────────────────────────────────────────
    # network-belongs
    # ─────────────────────────────────────────────────────────────────
    def _network_belongs(self, network: CityNetwork) -> list[Issue]:
        out: list[Issue] = []
        allowed_nets: dict[str, set[str]] = {}
        for org in network.organizations:
            allowed_nets[org.id] = {n.id for n in org.networks}

        for i, svc in enumerate(network.services):
            if svc.network_id is None:
                out.append(
                    Issue(
                        code="network-belongs",
                        path=f"services[{i}].network_id",
                        level="error",
                        message=f"service {svc.id!r} has no network_id",
                    )
                )
                continue
            if svc.network_id not in allowed_nets.get(svc.org_id, set()):
                out.append(
                    Issue(
                        code="network-belongs",
                        path=f"services[{i}].network_id",
                        level="error",
                        message=(
                            f"service {svc.id!r} uses network {svc.network_id!r} "
                            f"that does not belong to org {svc.org_id!r}"
                        ),
                    )
                )
        return out

    # ─────────────────────────────────────────────────────────────────
    # ip-in-network
    # ─────────────────────────────────────────────────────────────────
    def _ip_in_network(self, network: CityNetwork) -> list[Issue]:
        out: list[Issue] = []
        net_by_id = {}
        for org in network.organizations:
            for n in org.networks:
                net_by_id[n.id] = n

        for i, svc in enumerate(network.services):
            if svc.bind_ip is None or svc.network_id is None:
                continue
            net = net_by_id.get(svc.network_id)
            if net is None:
                continue
            try:
                addr = ipaddress.ip_address(svc.bind_ip)
                cidr = ipaddress.ip_network(net.cidr, strict=False)
            except ValueError as exc:
                out.append(
                    Issue(
                        code="ip-in-network",
                        path=f"services[{i}].bind_ip",
                        level="error",
                        message=f"invalid IP or CIDR for service {svc.id!r}: {exc}",
                    )
                )
                continue
            if addr not in cidr:
                out.append(
                    Issue(
                        code="ip-in-network",
                        path=f"services[{i}].bind_ip",
                        level="error",
                        message=(
                            f"service {svc.id!r} bind_ip {svc.bind_ip!r} is not in "
                            f"{net.cidr} ({net.id})"
                        ),
                    )
                )
        return out

    # ─────────────────────────────────────────────────────────────────
    # network-overlap
    # ─────────────────────────────────────────────────────────────────
    def _network_overlap(self, network: CityNetwork) -> list[Issue]:
        out: list[Issue] = []
        nets = [n for o in network.organizations for n in o.networks]
        for i, a in enumerate(nets):
            for b in nets[i + 1 :]:
                try:
                    na = ipaddress.ip_network(a.cidr, strict=False)
                    nb = ipaddress.ip_network(b.cidr, strict=False)
                except ValueError:
                    continue
                if na.overlaps(nb):
                    out.append(
                        Issue(
                            code="network-overlap",
                            path="networks",
                            level="error",
                            message=(
                                f"networks {a.id!r} ({a.cidr}) and {b.id!r} ({b.cidr}) overlap"
                            ),
                        )
                    )
        return out

    # ─────────────────────────────────────────────────────────────────
    # exposure-network
    # ─────────────────────────────────────────────────────────────────
    def _exposure_network(self, network: CityNetwork) -> list[Issue]:
        out: list[Issue] = []
        net_by_id = {}
        for org in network.organizations:
            for n in org.networks:
                net_by_id[n.id] = n

        allowed = {
            "public": {"dmz", "internet"},
            "intranet": {"lan"},
            "ot": {"ot"},
            "mgmt": {"mgmt"},
        }
        for i, svc in enumerate(network.services):
            if svc.network_id is None:
                continue
            net = net_by_id.get(svc.network_id)
            if net is None:
                continue
            if net.kind not in allowed.get(svc.exposure, set()):
                out.append(
                    Issue(
                        code="exposure-network",
                        path=f"services[{i}]",
                        level="error",
                        message=(
                            f"service {svc.id!r} exposure={svc.exposure!r} is not allowed "
                            f"on network kind {net.kind!r}"
                        ),
                    )
                )
        return out

    # ─────────────────────────────────────────────────────────────────
    # self-loop
    # ─────────────────────────────────────────────────────────────────
    def _self_loop(self, network: CityNetwork) -> list[Issue]:
        out: list[Issue] = []
        for i, link in enumerate(network.links):
            if link.from_service == link.to_service:
                out.append(
                    Issue(
                        code="self-loop",
                        path=f"links[{i}]",
                        level="error",
                        message=f"link from {link.from_service!r} points to itself",
                    )
                )
        return out

    # ─────────────────────────────────────────────────────────────────
    # software
    # ─────────────────────────────────────────────────────────────────
    def _software(self, network: CityNetwork) -> list[Issue]:
        out: list[Issue] = []
        for i, svc in enumerate(network.services):
            if svc.software is None:
                continue
            if svc.software.cve_id and not _CVE_RE.match(svc.software.cve_id):
                out.append(
                    Issue(
                        code="software",
                        path=f"services[{i}].software.cve_id",
                        level="error",
                        message=(
                            f"service {svc.id!r} cve_id {svc.software.cve_id!r} "
                            f"does not match CVE-YYYY-NNNNN"
                        ),
                    )
                )
        return out


# Convenience free function.
def check(network: CityNetwork) -> Report:
    return NetworkChecker().check(network)
