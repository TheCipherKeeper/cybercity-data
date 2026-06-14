"""Builder tests: artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from cybercity_data import CityNetwork
from cybercity_data.build import Builder
from cybercity_data.models import Network, Organization, Service


def test_build_produces_all_artifacts(tiny_network, tmp_path) -> None:
    builder = Builder(tiny_network)
    artifacts = builder.build()
    for name in (
        "network.json",
        "network.md",
        "schema.json",
        "topology.json",
        "attack-surface.json",
    ):
        assert name in artifacts, f"missing artifact: {name}"

    builder.render(tmp_path)
    assert (tmp_path / "network.json").exists()
    assert (tmp_path / "network.md").exists()
    assert (tmp_path / "schema.json").exists()
    assert (tmp_path / "topology.json").exists()
    assert (tmp_path / "attack-surface.json").exists()


def test_json_is_valid_dump(tiny_network, tmp_path) -> None:
    Builder(tiny_network).render(tmp_path)
    data = json.loads((tmp_path / "network.json").read_text(encoding="utf-8"))
    assert data["version"] == "2.0.0"
    assert len(data["organizations"]) == 3
    assert len(data["services"]) == 4


def test_topology_shape(tiny_network, tmp_path) -> None:
    Builder(tiny_network).render(tmp_path)
    topo = json.loads((tmp_path / "topology.json").read_text(encoding="utf-8"))
    assert "source_version" in topo["meta"]
    assert "summary" in topo
    assert len(topo["nodes"]) == 4
    assert len(topo["edges"]) == 1
    node = topo["nodes"][0]
    assert "id" in node
    assert "org_id" in node
    assert "is_decoy" in node


def test_attack_surface_lists_public_weakness(tiny_network, tmp_path) -> None:
    Builder(tiny_network).render(tmp_path)
    report = json.loads(
        (tmp_path / "attack-surface.json").read_text(encoding="utf-8")
    )
    assert "count" in report
    # tiny fixture has two public web services with auth=local (default).
    assert report["count"] >= 2


def test_markdown_has_sections(tiny_network, tmp_path) -> None:
    Builder(tiny_network).render(tmp_path)
    text = (tmp_path / "network.md").read_text(encoding="utf-8")
    for header in [
        "# CyberCity — Network Projection",
        "## Сводка",
        "## Сети",
        "## Организации",
        "## Сетевая связность",
        "## Сервисы",
        "## Decoy-хосты",
    ]:
        assert header in text, f"missing section: {header}"


def test_schema_is_valid_json_schema(tiny_network, tmp_path) -> None:
    Builder(tiny_network).render(tmp_path)
    schema = json.loads((tmp_path / "schema.json").read_text(encoding="utf-8"))
    # Pydantic v2 emits JSON Schema draft 2020-12; CityNetwork is the top title.
    assert schema.get("title") == "CityNetwork"
    assert "$defs" in schema
    assert "Service" in schema["$defs"]


def test_topology_summary_matches(tiny_network, tmp_path) -> None:
    Builder(tiny_network).render(tmp_path)
    topo = json.loads((tmp_path / "topology.json").read_text(encoding="utf-8"))
    summary = topo["summary"]
    assert summary["organizations"] == 3
    assert summary["services"] == 4
    assert summary["links"] == 1
    assert summary["decoys"] == 1


def test_attack_surface_empty_when_no_public_weak() -> None:
    network = CityNetwork(
        version="2.0.0",
        organizations=[
            Organization(
                id="a",
                name="A",
                kind="finance",
                segment="corp",
                networks=[
                    Network(id="a-dmz", org_id="a", kind="dmz", cidr="10.10.1.0/24")
                ],
            )
        ],
        services=[
            Service(
                id="svc",
                org_id="a",
                name="S",
                kind="web",
                exposure="intranet",
                host="svc.a.corp",
                network_id="a-dmz",
                bind_ip="10.10.1.10",
            )
        ],
    )
    content = Builder(network).build()["attack-surface.json"]
    report = json.loads(content)
    assert report["count"] == 0


def test_render_preserves_unchanged_files(tiny_network, tmp_path) -> None:
    builder = Builder(tiny_network)
    builder.render(tmp_path)
    first = (tmp_path / "network.json").stat().st_mtime

    builder.render(tmp_path)
    second = (tmp_path / "network.json").stat().st_mtime
    assert second == first


def test_attack_surface_skips_decoy(tiny_network: CityNetwork, tmp_path: Path) -> None:
    """A public decoy must not appear in attack-surface report."""
    from cybercity_data.models import Service

    # Create a public-facing decoy service.
    decoy = Service(
        id="public-decoy",
        org_id="city-hospital",
        name="Public decoy",
        kind="web",
        exposure="public",
        host="decoy.example",
        network_id="city-hospital-dmz",
        bind_ip="10.10.10.15",
        decoy={"kind": "http", "fingerprint": "realistic"},
    )
    network = tiny_network.model_copy(
        update={"services": [*tiny_network.services, decoy]}
    )
    report = json.loads(Builder(network).build()["attack-surface.json"])
    assert not any(i["id"] == "public-decoy" for i in report["items"])


def test_build_artifacts_free_function(tiny_network, tmp_path: Path) -> None:
    from cybercity_data.build import build_artifacts

    paths = build_artifacts(tiny_network, tmp_path)
    assert len(paths) == 5
    assert all((tmp_path / p.name).exists() for p in paths)
