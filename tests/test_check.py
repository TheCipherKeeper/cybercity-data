"""Cross-field rule tests."""

from __future__ import annotations

from cybercity_data import CityNetwork, check
from cybercity_data.models import Network, Organization, Service


def _mutate(network: CityNetwork, *, services=None, links=None, organizations=None):
    """Return a copy with selected lists replaced."""
    return network.model_copy(
        update={
            k: v
            for k, v in {
                "services": services,
                "links": links,
                "organizations": organizations,
            }.items()
            if v is not None
        }
    )


def _minimal_network(**overrides):
    """Build a minimal explicit CityNetwork for isolated rule tests."""
    defaults = {
        "version": "2.0.0",
        "organizations": [
            Organization(
                id="a",
                name="A",
                kind="finance",
                network_index=1,
                networks=[
                    Network(id="a-dmz", org_id="a", kind="dmz", cidr="10.1.1.0/24"),
                    Network(id="a-lan", org_id="a", kind="lan", cidr="10.1.2.0/24"),
                ],
            )
        ],
        "services": [
            Service(
                id="s1",
                org_id="a",
                name="S1",
                kind="web",
                exposure="public",
                host="s1.a.corp",
                network_id="a-dmz",
                bind_ip="10.1.1.10",
            )
        ],
    }
    defaults.update(overrides)
    return CityNetwork(**defaults)


def test_tiny_passes(tiny_network: CityNetwork) -> None:
    report = check(tiny_network)
    assert not report.has_errors, [i.message for i in report.errors]
    assert not report.warnings


def test_ids_duplicate_org_id(tiny_network: CityNetwork) -> None:
    dup = _mutate(
        tiny_network,
        organizations=[
            *tiny_network.organizations,
            tiny_network.organizations[0].model_copy(),
        ],
    )
    report = check(dup)
    assert any(i.code == "ids" and "organizations" in i.path for i in report.errors)


def test_ids_duplicate_service_id(tiny_network: CityNetwork) -> None:
    dup = _mutate(
        tiny_network,
        services=[
            *tiny_network.services,
            tiny_network.services[0].model_copy(),
        ],
    )
    report = check(dup)
    assert any(i.code == "ids" and "services" in i.path for i in report.errors)


def test_ids_duplicate_link_key(tiny_network: CityNetwork) -> None:
    dup = _mutate(
        tiny_network,
        links=[tiny_network.links[0], tiny_network.links[0].model_copy()],
    )
    report = check(dup)
    assert any(i.code == "ids" and "links" in i.path for i in report.errors)


def test_refs_dangling_service_org(tiny_network: CityNetwork) -> None:
    bad = _mutate(
        tiny_network,
        services=[
            tiny_network.services[0].model_copy(update={"org_id": "ghost-org"}),
        ],
    )
    report = check(bad)
    assert any(i.code == "refs" and "services[0]" in i.path for i in report.errors)


def test_refs_dangling_link(tiny_network: CityNetwork) -> None:
    bad = _mutate(
        tiny_network,
        links=[tiny_network.links[0].model_copy(update={"to_service": "ghost"})],
    )
    report = check(bad)
    assert any(i.code == "refs" for i in report.errors)


def test_network_belongs(tiny_network: CityNetwork) -> None:
    bad = _mutate(
        tiny_network,
        services=[
            tiny_network.services[0].model_copy(update={"network_id": "other-net"}),
        ],
    )
    report = check(bad)
    assert any(i.code == "network-belongs" for i in report.errors)


def test_network_belongs_missing_network_id(tiny_network: CityNetwork) -> None:
    svc = tiny_network.services[0]
    bad = _mutate(
        tiny_network,
        services=[svc.model_copy(update={"network_id": None})],
    )
    report = check(bad)
    assert any(
        i.code == "network-belongs" and "has no network_id" in i.message
        for i in report.errors
    )


def test_ip_in_network(tiny_network: CityNetwork) -> None:
    bad = _mutate(
        tiny_network,
        services=[
            tiny_network.services[0].model_copy(
                update={"network_id": "city-hospital-dmz", "bind_ip": "10.99.0.5"}
            ),
        ],
    )
    report = check(bad)
    assert any(i.code == "ip-in-network" for i in report.errors)


