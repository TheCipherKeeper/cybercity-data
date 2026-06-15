"""Cross-field rule tests."""

from cybercity_data import CityNetwork, check
from cybercity_data.domain.allocator import Allocator
from cybercity_data.domain.models import Network, Organization, Service


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
        "version": "3.0.0",
        "organizations": [
            Organization(
                id="a",
                name="A",
                kind="finance",
                networks=[
                    Network(id="a-dmz", org_id="a", kind="dmz"),
                    Network(id="a-lan", org_id="a", kind="lan"),
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
            )
        ],
    }
    defaults.update(overrides)
    return CityNetwork(**defaults)


def _check(network: CityNetwork):
    """Allocate with a fixed seed and run the checker."""
    allocation = Allocator(network, seed=0).allocate()
    return check(network, allocation=allocation)


def test_tiny_passes(tiny_network: CityNetwork, tiny_allocation) -> None:
    report = check(tiny_network, allocation=tiny_allocation)
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
    report = _check(dup)
    assert any(i.code == "ids" and "organizations" in i.path for i in report.errors)


def test_ids_duplicate_service_id(tiny_network: CityNetwork) -> None:
    dup = _mutate(
        tiny_network,
        services=[
            *tiny_network.services,
            tiny_network.services[0].model_copy(),
        ],
    )
    report = _check(dup)
    assert any(i.code == "ids" and "services" in i.path for i in report.errors)


def test_ids_duplicate_link_key(tiny_network: CityNetwork) -> None:
    dup = _mutate(
        tiny_network,
        links=[tiny_network.links[0], tiny_network.links[0].model_copy()],
    )
    report = _check(dup)
    assert any(i.code == "ids" and "links" in i.path for i in report.errors)


def test_refs_dangling_service_org(tiny_network: CityNetwork) -> None:
    bad = _mutate(
        tiny_network,
        services=[
            tiny_network.services[0].model_copy(update={"org_id": "ghost-org"}),
        ],
    )
    report = _check(bad)
    assert any(i.code == "refs" and "services[0]" in i.path for i in report.errors)


def test_refs_dangling_link(tiny_network: CityNetwork) -> None:
    bad = _mutate(
        tiny_network,
        links=[tiny_network.links[0].model_copy(update={"to_service": "ghost"})],
    )
    report = _check(bad)
    assert any(i.code == "refs" for i in report.errors)


def test_network_belongs(tiny_network: CityNetwork) -> None:
    bad = _mutate(
        tiny_network,
        services=[
            tiny_network.services[0].model_copy(update={"network_id": "other-net"}),
        ],
    )
    report = _check(bad)
    assert any(i.code == "network-belongs" for i in report.errors)


def test_network_belongs_missing_network_id(tiny_network: CityNetwork) -> None:
    svc = tiny_network.services[0]
    bad = _mutate(
        tiny_network,
        services=[svc.model_copy(update={"network_id": None})],
    )
    report = _check(bad)
    assert any(
        i.code == "network-belongs" and "has no network_id" in i.message for i in report.errors
    )


def test_exposure_network(tiny_network: CityNetwork) -> None:
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
    report = _check(bad)
    assert any(i.code == "exposure-network" for i in report.errors)


def test_exposure_network_unknown_net(tiny_network: CityNetwork) -> None:
    svc = tiny_network.services[0]
    bad = _mutate(
        tiny_network,
        services=[svc.model_copy(update={"network_id": "ghost-net"})],
    )
    report = _check(bad)
    # network-belongs fires, exposure-network skips unknown net.
    assert any(i.code == "network-belongs" for i in report.errors)
    assert not any(i.code == "exposure-network" for i in report.errors)


def test_self_loop(tiny_network: CityNetwork) -> None:
    bad = _mutate(
        tiny_network,
        links=[tiny_network.links[0].model_copy(update={"to_service": "cour-web"})],
    )
    report = _check(bad)
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
    report = _check(bad)
    assert any(i.code == "software" for i in report.errors)


def test_decoy_criticality() -> None:
    network = _minimal_network(
        services=[
            Service(
                id="s1",
                org_id="a",
                name="S1",
                kind="web",
                exposure="public",
                host="s1.a.corp",
                network_id="a-dmz",
            ),
            Service(
                id="decoy",
                org_id="a",
                name="Decoy",
                kind="iot",
                exposure="intranet",
                host="decoy.a.corp",
                network_id="a-lan",
                criticality="critical",
                decoy={"kind": "printer", "fingerprint": "realistic"},
            ),
        ]
    )
    report = _check(network)
    assert any(
        i.code == "decoy-criticality" and "cannot have criticality=critical" in i.message
        for i in report.errors
    )


def test_decoy_write_real() -> None:
    network = _minimal_network(
        services=[
            Service(
                id="s1",
                org_id="a",
                name="S1",
                kind="db",
                exposure="intranet",
                host="db.a.corp",
                network_id="a-lan",
            ),
            Service(
                id="decoy",
                org_id="a",
                name="Decoy",
                kind="iot",
                exposure="intranet",
                host="decoy.a.corp",
                network_id="a-lan",
                decoy={"kind": "printer", "fingerprint": "realistic"},
            ),
        ],
        links=[
            {
                "from_service": "decoy",
                "to_service": "s1",
                "kind": "db-write",
                "protocol": "tcp/1521",
            }
        ],
    )
    report = _check(network)
    assert any(i.code == "decoy-write-real" and "decoy service" in i.message for i in report.errors)
