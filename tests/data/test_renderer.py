"""Renderer tests: artifact content generation."""

import json
from pathlib import Path

from cybercity_data.city_model.adapters.inbound.data.filesystem import FileSystemGateway
from cybercity_data.city_model.adapters.inbound.data.loader import ServiceAssets
from cybercity_data.city_model.adapters.inbound.data.renderer import ArtifactRenderer
from cybercity_data.city_model.adapters.inbound.domain.allocator import Allocator
from cybercity_data.city_model.adapters.inbound.domain.models import Service, Software


def _render(
    renderer: ArtifactRenderer, network, allocation, assets, tmp_path: Path
) -> dict[str, str]:
    artifacts = renderer.render(network, allocation, assets)
    FileSystemGateway(tmp_path).write_artifacts(tmp_path, artifacts)
    return artifacts


def test_render_produces_all_artifacts(tiny_network, tiny_allocation, tmp_path) -> None:
    renderer = ArtifactRenderer()
    artifacts = _render(renderer, tiny_network, tiny_allocation, [], tmp_path)
    for name in (
        "network.json",
        "network.md",
        "schema.json",
        "topology.json",
        "network.html",
        "attack-surface.json",
        "inventory.md",
        "changes.json",
        "runtime/engine.json",
    ):
        assert name in artifacts, f"missing artifact: {name}"
        assert (tmp_path / name).exists(), f"missing rendered file: {name}"


def test_attack_surface_only_public(tiny_network, tiny_allocation, tmp_path) -> None:
    renderer = ArtifactRenderer()
    _render(renderer, tiny_network, tiny_allocation, [], tmp_path)
    surface = json.loads((tmp_path / "attack-surface.json").read_text(encoding="utf-8"))
    assert surface["schema_version"] == 1
    assert all(s["exposure"] == "public" for s in surface["services"])
    ids = {s["id"] for s in surface["services"]}
    assert ids <= {"hosp-web", "cour-web"}


def test_attack_surface_includes_software(tiny_network, tiny_allocation, tmp_path) -> None:
    org = next(o for o in tiny_network.organizations if o.id == "hospital")
    dmz = next(n for n in org.networks if n.kind == "dmz")
    public_with_sw = Service(
        id="hosp-api",
        org_id="hospital",
        name="Hospital API",
        kind="api",
        exposure="public",
        host="api.hospital.corp",
        network_id=dmz.id,
        software=Software(vendor="acme", product="api", version="1.0.0", cve_id="CVE-2024-1234"),
    )
    network = tiny_network.model_copy(update={"services": [*tiny_network.services, public_with_sw]})
    allocation = Allocator(network, seed=0).allocate()
    renderer = ArtifactRenderer()
    _render(renderer, network, allocation, [], tmp_path)
    surface = json.loads((tmp_path / "attack-surface.json").read_text(encoding="utf-8"))
    svc = next(s for s in surface["services"] if s["id"] == "hosp-api")
    assert svc["software"]["vendor"] == "acme"
    assert svc["software"]["cve_id"] == "CVE-2024-1234"


def test_inventory_lists_assets(tiny_network, tiny_allocation, tmp_path) -> None:
    assets = [
        ServiceAssets(
            svc_id="hosp-web",
            org_id="hospital",
            path=tmp_path / "assets" / "hosp-web",
        )
    ]
    assets[0].path.mkdir(parents=True)
    (assets[0].path / "nginx.conf").write_text("server {}", encoding="utf-8")
    renderer = ArtifactRenderer()
    _render(renderer, tiny_network, tiny_allocation, assets, tmp_path)
    text = (tmp_path / "inventory.md").read_text(encoding="utf-8")
    assert "# CyberCity — Asset Inventory" in text
    assert "hosp-web" in text


