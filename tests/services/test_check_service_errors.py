"""Преобразование ожидаемых ошибок сервиса проверки в ошибки приложения."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from cybercity_data.city_model.adapters.inbound.domain.allocator import AllocationError
from cybercity_data.city_model.adapters.inbound.services.check import CheckService
from cybercity_data.city_model.adapters.inbound.services.exceptions import ApplicationError


class FailingUseCase:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def execute(self, *_args, **_kwargs):
        raise self.error


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (FileNotFoundError("missing"), "missing"),
        (yaml.YAMLError("bad yaml"), "YAML error: bad yaml"),
        (ValidationError.from_exception_data("CityNetwork", []), "schema errors:"),
        (AllocationError("no range"), "allocation error: no range"),
    ],
)
def test_expected_errors_are_application_errors(error: Exception, message: str) -> None:
    service = CheckService(FailingUseCase(error))  # type: ignore[arg-type]
    with pytest.raises(ApplicationError, match=message):
        service.run(Path("."), strict=False)
