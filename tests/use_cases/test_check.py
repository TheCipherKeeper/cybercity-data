"""Check use case tests."""

from pathlib import Path

import pytest

from cybercity_data.city_model.adapters.inbound.data.loader import NetworkLoader
from cybercity_data.city_model.adapters.inbound.use_cases.check import CheckUseCase
from cybercity_data.city_model.adapters.inbound.use_cases.validate_step import ValidateCityStep


def _check_use_case(path: Path) -> CheckUseCase:
    return CheckUseCase(ValidateCityStep(NetworkLoader(path)))


@pytest.fixture
def warning_path(tiny_path: Path, tmp_path: Path) -> Path:
    """Copy of `tiny` with an orphan service asset directory (produces a warning)."""
    import shutil

    target = tmp_path / "warning"
    shutil.copytree(tiny_path, target)
    orphan = target / "organizations" / "hospital" / "services" / "orphan-asset"
    orphan.mkdir(parents=True)
    (orphan / "file.txt").write_text("orphan", encoding="utf-8")
    return target


def test_check_ok_on_tiny(tiny_path: Path) -> None:
    use_case = _check_use_case(tiny_path)
    result = use_case.execute(tiny_path, strict=False)
    assert result.ok
    assert not result.errors
    assert not result.warnings
    assert result.counts.organizations == 3
    assert result.seed is not None


def test_check_fails_on_broken(broken_path: Path) -> None:
    use_case = _check_use_case(broken_path)
    result = use_case.execute(broken_path, strict=False)
    assert not result.ok
    assert any(i.code == "ids" for i in result.errors)
    assert any(i.code == "refs" for i in result.errors)


def test_check_warning_does_not_fail_without_strict(warning_path: Path) -> None:
    use_case = _check_use_case(warning_path)
    result = use_case.execute(warning_path, strict=False)
    assert result.ok
    assert not result.errors
    assert any(i.code == "assets" for i in result.warnings)


def test_check_strict_rejects_warnings(warning_path: Path) -> None:
    use_case = _check_use_case(warning_path)
    result = use_case.execute(warning_path, strict=True)
    assert not result.ok
    assert any(i.code == "assets" for i in result.warnings)
    assert not result.errors


def test_check_includes_loader_issues(tmp_path: Path) -> None:
    (tmp_path / "organizations").mkdir()
    (tmp_path / "organizations" / "x").mkdir()
    (tmp_path / "organizations" / "x" / "config.yml").write_text(
        "id: y\nname: X\nkind: government\nnetworks: []\nservices: []\n",
        encoding="utf-8",
    )
    use_case = _check_use_case(tmp_path)
    result = use_case.execute(tmp_path, strict=False)
    assert not result.ok
    assert any(i.code == "L003" for i in result.errors)


def test_check_seeded_is_deterministic(tiny_path: Path) -> None:
    use_case = _check_use_case(tiny_path)
    a = use_case.execute(tiny_path, strict=False, seed=42)
    b = use_case.execute(tiny_path, strict=False, seed=42)
    assert a.allocation == b.allocation
    assert a.seed == b.seed == 42
