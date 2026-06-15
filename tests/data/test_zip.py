"""Engine zip bundler tests."""

import json
import zipfile

from cybercity_data.data.filesystem import FileSystemGateway
from cybercity_data.data.loader import ServiceAssets
from cybercity_data.data.renderer import ArtifactRenderer
from cybercity_data.data.zip import EngineZipWriter


def test_render_includes_engine_zip_with_assets(tiny_network, tiny_allocation, tmp_path) -> None:
    assets = [
        ServiceAssets(
            svc_id="hosp-web",
            org_id="hospital",
            path=tmp_path / "fake-assets" / "hosp-web",
        )
    ]
    assets[0].path.mkdir(parents=True)
    (assets[0].path / "nginx.conf").write_text("server {}", encoding="utf-8")

    renderer = ArtifactRenderer()
    artifacts = renderer.render(tiny_network, tiny_allocation, assets)
    FileSystemGateway(tmp_path).write_artifacts(tmp_path, artifacts)

    zip_path = EngineZipWriter().bundle(tmp_path, artifacts, tiny_network, assets)
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
    renderer = ArtifactRenderer()
    artifacts = renderer.render(tiny_network, tiny_allocation, [])
    runtime = json.loads(artifacts["runtime/engine.json"])
    cour = next(s for s in runtime["services"] if s["id"] == "cour-web")
    hosp = next(s for s in runtime["services"] if s["id"] == "hosp-web")
    assert "hosp-web" in cour["can_reach"]
    assert "cour-web" in hosp["reachable_from"]
