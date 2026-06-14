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
    _write(
        root / "organizations" / "city.yml",
        'version: "1.0.0"\n'
        "meta:\n"
        "  city: x\n"
        "  allocation:\n"
        "    corp: 10.10.0.0/16\n"
        "    ot: 10.20.0.0/16\n"
        "    mgmt: 10.30.0.0/16\n"
        "    internet: 203.0.113.0/24\n",
    )
    for org_id, label in (("city-a", "A"), ("city-b", "B")):
        (root / "organizations" / org_id).mkdir()
        _write(
            root / "organizations" / org_id / "config.yml",
            f"id: {org_id}\n"
            f"name: City {label}\n"
            "kind: finance\n"
            "segment: corp\n"
            "services:\n"
            f"  - id: web\n"
            f"    name: {label} web\n"
            "    kind: web\n"
            "    exposure: public\n"
            f"    host: {label.lower()}.example\n"
            + (
                "links:\n"
                "  - from_service: web\n"
                "    to_service: ghost\n"
                "    kind: api-call\n"
                "    protocol: tcp/443\n"
                if org_id == "city-b"
                else ""
            ),
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
        "networks": 8,
        "services": 4,
        "links": 1,
    }
    assert data["errors"] == []


def test_build_creates_artifacts(tiny_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = runner.invoke(app, ["build", str(tiny_path), "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / "network.json").exists()
    assert (out / "network.md").exists()
    assert (out / "schema.json").exists()
    assert (out / "topology.json").exists()
    assert (out / "attack-surface.json").exists()


def test_build_skipped_on_errors(tmp_path: Path) -> None:
    _make_broken_repo(tmp_path)
    out = tmp_path / "build"
    result = runner.invoke(app, ["build", str(tmp_path), "--out", str(out)])
    assert result.exit_code == 1
    assert not (out / "network.json").exists()


def test_strict_mode_fails_on_warnings(tiny_path: Path) -> None:
    result = runner.invoke(app, ["check", str(tiny_path), "--strict"])
    assert result.exit_code == 1, result.output
    assert "quota" in result.output


def test_init_creates_org(tiny_path: Path, tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "city.yml").write_text(
        'version: "1.0.0"\nmeta:\n  city: x\n  allocation:\n'
        "    corp: 10.10.0.0/16\n"
        "    ot: 10.20.0.0/16\n"
        "    mgmt: 10.30.0.0/16\n"
        "    internet: 203.0.113.0/24\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        [
            "init",
            "city-hospital",
            "--kind",
            "healthcare",
            "--segment",
            "corp",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    cfg = tmp_path / "organizations" / "city-hospital" / "config.yml"
    assert cfg.exists()
    text = cfg.read_text(encoding="utf-8")
    assert "id: city-hospital" in text
    assert "kind: healthcare" in text
    assert "segment: corp" in text


def test_check_json_on_missing_dir(tmp_path: Path) -> None:
    result = runner.invoke(app, ["check", str(tmp_path), "--json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["ok"] is False
    assert data["exit_code"] == 1
    assert "error" in data


def test_check_exits_1_on_bad_city_yaml(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir(parents=True)
    _write(tmp_path / "organizations" / "city.yml", "not: valid: yaml: [\n")
    result = runner.invoke(app, ["check", str(tmp_path)])
    assert result.exit_code == 1


def test_build_strict_skips_on_warnings(tiny_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = runner.invoke(
        app, ["build", str(tiny_path), "--out", str(out), "--strict"]
    )
    assert result.exit_code == 1, result.output
    assert not (out / "network.json").exists()


def test_build_strict_json_includes_render_skipped(tiny_path: Path) -> None:
    result = runner.invoke(
        app, ["build", str(tiny_path), "--json", "--strict"]
    )
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["ok"] is False
    assert "render_skipped" in data


def test_init_fails_without_organizations(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            "city-x",
            "--kind",
            "government",
            "--segment",
            "corp",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1


def test_init_fails_when_org_exists(tiny_path: Path, tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "city.yml").write_text(
        'version: "1.0.0"\nmeta:\n  city: x\n  allocation:\n'
        "    corp: 10.10.0.0/16\n"
        "    ot: 10.20.0.0/16\n"
        "    mgmt: 10.30.0.0/16\n"
        "    internet: 203.0.113.0/24\n",
        encoding="utf-8",
    )
    (tmp_path / "organizations" / "city-x").mkdir()
    result = runner.invoke(
        app,
        [
            "init",
            "city-x",
            "--kind",
            "government",
            "--segment",
            "corp",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1


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


def test_check_exits_1_on_schema_error(tmp_path: Path) -> None:
    """City meta missing allocation -> ValidationError -> exit 1."""
    (tmp_path / "organizations").mkdir(parents=True)
    _write(
        tmp_path / "organizations" / "city.yml",
        'version: "1.0.0"\nmeta:\n  city: x\n',
    )
    (tmp_path / "organizations" / "city-x").mkdir()
    _write(
        tmp_path / "organizations" / "city-x" / "config.yml",
        "id: city-x\nname: X\nkind: government\nsegment: corp\nservices: []\n",
    )
    result = runner.invoke(app, ["check", str(tmp_path)])
    assert result.exit_code == 1
    assert "schema errors" in result.output


def test_check_exits_1_on_internal_error(tmp_path: Path, monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("simulated internal failure")

    monkeypatch.setattr("cybercity_data.cli._load", boom)
    result = runner.invoke(app, ["check", str(tmp_path)])
    assert result.exit_code == 1
    assert "simulated internal failure" in result.output


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
    assert "cybercity-data 0.3.0" in result.output
