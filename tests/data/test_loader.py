"""Loader tests: assembly from on-disk layout."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from cybercity_data import CityNetwork
from cybercity_data.data.loader import NetworkLoader, find_org_dirs, load_network
from cybercity_data.domain.allocator import Allocator


def test_find_org_dirs_skips_underscore_dirs(tiny_path: Path, tmp_path: Path) -> None:
    import shutil

    target = tmp_path / "tiny-copy"
    shutil.copytree(tiny_path, target)
    bad = target / "organizations" / "_archive"
    bad.mkdir()
    (bad / "config.yml").write_text("ignored: true\n", encoding="utf-8")

    orgs = find_org_dirs(target)
    names = [p.name for p in orgs]
    assert "_archive" not in names
    assert {"hospital", "courthouse", "power"} <= set(names)


def test_find_org_dirs_skips_dirs_without_config(tiny_path: Path, tmp_path: Path) -> None:
    import shutil

    target = tmp_path / "tiny-copy"
    shutil.copytree(tiny_path, target)
    emptydir = target / "organizations" / "_empty"
    emptydir.mkdir()

    orgs = find_org_dirs(target)
    names = [p.name for p in orgs]
    assert "_empty" not in names


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


def test_load_missing_organizations_dir(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_network(tmp_path)


def test_load_l003_id_mismatch(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "x").mkdir()
    (tmp_path / "organizations" / "x" / "config.yml").write_text(
        "id: different\nname: X\nkind: government\nnetworks: []\nservices: []\n",
        encoding="utf-8",
    )
    network, issues = load_network(tmp_path)
    assert any(i.code == "L003" for i in issues)


def test_load_l002_per_org_schema_error(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "x").mkdir()
    (tmp_path / "organizations" / "x" / "config.yml").write_text(
        "id: x\nname: X\nkind: not-a-kind\nnetworks: []\nservices: []\n",
        encoding="utf-8",
    )
    network, issues = load_network(tmp_path)
    assert any(i.code == "L002" for i in issues)


def test_load_rejects_legacy_network_index(tmp_path: Path) -> None:
    """network_index is no longer accepted in config.yml."""
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "x").mkdir()
    (tmp_path / "organizations" / "x" / "config.yml").write_text(
        "id: x\nname: X\nkind: government\nnetwork_index: 1\nnetworks: []\nservices: []\n",
        encoding="utf-8",
    )
    network, issues = load_network(tmp_path)
    assert any(
        i.code == "L002" and "network_index" in i.path and "extra" in i.message.lower()
        for i in issues
    )


def test_load_rejects_legacy_cidr(tmp_path: Path) -> None:
    """cidr is no longer accepted on network declarations."""
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "x").mkdir()
    (tmp_path / "organizations" / "x" / "config.yml").write_text(
        "id: x\n"
        "name: X\n"
        "kind: government\n"
        "networks:\n"
        "  - id: x-dmz\n"
        "    kind: dmz\n"
        "    cidr: 10.1.1.0/24\n"
        "services: []\n",
        encoding="utf-8",
    )
    network, issues = load_network(tmp_path)
    assert any(
        i.code == "L002" and "cidr" in i.path and "extra" in i.message.lower() for i in issues
    )


def test_load_rejects_legacy_bind_ip(tmp_path: Path) -> None:
    """bind_ip is no longer accepted on service declarations."""
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "x").mkdir()
    (tmp_path / "organizations" / "x" / "config.yml").write_text(
        "id: x\n"
        "name: X\n"
        "kind: government\n"
        "networks:\n"
        "  - id: x-dmz\n"
        "    kind: dmz\n"
        "services:\n"
        "  - id: svc\n"
        "    name: S\n"
        "    kind: web\n"
        "    exposure: public\n"
        "    host: svc.example\n"
        "    network_id: x-dmz\n"
        "    bind_ip: 10.1.1.10\n",
        encoding="utf-8",
    )
    network, issues = load_network(tmp_path)
    assert any(
        i.code == "L002" and "bind_ip" in i.path and "extra" in i.message.lower() for i in issues
    )


def test_injected_org_id(tiny_path: Path) -> None:
    svc = next(s for s in load_network(tiny_path)[0].services if s.id == "hosp-web")
    assert svc.org_id == "hospital"


def test_load_l001_bad_yaml_in_org(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "x").mkdir()
    (tmp_path / "organizations" / "x" / "config.yml").write_text(
        "not: valid: yaml: [\n", encoding="utf-8"
    )
    network, issues = load_network(tmp_path)
    assert any(i.code == "L001" for i in issues)


def test_load_l001_root_not_mapping(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "x").mkdir()
    (tmp_path / "organizations" / "x" / "config.yml").write_text(
        "- just\n- a\n- list\n", encoding="utf-8"
    )
    network, issues = load_network(tmp_path)
    assert any(i.code == "L001" for i in issues)


def test_load_l002_service_schema_error(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "x").mkdir()
    (tmp_path / "organizations" / "x" / "config.yml").write_text(
        "id: x\n"
        "name: X\n"
        "kind: government\n"
        "networks: []\n"
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
    (tmp_path / "organizations" / "x").mkdir()
    (tmp_path / "organizations" / "x" / "config.yml").write_text(
        "id: x\n"
        "name: X\n"
        "kind: government\n"
        "networks: []\n"
        "services:\n"
        "  - id: svc\n"
        "    name: S\n"
        "    kind: web\n"
        "    exposure: public\n"
        "    host: svc.example\n"
        "    network_id: x-dmz\n"
        "links:\n"
        "  - from_service: svc\n"
        "    to_service: svc\n"
        "    kind: not-a-kind\n",
        encoding="utf-8",
    )
    network, issues = load_network(tmp_path)
    assert any(i.code == "L002" and "link" in i.message for i in issues)


def test_load_no_org_dirs(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    with pytest.raises(FileNotFoundError):
        load_network(tmp_path)


def test_service_assets_discovered(tiny_path: Path) -> None:
    loader = NetworkLoader(tiny_path)
    loader.load()
    assets = {a.svc_id: a for a in loader.service_assets}
    assert "hosp-web" in assets
    assert assets["hosp-web"].org_id == "hospital"
    assert (assets["hosp-web"].path / "nginx.conf").exists()


def test_orphan_service_asset_emits_warning(broken_path: Path) -> None:
    loader = NetworkLoader(broken_path)
    loader.load()
    warning = next(
        (i for i in loader.issues if i.code == "assets" and "orphan-service" in i.message),
        None,
    )
    assert warning is not None
    assert warning.level == "warning"


def test_load_final_assembly_validation_error(tmp_path: Path) -> None:
    """Bad version in YAML should fail final CityNetwork validation."""
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "x").mkdir()
    (tmp_path / "organizations" / "x" / "config.yml").write_text(
        "id: x\nname: X\nkind: government\nnetworks: []\nservices: []\n",
        encoding="utf-8",
    )
    # Direct CityNetwork construction with bad version should raise.
    with pytest.raises(ValidationError):
        CityNetwork(version="bad-version", organizations=[])


def test_loaded_network_can_be_allocated(tiny_path: Path) -> None:
    """After loading, the allocator can produce valid addressing."""
    network, _ = load_network(tiny_path)
    allocation = Allocator(network, seed=0).allocate()
    assert allocation.net_cidr
    assert allocation.svc_ip
