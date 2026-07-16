"""DTO returned by the init pipeline."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class InitResult(BaseModel):
    """Outcome of `cybercity-data init`."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    ok: bool
    config_path: Path | None = None
    error: str | None = None
