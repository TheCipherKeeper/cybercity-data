"""Check service: facade for the validation pipeline.

The service wires the loader and the shared validation step used by the
``CheckUseCase``.  It exposes a single ``run()`` entry point and delegates the
actual work to named pipeline steps so that each step can be exercised in
isolation in tests.
"""

from pathlib import Path

import yaml
from pydantic import ValidationError

from ..data.loader import NetworkLoader
from ..domain.allocator import AllocationError
from ..dto import CheckResult
from ..use_cases.check import CheckUseCase
from ..use_cases.validate_step import ValidateCityStep
from .exceptions import ApplicationError


def _format_validation_error(exc: ValidationError) -> str:
    bits = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err["loc"]) or "<root>"
        bits.append(f"{loc}: {err['msg']}")
    return "schema errors: " + "; ".join(bits)


class CheckService:
    """Facade for the validation pipeline.

    Hides ``NetworkLoader`` and ``ValidateCityStep`` wiring from the controller.
    The work is split into named steps that can be tested independently.
    """

    def __init__(self, use_case: CheckUseCase) -> None:
        self._use_case = use_case

    def run(self, path: Path, strict: bool, seed: int | None = None) -> CheckResult:
        """Validate the per-org layout under ``path``."""
        try:
            return self._validate(path, strict=strict, seed=seed)
        except FileNotFoundError as exc:
            raise ApplicationError(str(exc)) from exc
        except yaml.YAMLError as exc:
            raise ApplicationError(f"YAML error: {exc}") from exc
        except ValidationError as exc:
            raise ApplicationError(_format_validation_error(exc)) from exc
        except AllocationError as exc:
            raise ApplicationError(f"allocation error: {exc}") from exc

    def _validate(self, path: Path, strict: bool, seed: int | None) -> CheckResult:
        """Run the validation use case and return a structured result."""
        return self._use_case.execute(path, strict=strict, seed=seed)


def create_check_service(path: Path) -> CheckService:
    """Wire the loader and validation step for the CLI."""
    loader = NetworkLoader(path)
    return CheckService(use_case=CheckUseCase(ValidateCityStep(loader)))
