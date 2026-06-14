"""CLI tests via typer.testing.CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cybercity_data.cli import app

runner = CliRunner()


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _make_broken_repo(root: Path) -> None:
    """Minimal repo that triggers validator errors (ids + refs) -> exit 1."""
    (root / "organizations").mkdir(parents=True)
    for org_id, label, idx in (("x-a", "A", 1), ("x-b", "B", 2)):
        (root / "organizations" / org_id).mkdir()
        _write(
            root / "organizations" / org_id / "config.yml",
            f"id: {org_id}\n"
            f"name: City {label}\n"
            "kind: finance\n"
            f"network_index: {idx}\n"
            "networks:\n"
            f"  - id: {org_id}-dmz\n"
            "    kind: dmz\n"
            f"    cidr: 10.{idx}.{idx}.0/24\n"
            "services:\n"
            f"  - id: web\n"
            f"    name: {label} web\n"
            "    kind: web\n"
            "    exposure: public\n"
            f"    host: {label.lower()}.example\n"
            f"    network_id: {org_id}-dmz\n"
            f"    bind_ip: 10.{idx}.{idx}.10\n"
            + (
                "links:\n"
                "  - from_service: web\n"
                "    to_service: ghost\n"
                "    kind: api-call\n"
                "    protocol: tcp/443\n"
                if org_id == "x-b"
                else ""
            ),
        )


def _make_minimal_repo(root: Path) -> None:
    """Minimal valid repo with one org."""
    (root / "organizations").mkdir(parents=True)
    (root / "organizations" / "x").mkdir()
    _write(
        root / "organizations" / "x" / "config.yml",
        "id: x\n"
        "name: X\n"
        "kind: government\n"
        "network_index: 1\n"
        "networks:\n"
        "  - id: x-dmz\n"
        "    kind: dmz\n"
        "    cidr: 10.1.1.0/24\n"
        "services:\n"
        "  - id: web\n"
        "    name: Web\n"
        "    kind: web\n"
        "    exposure: public\n"
        "    host: web.example\n"
        "    network_id: x-dmz\n"
        "    bind_ip: 10.1.1.10\n",
    )


def test_check_ok_on_tiny(tiny_path: Path) -> None:
    result = runner.invoke(app, ["check", str(tiny_path)])
    assert result.exit_code == 0, result.output
    assert "0 errors" in result.output


def test_check_exits_1_on_validation_errors(broken_path: Path) -> None:
    result = runner.invoke(app, ["check", str(broken_path)])
    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    assert "ids" in combined
    assert "refs" in combined


def test_check_exits_1_on_missing_organizations(tmp_path: Path) -> None:
    result = runner.invoke(app, ["check", str(tmp_path)])
    assert result.exit_code == 1


def test_check_json_shape_on_tiny(tiny_path: Path) -> None:
    result = runner.invoke(app, ["check", str(tiny_path), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["exit_code"] == 0
    assert data["path"] == str(tiny_path)
    assert data["counts"] == {
        "organizations": 3,
        "networks": 3,
        "services": 4,
        "links": 1,
    }
    assert data["errors"] == []
    assert data["warnings"] == []


def test_build_creates_artifacts(tiny_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = runner.invoke(app, ["build", str(tiny_path), "--out", str(out)])
    assert result.exit_code == 0, result.output
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
        assert (out / name).exists(), f"missing artifact: {name}"
    assert (out / "engine.zip").exists(), "missing engine.zip"


def test_build_clean_removes_old_files(tiny_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    (out / "stale.txt").write_text("old", encoding="utf-8")
    result = runner.invoke(
        app, ["build", str(tiny_path), "--out", str(out), "--clean"]
    )
    assert result.exit_code == 0, result.output
    assert not (out / "stale.txt").exists()
    assert (out / "network.json").exists()


def test_build_skipped_on_errors(tmp_path: Path) -> None:
    _make_broken_repo(tmp_path)
    out = tmp_path / "build"
    result = runner.invoke(app, ["build", str(tmp_path), "--out", str(out)])
    assert result.exit_code == 1
    assert not (out / "network.json").exists()


def test_init_creates_example_org(tiny_path: Path, tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    result = runner.invoke(
        app,
        [
            "init",
            "hospital",
            "--kind",
            "healthcare",
            "--network-index",
            "10",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    cfg = tmp_path / "organizations" / "hospital" / "config.yml"
    assert cfg.exists()
    text = cfg.read_text(encoding="utf-8")
    assert "id: hospital" in text
    assert "kind: healthcare" in text
    assert "network_index: 10" in text
    assert "hospital-dmz" in text
    assert "hospital-web" in text


def test_init_creates_empty_org_with_flag(tiny_path: Path, tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    result = runner.invoke(
        app,
        [
            "init",
            "hospital",
            "--kind",
            "healthcare",
            "--network-index",
            "10",
            "--path",
            str(tmp_path),
            "--empty",
        ],
    )
    assert result.exit_code == 0, result.output
    cfg = tmp_path / "organizations" / "hospital" / "config.yml"
    text = cfg.read_text(encoding="utf-8")
    assert "networks: []" in text
    assert "services: []" in text
    assert "links: []" in text


def test_check_json_on_missing_dir(tmp_path: Path) -> None:
    result = runner.invoke(app, ["check", str(tmp_path), "--json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["ok"] is False
    assert data["exit_code"] == 1
    assert "error" in data


def test_check_exits_1_on_bad_yaml(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "organizations" / "x" / "config.yml", "not: valid: yaml: [\n")
    result = runner.invoke(app, ["check", str(tmp_path)])
    assert result.exit_code == 1


def test_check_exits_1_on_schema_error(tmp_path: Path) -> None:
    """Bad organization kind -> loader/schema error -> exit 1."""
    _make_minimal_repo(tmp_path)
    _write(
        tmp_path / "organizations" / "x" / "config.yml",
        "id: x\nname: X\nkind: not-a-kind\nnetwork_index: 1\nnetworks: []\nservices: []\n",
    )
    result = runner.invoke(app, ["check", str(tmp_path)])
    assert result.exit_code == 1
    assert "L002" in result.output


def test_check_json_includes_rendered_paths(tiny_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = runner.invoke(
        app, ["build", str(tiny_path), "--out", str(out), "--json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True
    assert "rendered" in data
    assert any(str(out) in p for p in data["rendered"])


def test_init_fails_without_organizations(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            "x",
            "--kind",
            "government",
            "--network-index",
            "1",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1


def test_init_fails_when_org_exists(tiny_path: Path, tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "x").mkdir()
    result = runner.invoke(
        app,
        [
            "init",
            "x",
            "--kind",
            "government",
            "--network-index",
            "1",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1


def test_check_exits_1_on_internal_error(tmp_path: Path, monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("simulated internal failure")

    monkeypatch.setattr("cybercity_data.cli._load", boom)
    result = runner.invoke(app, ["check", str(tmp_path)])
    assert result.exit_code == 1
    assert "simulated internal failure" in result.output


def test_check_exits_1_on_yaml_error(tmp_path: Path, monkeypatch) -> None:
    import yaml

    def boom(*_args, **_kwargs):
        raise yaml.YAMLError("simulated yaml failure")

    monkeypatch.setattr("cybercity_data.cli._load", boom)
    result = runner.invoke(app, ["check", str(tmp_path)])
    assert result.exit_code == 1
    assert "YAML error" in result.output


def test_check_exits_1_on_validation_error(tmp_path: Path, monkeypatch) -> None:
    from pydantic import ValidationError

    def boom(*_args, **_kwargs):
        raise ValidationError.from_exception_data("CityNetwork", [])

    monkeypatch.setattr("cybercity_data.cli._load", boom)
    result = runner.invoke(app, ["check", str(tmp_path)])
    assert result.exit_code == 1
    assert "schema errors" in result.output


def test_build_exits_1_on_internal_render_error(
    tiny_path: Path, tmp_path: Path, monkeypatch
) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("render boom")

    monkeypatch.setattr("cybercity_data.cli.Builder.render", boom)
    out = tmp_path / "out"
    result = runner.invoke(app, ["build", str(tiny_path), "--out", str(out)])
    assert result.exit_code == 1
    assert "render boom" in result.output


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "cybercity-data 0.4.0" in result.output
