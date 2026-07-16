"""Init use case tests."""

from pathlib import Path

from cybercity_data.city_model.adapters.inbound.data.filesystem import FileSystemGateway
from cybercity_data.city_model.adapters.inbound.use_cases.init import InitUseCase


def test_init_creates_example_org(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    use_case = InitUseCase(FileSystemGateway(tmp_path))
    result = use_case.execute(tmp_path, "hospital", "healthcare", empty=False)
    assert result.ok
    assert result.config_path is not None
    text = result.config_path.read_text(encoding="utf-8")
    assert "id: hospital" in text
    assert "kind: healthcare" in text
    assert "network_index" not in text
    assert "hospital-dmz" in text
    assert "hospital-web" in text


def test_init_creates_empty_org_with_flag(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    use_case = InitUseCase(FileSystemGateway(tmp_path))
    result = use_case.execute(tmp_path, "hospital", "healthcare", empty=True)
    assert result.ok
    text = result.config_path.read_text(encoding="utf-8")
    assert "networks: []" in text
    assert "services: []" in text
    assert "links: []" in text


def test_init_fails_without_organizations(tmp_path: Path) -> None:
    use_case = InitUseCase(FileSystemGateway(tmp_path))
    result = use_case.execute(tmp_path, "x", "government", False)
    assert not result.ok
    assert "missing directory" in result.error


def test_init_fails_when_org_exists(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "x").mkdir()
    use_case = InitUseCase(FileSystemGateway(tmp_path))
    result = use_case.execute(tmp_path, "x", "government", False)
    assert not result.ok
    assert "already exists" in result.error
