"""DTO returned by the build pipeline."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .check_result import CheckResult


class BuildResult(BaseModel):
    """Outcome of the build pipeline."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    ok: bool
    check: CheckResult
    rendered: list[Path] | None = None
    skipped_reason: str | None = None
    error: str | None = None