def test_ip_in_network_invalid_ip(tiny_network: CityNetwork) -> None:
    svc = tiny_network.services[0]
    bad = _mutate(
        tiny_network,
        services=[
            svc.model_copy(
                update={"network_id": "city-hospital-dmz", "bind_ip": "999.999.999.999"}
            )
        ],
    )
    report = check(bad)
    assert any(
        i.code == "ip-in-network" and "invalid IP or CIDR" in i.message
        for i in report.errors
    )


def test_network_overlap() -> None:
    network = _minimal_network(
        organizations=[
            Organization(
                id="a",
                name="A",
                kind="finance",
                network_index=1,
                networks=[
                    Network(id="a-dmz", org_id="a", kind="dmz", cidr="10.1.1.0/24")
                ],
            ),
            Organization(
                id="b",
                name="B",
                kind="finance",
                network_index=1,
                networks=[
                    Network(id="b-dmz", org_id="b", kind="dmz", cidr="10.1.1.0/24")
                ],
            ),
        ],
        services=[
            Service(
                id="s1",
                org_id="a",
                name="S1",
                kind="web",
                exposure="public",
                host="s1.a.corp",
                network_id="a-dmz",
                bind_ip="10.1.1.10",
            ),
            Service(
                id="s2",
                org_id="b",
                name="S2",
                kind="web",
                exposure="public",
                host="s2.b.corp",
                network_id="b-dmz",
                bind_ip="10.1.1.11",
            ),
        ],
    )
    report = check(network)
    assert any(i.code == "network-overlap" for i in report.errors)


def test_network_overlap_invalid_cidr_ignored() -> None:
    """Invalid CIDR should not crash the overlap check."""
    from unittest.mock import patch

    network = _minimal_network(
        organizations=[
            Organization(
                id="a",
                name="A",
                kind="finance",
                network_index=1,
                networks=[
                    Network(id="a-dmz", org_id="a", kind="dmz", cidr="10.1.1.0/24")
                ],
            ),
            Organization(
                id="b",
                name="B",
                kind="finance",
                network_index=2,
                networks=[
                    Network(id="b-dmz", org_id="b", kind="dmz", cidr="10.2.2.0/24")
                ],
            ),
        ]
    )
    # Simulate invalid CIDR in overlap check without violating pydantic assignment.
    with patch("ipaddress.ip_network", side_effect=ValueError("boom")):
        report = check(network)
    # Overlap is skipped for invalid CIDR.
    overlap = [i for i in report.issues if i.code == "network-overlap"]
    assert not overlap


def test_exposure_network() -> None:
    network = _minimal_network()
    bad = network.model_copy(
        update={
            "services": [
                network.services[0].model_copy(
                    update={"network_id": "a-lan"}  # public on lan is forbidden
                )
            ]
        }
    )
    report = check(bad)
    assert any(i.code == "exposure-network" for i in report.errors)


def test_exposure_network_unknown_net(tiny_network: CityNetwork) -> None:
    svc = tiny_network.services[0]
    bad = _mutate(
        tiny_network,
        services=[svc.model_copy(update={"network_id": "ghost-net"})],
    )
    report = check(bad)
    # network-belongs fires, exposure-network skips unknown net.
    assert any(i.code == "network-belongs" for i in report.errors)
    assert not any(i.code == "exposure-network" for i in report.errors)


def test_self_loop(tiny_network: CityNetwork) -> None:
    bad = _mutate(
        tiny_network,
        links=[tiny_network.links[0].model_copy(update={"to_service": "cour-web"})],
    )
    report = check(bad)
    assert any(i.code == "self-loop" for i in report.errors)


def test_software_cve_format(tiny_network: CityNetwork) -> None:
    svc = next(s for s in tiny_network.services if s.software is not None)
    software = svc.software
    assert software is not None
    bad = _mutate(
        tiny_network,
        services=[
            svc.model_copy(
                update={"software": software.model_copy(update={"cve_id": "CVE-2024-1"})}
            )
        ],
    )
    report = check(bad)
    assert any(i.code == "software" for i in report.errors)