def test_changes_shape(tiny_network, tiny_allocation, tmp_path) -> None:
    renderer = ArtifactRenderer()
    _render(renderer, tiny_network, tiny_allocation, [], tmp_path)
    changes = json.loads((tmp_path / "changes.json").read_text(encoding="utf-8"))
    assert changes["schema_version"] == 1
    assert "summary" in changes
    for key in ("organizations", "services", "links"):
        assert key in changes["summary"]
        for sub in ("added", "removed", "modified"):
            assert sub in changes["summary"][key]


def test_json_is_valid_dump(tiny_network, tiny_allocation, tmp_path) -> None:
    renderer = ArtifactRenderer()
    _render(renderer, tiny_network, tiny_allocation, [], tmp_path)
    data = json.loads((tmp_path / "network.json").read_text(encoding="utf-8"))
    assert data["version"] == "3.0.0"
    assert len(data["organizations"]) == 3
    assert len(data["services"]) == 4
    assert "meta" not in data
    assert "known_weakness" not in data["services"][0]


def test_topology_shape(tiny_network, tiny_allocation, tmp_path) -> None:
    renderer = ArtifactRenderer()
    _render(renderer, tiny_network, tiny_allocation, [], tmp_path)
    topo = json.loads((tmp_path / "topology.json").read_text(encoding="utf-8"))
    assert "source_version" in topo["meta"]
    assert "summary" in topo
    assert len(topo["nodes"]) == 4
    assert len(topo["edges"]) == 1
    node = topo["nodes"][0]
    assert "id" in node
    assert "org_id" in node
    assert "is_honeypot" in node
    assert "known_weakness" not in node
    assert "attack_chain" not in topo["edges"][0]


def test_markdown_has_sections(tiny_network, tiny_allocation, tmp_path) -> None:
    renderer = ArtifactRenderer()
    _render(renderer, tiny_network, tiny_allocation, [], tmp_path)
    text = (tmp_path / "network.md").read_text(encoding="utf-8")
    for header in [
        "# CyberCity — Network Projection",
        "## Сводка",
        "## Сети",
        "## Организации",
        "## Сетевая связность",
        "## Сервисы",
        "## Honeypot-сервисы",
    ]:
        assert header in text, f"missing section: {header}"


def test_schema_is_valid_json_schema(tiny_network, tiny_allocation, tmp_path) -> None:
    renderer = ArtifactRenderer()
    _render(renderer, tiny_network, tiny_allocation, [], tmp_path)
    schema = json.loads((tmp_path / "schema.json").read_text(encoding="utf-8"))
    # Pydantic v2 emits JSON Schema draft 2020-12; CityNetwork is the top title.
    assert schema.get("title") == "CityNetwork"
    assert "$defs" in schema
    assert "Service" in schema["$defs"]


def test_topology_summary_matches(tiny_network, tiny_allocation, tmp_path) -> None:
    renderer = ArtifactRenderer()
    _render(renderer, tiny_network, tiny_allocation, [], tmp_path)
    topo = json.loads((tmp_path / "topology.json").read_text(encoding="utf-8"))
    summary = topo["summary"]
    assert summary["organizations"] == 3
    assert summary["services"] == 4
    assert summary["links"] == 1
    assert summary["honeypot_services"] == 1


def test_render_preserves_unchanged_files(tiny_network, tiny_allocation, tmp_path) -> None:
    renderer = ArtifactRenderer()
    artifacts = renderer.render(tiny_network, tiny_allocation, [])
    fs = FileSystemGateway(tmp_path)
    fs.write_artifacts(tmp_path, artifacts)
    first = (tmp_path / "network.json").stat().st_mtime

    fs.write_artifacts(tmp_path, artifacts)
    second = (tmp_path / "network.json").stat().st_mtime
    assert second == first


def test_build_artifacts_free_function(tiny_network, tiny_allocation, tmp_path: Path) -> None:
    from cybercity_data.city_model.adapters.inbound.data.renderer import build_artifacts

    paths = build_artifacts(tiny_network, tmp_path, allocation=tiny_allocation)
    assert len(paths) == 10
    assert all((tmp_path / p).exists() for p in paths)
