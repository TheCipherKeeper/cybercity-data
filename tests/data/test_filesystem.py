"""Filesystem gateway tests."""

from pathlib import Path

import pytest

from cybercity_data.city_model.adapters.inbound.data.filesystem import (
    FileSystemGateway,
    InitTemplate,
)


def test_clean_directory_removes_children(tmp_path: Path) -> None:
    fs = FileSystemGateway(tmp_path)
    target = tmp_path / "out"
    target.mkdir()
    (target / "stale.txt").write_text("old", encoding="utf-8")
    (target / "subdir").mkdir()
    (target / "subdir" / "file.txt").write_text("x", encoding="utf-8")

    fs.clean_directory(target)

    assert target.exists()
    assert not (target / "stale.txt").exists()
    assert not (target / "subdir").exists()


def test_write_artifacts_creates_files(tmp_path: Path) -> None:
    fs = FileSystemGateway(tmp_path)
    artifacts = {"a.txt": "alpha", "b/c.txt": "gamma"}
    paths = fs.write_artifacts(tmp_path, artifacts)
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "alpha"
    assert (tmp_path / "b" / "c.txt").read_text(encoding="utf-8") == "gamma"
    assert len(paths) == 2


def test_write_artifacts_preserves_unchanged_mtime(tmp_path: Path) -> None:
    fs = FileSystemGateway(tmp_path)
    artifacts = {"x.txt": "same"}
    fs.write_artifacts(tmp_path, artifacts)
    first = (tmp_path / "x.txt").stat().st_mtime
    fs.write_artifacts(tmp_path, artifacts)
    second = (tmp_path / "x.txt").stat().st_mtime
    assert first == second


def test_ensure_organizations_root_missing(tmp_path: Path) -> None:
    fs = FileSystemGateway(tmp_path)
    with pytest.raises(FileNotFoundError):
        fs.ensure_organizations_root(tmp_path)


def test_ensure_organizations_root_ok(tmp_path: Path) -> None:
    fs = FileSystemGateway(tmp_path)
    (tmp_path / "organizations").mkdir()
    root = fs.ensure_organizations_root(tmp_path)
    assert root.name == "organizations"


def test_ensure_not_exists(tmp_path: Path) -> None:
    fs = FileSystemGateway(tmp_path)
    (tmp_path / "x").mkdir()
    with pytest.raises(FileExistsError):
        fs.ensure_not_exists(tmp_path / "x")
    fs.ensure_not_exists(tmp_path / "y")  # does not raise


def test_init_template_scaffold_empty() -> None:
    text = InitTemplate.scaffold("test-org", "government", empty=True)
    assert "id: test-org" in text
    assert "kind: government" in text
    assert "networks: []" in text
    assert "services: []" in text
    assert "links: []" in text


def test_init_template_scaffold_example() -> None:
    text = InitTemplate.scaffold("test-org", "finance", empty=False)
    assert "id: test-org" in text
    assert "kind: finance" in text
    assert "test-org-dmz" in text
    assert "test-org-web" in text


def test_init_template_write_config(tmp_path: Path) -> None:
    fs = FileSystemGateway(tmp_path)
    target = tmp_path / "organizations" / "new-org"
    (tmp_path / "organizations").mkdir()
    config_path = InitTemplate.write_config(fs, target, "new-org", "healthcare", False)
    assert config_path.exists()
    assert "id: new-org" in config_path.read_text(encoding="utf-8")
