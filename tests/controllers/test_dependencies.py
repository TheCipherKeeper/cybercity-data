"""Проверки явного реестра фабрик CLI-сервисов."""

from pathlib import Path

import pytest

from cybercity_data.city_model.adapters.inbound.controllers import dependencies
from cybercity_data.city_model.adapters.inbound.services import CheckService


def test_registered_factory_is_used(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    expected = object()
    original = dependencies._FACTORIES[CheckService]
    monkeypatch.setitem(dependencies._FACTORIES, CheckService, original)

    dependencies.register_factory(CheckService, lambda _path: expected)  # type: ignore[arg-type]

    assert dependencies.resolve(CheckService, tmp_path) is expected


def test_unknown_service_type_is_rejected(tmp_path: Path) -> None:
    class UnknownService:
        pass

    with pytest.raises(KeyError, match="no factory registered for UnknownService"):
        dependencies.resolve(UnknownService, tmp_path)  # type: ignore[type-var]
