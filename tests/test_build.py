"""Builder tests: artifacts."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from cybercity_data.allocator import Allocator
from cybercity_data.build import Builder
from cybercity_data.loader import ServiceAssets


def test_build_produces_all_artifacts(tiny_network, tiny_allocation, tmp_path) -> None:
    builder = Builder(tiny_network, allocation=tiny_allocation)
    artifacts = builder.build()
    for name in (
        "network.json",
        "network.md",
        "schema.json",
        "topology.json",
        "network.html",
        "attack-surface.json",
        "inventory.md",
        "changes.json",
    ):
        assert name in artifacts, f"missing artifact: {name}"

    builder.render(tmp_path)
    for name in (
        "network.json",
        "network.md",
        "schema.json",
        "topology.json",
        "network.html",
        "attack-surface.json",
        "inventory.md",
        "changes.json",
        "engine.zip",
    ):
        assert (tmp_path / name).exists(), f"missing rendered file: {name}"


def test_attack_surface_only_public(tiny_network, tiny_allocation, tmp_path) -> None:
    Builder(tiny_network, allocation=tiny_allocation).render(tmp_path)
    surface = json.loads((tmp_path / "attack-surface.json").read_text(encoding="utf-8"))
    assert surface["schema_version"] == 1
    assert all(s["exposure"] == "public" for s in surface["services"])
    ids = {s["id"] for s in surface["services"]}
    assert ids <= {"hosp-web", "cour-web"}


def test_attack_surface_includes_software(tiny_network, tiny_allocation, tmp_path) -> None:
    from cybercity_data.models import Service, Software

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
        software=Software(
            vendor="acme", product="api", version="1.0.0", cve_id="CVE-2024-1234"
        ),
    )
    network = tiny_network.model_copy(
        update={"services": [*tiny_network.services, public_with_sw]}
    )
    allocation = Allocator(network, seed=0).allocate()
    Builder(network, allocation=allocation).render(tmp_path)
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
    Builder(tiny_network, allocation=tiny_allocation, service_assets=assets).render(tmp_path)
    text = (tmp_path / "inventory.md").read_text(encoding="utf-8")
    assert "# CyberCity — Asset Inventory" in text
    assert "hosp-web" in text


def test_changes_shape(tiny_network, tiny_allocation, tmp_path) -> None:
    Builder(tiny_network, allocation=tiny_allocation).render(tmp_path)
    changes = json.loads((tmp_path / "changes.json").read_text(encoding="utf-8"))
    assert changes["schema_version"] == 1
    assert "summary" in changes
    for key in ("organizations", "services", "links"):
        assert key in changes["summary"]
        for sub in ("added", "removed", "modified"):
            assert sub in changes["summary"][key]


def test_changes_with_previous_build(tiny_network, tiny_allocation, tmp_path, monkeypatch) -> None:
    previous = tiny_network.model_copy(update={"services": tiny_network.services[:1]})
    monkeypatch.setattr(
        Builder,
        "_previous_network_json",
        lambda _self: previous.model_dump_json(),
    )
    Builder(tiny_network, allocation=tiny_allocation).render(tmp_path)
    changes = json.loads((tmp_path / "changes.json").read_text(encoding="utf-8"))
    assert changes["previous_ref"] is not None or changes["previous_ref"] is None
    assert changes["summary"]["services"]["removed"] >= 0
    assert changes["summary"]["services"]["added"] >= 0


def test_json_is_valid_dump(tiny_network, tiny_allocation, tmp_path) -> None:
    Builder(tiny_network, allocation=tiny_allocation).render(tmp_path)
    data = json.loads((tmp_path / "network.json").read_text(encoding="utf-8"))
    assert data["version"] == "3.0.0"
    assert len(data["organizations"]) == 3
    assert len(data["services"]) == 4
    assert "meta" not in data
    assert "known_weakness" not in data["services"][0]


def test_topology_shape(tiny_network, tiny_allocation, tmp_path) -> None:
    Builder(tiny_network, allocation=tiny_allocation).render(tmp_path)
    topo = json.loads((tmp_path / "topology.json").read_text(encoding="utf-8"))
    assert "source_version" in topo["meta"]
    assert "summary" in topo
    assert len(topo["nodes"]) == 4
    assert len(topo["edges"]) == 1
    node = topo["nodes"][0]
    assert "id" in node
    assert "org_id" in node
    assert "is_mock" in node
    assert "known_weakness" not in node
    assert "attack_chain" not in topo["edges"][0]


def test_markdown_has_sections(tiny_network, tiny_allocation, tmp_path) -> None:
    Builder(tiny_network, allocation=tiny_allocation).render(tmp_path)
    text = (tmp_path / "network.md").read_text(encoding="utf-8")
    for header in [
        "# CyberCity — Network Projection",
        "## Сводка",
        "## Сети",
        "## Организации",
        "## Сетевая связность",
        "## Сервисы",
        "## Имитационные сервисы",
    ]:
        assert header in text, f"missing section: {header}"


def test_schema_is_valid_json_schema(tiny_network, tiny_allocation, tmp_path) -> None:
    Builder(tiny_network, allocation=tiny_allocation).render(tmp_path)
    schema = json.loads((tmp_path / "schema.json").read_text(encoding="utf-8"))
    # Pydantic v2 emits JSON Schema draft 2020-12; CityNetwork is the top title.
    assert schema.get("title") == "CityNetwork"
    assert "$defs" in schema
    assert "Service" in schema["$defs"]


def test_topology_summary_matches(tiny_network, tiny_allocation, tmp_path) -> None:
    Builder(tiny_network, allocation=tiny_allocation).render(tmp_path)
    topo = json.loads((tmp_path / "topology.json").read_text(encoding="utf-8"))
    summary = topo["summary"]
    assert summary["organizations"] == 3
    assert summary["services"] == 4
    assert summary["links"] == 1
    assert summary["mock_services"] == 1


def test_render_preserves_unchanged_files(tiny_network, tiny_allocation, tmp_path) -> None:
    builder = Builder(tiny_network, allocation=tiny_allocation)
    builder.render(tmp_path)
    first = (tmp_path / "network.json").stat().st_mtime

    builder.render(tmp_path)
    second = (tmp_path / "network.json").stat().st_mtime
    assert second == first


def test_build_artifacts_free_function(tiny_network, tiny_allocation, tmp_path: Path) -> None:
    from cybercity_data.build import build_artifacts

    paths = build_artifacts(tiny_network, tmp_path, allocation=tiny_allocation)
    assert len(paths) == 9
    assert all((tmp_path / p.name).exists() for p in paths)


def test_render_includes_engine_zip_with_assets(
    tiny_network, tiny_allocation, tmp_path
) -> None:
    assets = [
        ServiceAssets(
            svc_id="hosp-web",
            org_id="hospital",
            path=tmp_path / "fake-assets" / "hosp-web",
        )
    ]
    assets[0].path.mkdir(parents=True)
    (assets[0].path / "nginx.conf").write_text("server {}", encoding="utf-8")

    builder = Builder(tiny_network, allocation=tiny_allocation, service_assets=assets)
    builder.render(tmp_path)
    zip_path = tmp_path / "engine.zip"
    assert zip_path.exists()

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        assert "model/network.json" in names
        assert "model/topology.json" in names
        assert "model/schema.json" in names
        assert "runtime/engine.json" in names
        assert "views/network.md" in names
        assert "views/network.html" in names
        assert "views/inventory.md" in names
        assert "security/attack-surface.json" in names
        assert "changes.json" in names
        assert any("assets/services/hospital/hosp-web/nginx.conf" in n for n in names)

        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert manifest["schema_version"] == 1
        assert manifest["summary"]["asset_dirs"] == 1

        runtime = json.loads(zf.read("runtime/engine.json").decode("utf-8"))
        assert runtime["schema_version"] == 1
        assert runtime["tick_ms"] == 1000
        assert any(s["id"] == "hosp-web" for s in runtime["services"])


def test_engine_runtime_reachability(tiny_network, tiny_allocation, tmp_path) -> None:
    builder = Builder(tiny_network, allocation=tiny_allocation, service_assets=[])
    builder.render(tmp_path)
    # tiny fixture: cour-web -> hosp-web (auth)
    runtime = json.loads(builder._build_runtime())
    cour = next(s for s in runtime["services"] if s["id"] == "cour-web")
    hosp = next(s for s in runtime["services"] if s["id"] == "hosp-web")
    assert "hosp-web" in cour["can_reach"]
    assert "cour-web" in hosp["reachable_from"]


def test_html_viewer_is_self_contained(tiny_network, tiny_allocation, tmp_path) -> None:
    """network.html must work from file:// without external fetch/CDN."""
    import re

    Builder(tiny_network, allocation=tiny_allocation).render(tmp_path)
    html = (tmp_path / "network.html").read_text(encoding="utf-8")
    assert "const TOPOLOGY = {" in html
    assert "!function(t,n){" in html  # inlined D3 bundle
    assert re.search(r"fetch\s*\(\s*['\"]topology\.json", html) is None
    assert re.search(r"<script[^>]*src\s*=\s*['\"]https?://", html) is None
    assert "topology.json" not in html
