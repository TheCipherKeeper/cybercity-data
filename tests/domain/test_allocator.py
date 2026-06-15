"""Tests for the network/IP allocator."""

import pytest

from cybercity_data.domain.allocator import AllocationError, Allocator
from cybercity_data.domain.models import CityNetwork, Network, Organization, Service


def _minimal_network() -> CityNetwork:
    return CityNetwork(
        organizations=[
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
                id="s2",
                org_id="a",
                name="S2",
                kind="api",
                exposure="intranet",
                host="s2.a.corp",
                network_id="a-lan",
            ),
        ],
    )


def test_deterministic_with_same_seed() -> None:
    network = _minimal_network()
    a1 = Allocator(network, seed=42).allocate()
    a2 = Allocator(network, seed=42).allocate()
    assert a1 == a2


def test_different_seeds_give_different_org_indices() -> None:
    network = _minimal_network()
    a1 = Allocator(network, seed=1).allocate()
    a2 = Allocator(network, seed=2).allocate()
    assert a1.org_index != a2.org_index


def test_unique_network_indices() -> None:
    network = CityNetwork(
        organizations=[
            Organization(
                id=f"org-{i}",
                name=f"Org {i}",
                kind="government",
                networks=[Network(id=f"org-{i}-dmz", org_id=f"org-{i}", kind="dmz")],
            )
            for i in range(10)
        ],
        services=[],
    )
    allocation = Allocator(network, seed=0).allocate()
    assert len(set(allocation.org_index.values())) == 10
    assert all(1 <= idx <= 255 for idx in allocation.org_index.values())


def test_cidr_pools_by_kind() -> None:
    network = CityNetwork(
        organizations=[
            Organization(
                id="a",
                name="A",
                kind="government",
                networks=[
                    Network(id="a-dmz", org_id="a", kind="dmz"),
                    Network(id="a-lan", org_id="a", kind="lan"),
                    Network(id="a-ot", org_id="a", kind="ot"),
                    Network(id="a-mgmt", org_id="a", kind="mgmt"),
                ],
            )
        ],
        services=[],
    )
    allocation = Allocator(network, seed=0).allocate()
    idx = allocation.network_index("a")
    dmz_third = int(allocation.cidr("a-dmz").split(".")[2])
    lan_third = int(allocation.cidr("a-lan").split(".")[2])
    ot_third = int(allocation.cidr("a-ot").split(".")[2])
    mgmt_third = int(allocation.cidr("a-mgmt").split(".")[2])

    assert 0 <= dmz_third <= 127
    assert 128 <= lan_third <= 252
    assert 128 <= ot_third <= 252
    assert mgmt_third == 253
    assert len({dmz_third, lan_third, ot_third, mgmt_third}) == 4

    assert allocation.cidr("a-dmz").startswith(f"10.{idx}.")
    assert allocation.cidr("a-lan").startswith(f"10.{idx}.")


def test_service_ips_in_networks() -> None:
    network = _minimal_network()
    allocation = Allocator(network, seed=0).allocate()
    for svc in network.services:
        net_id = svc.network_id
        assert net_id is not None
        cidr = allocation.cidr(net_id)
        bind_ip = allocation.bind_ip(svc.id)
        prefix = cidr.split("/")[1]
        # bind_ip belongs to the allocated network
        assert bind_ip.startswith(cidr.rsplit(".", 1)[0] + ".")
        host = int(bind_ip.split(".")[3])
        assert 1 <= host <= 2 ** (32 - int(prefix)) - 2


def test_unique_bind_ip_per_network() -> None:
    network = CityNetwork(
        organizations=[
            Organization(
                id="a",
                name="A",
                kind="government",
                networks=[Network(id="a-dmz", org_id="a", kind="dmz")],
            )
        ],
        services=[
            Service(
                id=f"s{i}",
                org_id="a",
                name=f"S{i}",
                kind="web",
                exposure="public",
                host=f"s{i}.a.corp",
                network_id="a-dmz",
            )
            for i in range(5)
        ],
    )
    allocation = Allocator(network, seed=0).allocate()
    ips = [allocation.bind_ip(s.id) for s in network.services]
    assert len(set(ips)) == len(ips)


def test_too_many_orgs_raises() -> None:
    network = CityNetwork(
        organizations=[
            Organization(
                id=f"org-{i}",
                name=f"Org {i}",
                kind="government",
                networks=[],
            )
            for i in range(256)
        ],
        services=[],
    )
    with pytest.raises(AllocationError):
        Allocator(network, seed=0).allocate()


def test_too_many_dmz_networks_raises() -> None:
    network = CityNetwork(
        organizations=[
            Organization(
                id="a",
                name="A",
                kind="government",
                networks=[Network(id=f"a-dmz-{i}", org_id="a", kind="dmz") for i in range(129)],
            )
        ],
        services=[],
    )
    with pytest.raises(AllocationError):
        Allocator(network, seed=0).allocate()


def test_too_many_lan_networks_raises() -> None:
    network = CityNetwork(
        organizations=[
            Organization(
                id="a",
                name="A",
                kind="government",
                networks=[Network(id=f"a-lan-{i}", org_id="a", kind="lan") for i in range(126)],
            )
        ],
        services=[],
    )
    with pytest.raises(AllocationError):
        Allocator(network, seed=0).allocate()


def test_multiple_mgmt_networks_raises() -> None:
    network = CityNetwork(
        organizations=[
            Organization(
                id="a",
                name="A",
                kind="government",
                networks=[
                    Network(id="a-mgmt-1", org_id="a", kind="mgmt"),
                    Network(id="a-mgmt-2", org_id="a", kind="mgmt"),
                ],
            )
        ],
        services=[],
    )
    with pytest.raises(AllocationError):
        Allocator(network, seed=0).allocate()
