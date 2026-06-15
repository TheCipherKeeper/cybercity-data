"""Engine runtime package bundler."""

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from ..domain.models import CityNetwork
from .loader import ServiceAssets


class EngineZipWriter:
    """Bundle every artifact plus optional service assets into `engine.zip`."""

    def bundle(
        self,
        target: Path,
        artifacts: dict[str, str],
        network: CityNetwork,
        service_assets: list[ServiceAssets],
    ) -> Path:
        """Create `target/engine.zip` and return its path."""
        zip_path = target / "engine.zip"
        ts = datetime.now(UTC).isoformat()
        manifest = {
            "schema_version": 1,
            "generated_at": ts,
            "source_version": network.version,
            "summary": {
                "organizations": len(network.organizations),
                "networks": sum(len(o.networks) for o in network.organizations),
                "services": len(network.services),
                "links": len(network.links),
                "asset_dirs": len(service_assets),
            },
            "files": {
                "model/network.json": "canonical CityNetwork dump",
                "model/topology.json": "clean graph for UI/simulator",
                "model/schema.json": "JSON Schema for validation",
                "runtime/engine.json": "engine runtime configuration",
                "security/attack-surface.json": "publicly exposed services",
                "views/network.md": "human-readable projection",
                "views/network.html": "self-contained interactive viewer",
                "views/inventory.md": "asset inventory",
                "changes.json": "diff against previous build",
                "manifest.json": "this file",
            },
        }

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
            zf.writestr("model/network.json", artifacts["network.json"])
            zf.writestr("model/topology.json", artifacts["topology.json"])
            zf.writestr("model/schema.json", artifacts["schema.json"])
            zf.writestr("runtime/engine.json", artifacts["runtime/engine.json"])
            zf.writestr("security/attack-surface.json", artifacts["attack-surface.json"])
            zf.writestr("views/network.md", artifacts["network.md"])
            zf.writestr("views/network.html", artifacts["network.html"])
            zf.writestr("views/inventory.md", artifacts["inventory.md"])
            zf.writestr("changes.json", artifacts["changes.json"])

            for asset in service_assets:
                for file in sorted(asset.path.rglob("*")):
                    if file.is_file():
                        rel_path = file.relative_to(asset.path).as_posix()
                        arcname = f"assets/services/{asset.org_id}/{asset.svc_id}/{rel_path}"
                        zf.write(file, arcname=arcname)

        return zip_path
