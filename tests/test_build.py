"""Builder tests: artifacts."""

from __future__ import annotations

import json

from cybercity_data.build import Builder


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
    assert data["meta"]["city"] == "cybercity"
    assert len(data["organizations"]) == 3
    assert len(data["services"]) == 4


def test_topology_shape(tiny_network, tmp_path) -> None:
    Builder(tiny_network).render(tmp_path)
    topo = json.loads((tmp_path / "topology.json").read_text(encoding="utf-8"))
    assert topo["meta"]["city"] == "cybercity"
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
