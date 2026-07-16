"""Build use case tests."""

from pathlib import Path

from cybercity_data.city_model.adapters.inbound.data.filesystem import FileSystemGateway
from cybercity_data.city_model.adapters.inbound.data.git import GitChangesGateway
from cybercity_data.city_model.adapters.inbound.data.loader import NetworkLoader
from cybercity_data.city_model.adapters.inbound.data.renderer import ArtifactRenderer
from cybercity_data.city_model.adapters.inbound.data.zip import EngineZipWriter
from cybercity_data.city_model.adapters.inbound.use_cases.build import BuildUseCase
from cybercity_data.city_model.adapters.inbound.use_cases.validate_step import ValidateCityStep


def _build_use_case(path: Path) -> BuildUseCase:
    loader = NetworkLoader(path)
    return BuildUseCase(
        validate_step=ValidateCityStep(loader),
        renderer=ArtifactRenderer(git=GitChangesGateway(path)),
        writer=FileSystemGateway(path),
        zip_writer=EngineZipWriter(),
    )


def test_build_creates_artifacts(tiny_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    use_case = _build_use_case(tiny_path)
    result = use_case.execute(tiny_path, out=out, strict=False, clean=False)
    assert result.ok, result.check.errors
    assert result.rendered is not None
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
        "engine.zip",
    ):
        assert (out / name).exists(), f"missing artifact: {name}"


def test_build_clean_removes_old_files(tiny_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    (out / "stale.txt").write_text("old", encoding="utf-8")
    use_case = _build_use_case(tiny_path)
    result = use_case.execute(tiny_path, out=out, strict=False, clean=True)
    assert result.ok
    assert not (out / "stale.txt").exists()
    assert (out / "network.json").exists()


def test_build_skipped_on_errors(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "x").mkdir()
    (tmp_path / "organizations" / "x" / "config.yml").write_text(
        "id: x\nname: X\nkind: government\nnetworks: []\nservices:\n"
        "  - id: svc\n    name: S\n    kind: web\n    exposure: public\n"
        "    host: svc.example\n    network_id: missing-net\nlinks: []\n",
        encoding="utf-8",
    )
    use_case = _build_use_case(tmp_path)
    result = use_case.execute(tmp_path, out=tmp_path / "build", strict=False, clean=False)
    assert not result.ok
    assert result.skipped_reason is not None
    assert not (tmp_path / "build" / "network.json").exists()

    strict_check = result.check.model_copy(
        update={"strict": True, "warnings": [result.check.errors[0]]}
    )
    strict_result = use_case._skip(strict_check)
    assert strict_result.skipped_reason is not None
    assert "warning(s) (strict mode)" in strict_result.skipped_reason
