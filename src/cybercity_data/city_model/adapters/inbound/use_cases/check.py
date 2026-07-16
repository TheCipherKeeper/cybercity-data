"""Check use case: thin wrapper around the shared validation step.

The actual load / allocate / check logic lives in ``ValidateCityStep`` so that
other use cases (e.g. ``BuildUseCase``) can reuse it without importing this
use case directly.
"""

from pathlib import Path

from ..dto import CheckResult
from .validate_step import ValidateCityStep


class CheckUseCase:
    """Load the per-org layout, allocate addresses, and run cross-field rules."""

    def __init__(self, validate_step: ValidateCityStep) -> None:
        self._validate = validate_step

    def execute(self, path: Path, strict: bool, seed: int | None = None) -> CheckResult:
        """Run the validation pipeline and return a structured result."""
        return self._validate.execute(path, strict=strict, seed=seed)
