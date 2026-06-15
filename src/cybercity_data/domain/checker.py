"""Cross-field validation for the CyberCity digital-twin network model.

Rules are semantic, never short-circuit, and return a stable `Issue` object.
v0.3 codes are short words instead of V00n numbers — easier to read in CI.
"""

import ipaddress
import re
from collections import Counter

from pydantic import BaseModel, ConfigDict

from .allocator import Allocation
from .models import CityNetwork


class Issue(BaseModel):
    """A single validation finding.

    code  — short semantic identifier, e.g. "ids" or "ip-in-network".
    path  — JSONPath-like locator inside the assembled CityNetwork.
    level — "error" blocks build, "warning" is informational.
    message — human-readable explanation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    path: str
    level: str
    message: str


class Report(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

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
    """Run every cross-field rule against an assembled `CityNetwork`.

    The checker needs an :class:`~cybercity_data.domain.allocator.Allocation` because
    concrete addressing is no longer part of the declarative model.
    """

    def __init__(self, allocation: Allocation | None = None) -> None:
        self.allocation = allocation

    def check(self, network: CityNetwork) -> Report:
        return Report(
            issues=[
                *self._ids(network),
                *self._network_index(network),
                *self._refs(network),
                *self._network_belongs(network),
                *self._ip_in_network(network),
                *self._ip_unique(network),
                *self._network_overlap(network),
                *self._ip_scheme(network),
                *self._exposure_network(network),
                *self._self_loop(network),
                *self._software(network),
                *self._decoy(network),
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
                            f"duplicate link ({frm!r} -> {to!r}, kind={kind!r}) ({n} occurrences)"
                        ),
                    )
                )
        return out

    # ─────────────────────────────────────────────────────────────────
    # network-index
    # ─────────────────────────────────────────────────────────────────
    def _network_index(self, network: CityNetwork) -> list[Issue]:
        out: list[Issue] = []
        if self.allocation is None:
            return out
        indices: dict[int, str] = {}
        for i, org in enumerate(network.organizations):
            idx = self.allocation.network_index(org.id)
            if idx in indices:
                out.append(
                    Issue(
                        code="network-index",
                        path=f"organizations[{i}].network_index",
                        level="error",
                        message=(
                            f"organization {org.id!r} reuses network_index "
                            f"{idx} with {indices[idx]!r}"
                        ),
                    )
                )
            else:
                indices[idx] = org.id
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
        if self.allocation is None:
            return out
        net_by_id = {}
        for org in network.organizations:
            for n in org.networks:
                net_by_id[n.id] = n

        for i, svc in enumerate(network.services):
            if svc.network_id is None:
                continue
            net = net_by_id.get(svc.network_id)
            if net is None:
                continue
            bind_ip = self.allocation.svc_ip.get(svc.id)
            cidr = self.allocation.net_cidr.get(net.id)
            if bind_ip is None or cidr is None:
                continue
            try:
                addr = ipaddress.ip_address(bind_ip)
                net_addr = ipaddress.ip_network(cidr, strict=False)
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
            if addr not in net_addr:
                out.append(
                    Issue(
                        code="ip-in-network",
                        path=f"services[{i}].bind_ip",
                        level="error",
                        message=(
                            f"service {svc.id!r} bind_ip {bind_ip!r} is not in {cidr} ({net.id})"
                        ),
                    )
                )
        return out

    # ─────────────────────────────────────────────────────────────────
    # ip-unique
    # ─────────────────────────────────────────────────────────────────
    def _ip_unique(self, network: CityNetwork) -> list[Issue]:
        out: list[Issue] = []
        if self.allocation is None:
            return out
        seen: dict[str, dict[str, str]] = {}
        for i, svc in enumerate(network.services):
            if svc.network_id is None:
                continue
            bind_ip = self.allocation.svc_ip.get(svc.id)
            if bind_ip is None:
                continue
            net_ips = seen.setdefault(svc.network_id, {})
            if bind_ip in net_ips:
                other_id = net_ips[bind_ip]
                out.append(
                    Issue(
                        code="ip-unique",
                        path=f"services[{i}].bind_ip",
                        level="error",
                        message=(
                            f"service {svc.id!r} bind_ip {bind_ip!r} is already "
                            f"used by service {other_id!r} in network {svc.network_id!r}"
                        ),
                    )
                )
            else:
                net_ips[bind_ip] = svc.id
        return out

    # ─────────────────────────────────────────────────────────────────
    # ip-scheme
    # ─────────────────────────────────────────────────────────────────
    def _ip_scheme(self, network: CityNetwork) -> list[Issue]:
        """Validate that allocated networks live under 10.<network_index>.x.x."""
        out: list[Issue] = []
        if self.allocation is None:
            return out
        for i, org in enumerate(network.organizations):
            prefix = f"10.{self.allocation.network_index(org.id)}."
            for j, net in enumerate(org.networks):
                cidr = self.allocation.net_cidr.get(net.id)
                if cidr is None:
                    continue
                if not cidr.startswith(prefix):
                    out.append(
                        Issue(
                            code="ip-scheme",
                            path=f"organizations[{i}].networks[{j}].cidr",
                            level="error",
                            message=(
                                f"network {net.id!r} cidr {cidr!r} does not start "
                                f"with expected prefix {prefix!r} for org {org.id!r}"
                            ),
                        )
                    )
        return out

    # ─────────────────────────────────────────────────────────────────
    # network-overlap
    # ─────────────────────────────────────────────────────────────────
    def _network_overlap(self, network: CityNetwork) -> list[Issue]:
        out: list[Issue] = []
        if self.allocation is None:
            return out
        nets = [n for o in network.organizations for n in o.networks]
        for i, a in enumerate(nets):
            a_cidr = self.allocation.net_cidr.get(a.id)
            if a_cidr is None:
                continue
            for b in nets[i + 1 :]:
                b_cidr = self.allocation.net_cidr.get(b.id)
                if b_cidr is None:
                    continue
                try:
                    na = ipaddress.ip_network(a_cidr, strict=False)
                    nb = ipaddress.ip_network(b_cidr, strict=False)
                except ValueError:
                    continue
                if na.overlaps(nb):
                    out.append(
                        Issue(
                            code="network-overlap",
                            path="networks",
                            level="error",
                            message=(
                                f"networks {a.id!r} ({a_cidr}) and {b.id!r} ({b_cidr}) overlap"
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

    # ─────────────────────────────────────────────────────────────────
    # decoy
    # ─────────────────────────────────────────────────────────────────
    def _decoy(self, network: CityNetwork) -> list[Issue]:
        out: list[Issue] = []
        is_decoy = {s.id: s.decoy is not None for s in network.services}
        for i, svc in enumerate(network.services):
            if svc.decoy is None:
                continue
            if svc.criticality == "critical":
                out.append(
                    Issue(
                        code="decoy-criticality",
                        path=f"services[{i}].criticality",
                        level="error",
                        message=(f"decoy service {svc.id!r} cannot have criticality=critical"),
                    )
                )

        write_kinds = {"db-write", "backup-of"}
        for j, link in enumerate(network.links):
            if not is_decoy.get(link.from_service, False):
                continue
            if link.kind not in write_kinds:
                continue
            if not is_decoy.get(link.to_service, True):
                out.append(
                    Issue(
                        code="decoy-write-real",
                        path=f"links[{j}]",
                        level="error",
                        message=(
                            f"decoy service {link.from_service!r} cannot {link.kind!r} "
                            f"real service {link.to_service!r}"
                        ),
                    )
                )
        return out


# Convenience free function.
def check(network: CityNetwork, allocation: Allocation | None = None) -> Report:
    return NetworkChecker(allocation=allocation).check(network)
