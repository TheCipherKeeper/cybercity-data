"""Property-based tests for the pipeline."""

from __future__ import annotations

import hypothesis.strategies as st
from hypothesis import given, settings

from cybercity_data import Builder, CityNetwork, check
from cybercity_data.models import Link, Network, Organization, Service

_SVC_KINDS = [
    "web",
    "api",
    "pos",
    "identity",
    "db",
    "file-share",
    "vpn",
    "mail",
    "dns",
    "ntp",
    "backup",
    "log",
    "iot",
]

_EXPOSURES = ["public", "intranet", "ot", "mgmt"]
_AUTHS = ["none", "local", "sso", "mfa", "certificate"]
_CRITICALITIES = ["critical", "high", "medium", "low"]
_LINK_KINDS = [
    "api-call",
    "auth",
    "db-read",
    "db-write",
    "log-sink",
    "backup-of",
    "trusts",
    "vendor-vpn",
    "dns-query",
    "ntp-query",
]


@st.composite
def _city_network(draw):
    org_id = draw(st.sampled_from(["city-a", "city-b", "city-c"]))
    network_index = draw(st.integers(min_value=1, max_value=255))
    third_octet = draw(st.integers(min_value=0, max_value=254))
    cidr = f"10.{network_index}.{third_octet}.0/24"
    net_id = f"{org_id}-net"
    org = Organization(
        id=org_id,
        name=org_id,
        kind="government",
        network_index=network_index,
        networks=[Network(id=net_id, org_id=org_id, kind="lan", cidr=cidr)],
    )

    n_services = draw(st.integers(min_value=1, max_value=8))
    services: list[Service] = []
    for i in range(n_services):
        host_octet = draw(st.integers(min_value=1, max_value=254))
        svc = Service(
            id=f"svc-{i}",
            org_id=org_id,
            name=f"Service {i}",
            kind=draw(st.sampled_from(_SVC_KINDS)),
            exposure=draw(st.sampled_from(_EXPOSURES)),
            host=f"svc-{i}.{org_id}.corp",
            network_id=net_id,
            bind_ip=f"10.{network_index}.{third_octet}.{host_octet}",
            auth=draw(st.sampled_from(_AUTHS)),
            data_classification=draw(
                st.sampled_from(["public", "internal", "confidential", "restricted"])
            ),
            criticality=draw(st.sampled_from(_CRITICALITIES)),
        )
        services.append(svc)

    n_links = draw(st.integers(min_value=0, max_value=min(6, n_services * (n_services - 1))))
    links: list[Link] = []
    seen: set[tuple[str, str, str]] = set()
    for _ in range(n_links):
        source = draw(st.sampled_from([s.id for s in services]))
        target = draw(st.sampled_from([s.id for s in services if s.id != source]))
        kind = draw(st.sampled_from(_LINK_KINDS))
        key = (source, target, kind)
        if key in seen:
            continue
        seen.add(key)
        links.append(Link(from_service=source, to_service=target, kind=kind))

    return CityNetwork(organizations=[org], services=services, links=links)


@settings(max_examples=50, deadline=None)
@given(network=_city_network())
def test_check_and_build_never_crash(network: CityNetwork) -> None:
    report = check(network)
    assert isinstance(report.issues, list)
    artifacts = Builder(network).build()
    for name in ("network.json", "topology.json", "attack-surface.json", "changes.json"):
        assert name in artifacts
