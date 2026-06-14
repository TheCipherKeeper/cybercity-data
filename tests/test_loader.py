"""Loader tests: assembly from on-disk layout."""

from __future__ import annotations

from pathlib import Path

import pytest

from cybercity_data import CityNetwork
from cybercity_data.loader import find_org_dirs, load_network


def test_find_org_dirs_skips_underscore_dirs(tiny_path: Path) -> None:
    bad = tiny_path / "organizations" / "_archive"
    try:
        bad.mkdir()
        (bad / "config.yml").write_text("ignored: true\n", encoding="utf-8")

        orgs = find_org_dirs(tiny_path)
        names = [p.name for p in orgs]
        assert "_archive" not in names
        assert {"city-hospital", "city-courthouse", "city-power"} <= set(names)
    finally:
        import shutil

        shutil.rmtree(bad, ignore_errors=True)


def test_find_org_dirs_skips_dirs_without_config(tiny_path: Path) -> None:
    emptydir = tiny_path / "organizations" / "_empty"
    try:
        emptydir.mkdir()

        orgs = find_org_dirs(tiny_path)
        names = [p.name for p in orgs]
        assert "_empty" not in names
    finally:
        import shutil

        shutil.rmtree(emptydir, ignore_errors=True)


def test_find_org_dirs_missing_organizations(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        find_org_dirs(tmp_path)


def test_load_tiny_no_loader_issues(tiny_path: Path) -> None:
    network, issues = load_network(tiny_path)
    assert isinstance(network, CityNetwork)
    assert not issues, [i.message for i in issues]
    assert len(network.organizations) == 3
    assert len(network.services) == 4
    assert len(network.links) == 1


def test_load_missing_city_yml(tmp_path: Path) -> None:
    (tmp_path / "organizations" / "city-x").mkdir(parents=True)
    (tmp_path / "organizations" / "city-x" / "config.yml").write_text(
        "id: city-x\nname: X\nkind: government\nsegment: corp\n",
        encoding="utf-8",
    )
    with pytest.raises(FileNotFoundError):
        load_network(tmp_path)


def test_load_l003_id_mismatch(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "city.yml").write_text(
        'version: "1.0.0"\n'
        "meta:\n"
        "  city: x\n"
        "  allocation:\n"
        "    corp: 10.10.0.0/16\n"
        "    ot: 10.20.0.0/16\n"
        "    mgmt: 10.30.0.0/16\n"
        "    internet: 203.0.113.0/24\n",
        encoding="utf-8",
    )
    (tmp_path / "organizations" / "city-x").mkdir()
    (tmp_path / "organizations" / "city-x" / "config.yml").write_text(
        "id: different\n"
        "name: X\n"
        "kind: government\n"
        "segment: corp\n"
        "services: []\n",
        encoding="utf-8",
    )
    network, issues = load_network(tmp_path)
    assert any(i.code == "L003" for i in issues)


def test_load_l002_per_org_schema_error(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "city.yml").write_text(
        'version: "1.0.0"\n'
        "meta:\n"
        "  city: x\n"
        "  allocation:\n"
        "    corp: 10.10.0.0/16\n"
        "    ot: 10.20.0.0/16\n"
        "    mgmt: 10.30.0.0/16\n"
        "    internet: 203.0.113.0/24\n",
        encoding="utf-8",
    )
    (tmp_path / "organizations" / "city-x").mkdir()
    (tmp_path / "organizations" / "city-x" / "config.yml").write_text(
        "id: city-x\n"
        "name: X\n"
        "kind: not-a-kind\n"
        "segment: corp\n"
        "services: []\n",
        encoding="utf-8",
    )
    network, issues = load_network(tmp_path)
    assert any(i.code == "L002" for i in issues)


def test_auto_alloc_networks(tiny_network: CityNetwork) -> None:
    org = next(o for o in tiny_network.organizations if o.id == "city-hospital")
    kinds = {n.kind for n in org.networks}
    assert kinds == {"dmz", "lan", "mgmt"}


def test_auto_assign_network_id(tiny_network: CityNetwork) -> None:
    svc = next(s for s in tiny_network.services if s.id == "hosp-web")
    assert svc.network_id == "city-hospital-dmz"


def test_injected_org_id(tiny_network: CityNetwork) -> None:
    svc = next(s for s in tiny_network.services if s.id == "hosp-web")
    assert svc.org_id == "city-hospital"


def test_auto_alloc_bind_ip(tiny_network: CityNetwork) -> None:
    svc = next(s for s in tiny_network.services if s.id == "hosp-web")
    assert svc.bind_ip is not None
    assert svc.bind_ip.startswith("10.10.")


def test_explicit_bind_ip_preserved(tiny_network: CityNetwork) -> None:
    svc = next(s for s in tiny_network.services if s.id == "decoy-printer-01")
    assert svc.bind_ip is not None


def test_load_l001_bad_yaml_in_org(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "city.yml").write_text(
        'version: "1.0.0"\n'
        "meta:\n"
        "  city: x\n"
        "  allocation:\n"
        "    corp: 10.10.0.0/16\n"
        "    ot: 10.20.0.0/16\n"
        "    mgmt: 10.30.0.0/16\n"
        "    internet: 203.0.113.0/24\n",
        encoding="utf-8",
    )
    (tmp_path / "organizations" / "city-x").mkdir()
    (tmp_path / "organizations" / "city-x" / "config.yml").write_text(
        "not: valid: yaml: [\n", encoding="utf-8"
    )
    network, issues = load_network(tmp_path)
    assert any(i.code == "L001" for i in issues)


def test_load_l001_root_not_mapping(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "city.yml").write_text(
        'version: "1.0.0"\n'
        "meta:\n"
        "  city: x\n"
        "  allocation:\n"
        "    corp: 10.10.0.0/16\n"
        "    ot: 10.20.0.0/16\n"
        "    mgmt: 10.30.0.0/16\n"
        "    internet: 203.0.113.0/24\n",
        encoding="utf-8",
    )
    (tmp_path / "organizations" / "city-x").mkdir()
    (tmp_path / "organizations" / "city-x" / "config.yml").write_text(
        "- just\n- a\n- list\n", encoding="utf-8"
    )
    network, issues = load_network(tmp_path)
    assert any(i.code == "L001" for i in issues)


def test_load_l002_service_schema_error(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "city.yml").write_text(
        'version: "1.0.0"\n'
        "meta:\n"
        "  city: x\n"
        "  allocation:\n"
        "    corp: 10.10.0.0/16\n"
        "    ot: 10.20.0.0/16\n"
        "    mgmt: 10.30.0.0/16\n"
        "    internet: 203.0.113.0/24\n",
        encoding="utf-8",
    )
    (tmp_path / "organizations" / "city-x").mkdir()
    (tmp_path / "organizations" / "city-x" / "config.yml").write_text(
        "id: city-x\n"
        "name: X\n"
        "kind: government\n"
        "segment: corp\n"
        "services:\n"
        "  - id: bad-svc\n"
        "    name: Bad\n"
        "    kind: not-a-kind\n"
        "    exposure: public\n"
        "    host: bad.example\n",
        encoding="utf-8",
    )
    network, issues = load_network(tmp_path)
    assert any(i.code == "L002" and "service" in i.message for i in issues)


def test_load_l002_link_schema_error(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "city.yml").write_text(
        'version: "1.0.0"\n'
        "meta:\n"
        "  city: x\n"
        "  allocation:\n"
        "    corp: 10.10.0.0/16\n"
        "    ot: 10.20.0.0/16\n"
        "    mgmt: 10.30.0.0/16\n"
        "    internet: 203.0.113.0/24\n",
        encoding="utf-8",
    )
    (tmp_path / "organizations" / "city-x").mkdir()
    (tmp_path / "organizations" / "city-x" / "config.yml").write_text(
        "id: city-x\n"
        "name: X\n"
        "kind: government\n"
        "segment: corp\n"
        "services:\n"
        "  - id: svc\n"
        "    name: S\n"
        "    kind: web\n"
        "    exposure: public\n"
        "    host: svc.example\n"
        "links:\n"
        "  - from_service: svc\n"
        "    to_service: svc\n"
        "    kind: not-a-kind\n",
        encoding="utf-8",
    )
    network, issues = load_network(tmp_path)
    assert any(i.code == "L002" and "link" in i.message for i in issues)


def test_load_explicit_networks_are_used(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "city.yml").write_text(
        'version: "1.0.0"\n'
        "meta:\n"
        "  city: x\n"
        "  allocation:\n"
        "    corp: 10.10.0.0/16\n"
        "    ot: 10.20.0.0/16\n"
        "    mgmt: 10.30.0.0/16\n"
        "    internet: 203.0.113.0/24\n",
        encoding="utf-8",
    )
    (tmp_path / "organizations" / "city-x").mkdir()
    (tmp_path / "organizations" / "city-x" / "config.yml").write_text(
        "id: city-x\n"
        "name: X\n"
        "kind: government\n"
        "segment: corp\n"
        "networks:\n"
        "  - id: city-x-dmz\n"
        "    kind: dmz\n"
        "    cidr: 10.10.99.0/24\n"
        "services:\n"
        "  - id: svc\n"
        "    name: S\n"
        "    kind: web\n"
        "    exposure: public\n"
        "    host: svc.example\n"
        "    network_id: city-x-dmz\n"
        "    bind_ip: 10.10.99.10\n",
        encoding="utf-8",
    )
    network, issues = load_network(tmp_path)
    assert not issues, [i.message for i in issues]
    org = network.organizations[0]
    assert len(org.networks) == 1
    assert org.networks[0].cidr == "10.10.99.0/24"
    assert network.services[0].bind_ip == "10.10.99.10"


def test_load_l004_ip_pool_exhausted(tmp_path: Path) -> None:
    """Fill a /29 with 6 hosts and try to assign a 7th service."""
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "city.yml").write_text(
        'version: "1.0.0"\n'
        "meta:\n"
        "  city: x\n"
        "  allocation:\n"
        "    corp: 10.10.0.0/16\n"
        "    ot: 10.20.0.0/16\n"
        "    mgmt: 10.30.0.0/16\n"
        "    internet: 203.0.113.0/24\n",
        encoding="utf-8",
    )
    (tmp_path / "organizations" / "city-x").mkdir()
    services_yaml = "services:\n"
    for i in range(7):
        services_yaml += (
            f"  - id: svc{i}\n"
            f"    name: S{i}\n"
            "    kind: web\n"
            "    exposure: public\n"
            f"    host: svc{i}.example\n"
            "    network_id: city-x-dmz\n"
        )
    (tmp_path / "organizations" / "city-x" / "config.yml").write_text(
        "id: city-x\n"
        "name: X\n"
        "kind: government\n"
        "segment: corp\n"
        "networks:\n"
        "  - id: city-x-dmz\n"
        "    kind: dmz\n"
        "    cidr: 10.10.99.0/29\n"
        + services_yaml,
        encoding="utf-8",
    )
    network, issues = load_network(tmp_path)
    assert any(i.code == "L004" for i in issues)
