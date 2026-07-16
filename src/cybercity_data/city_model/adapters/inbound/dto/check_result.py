"""DTO returned by the validation pipeline."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from ..data.loader import ServiceAssets
from ..domain.allocator import Allocation
from ..domain.checker import Issue
from ..domain.models import CityNetwork
from .counts import Counts


class CheckResult(BaseModel):
    """Outcome of the validation pipeline."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    path: Path
    ok: bool
    strict: bool
    network: CityNetwork
    allocation: Allocation
    errors: list[Issue]
    warnings: list[Issue]
    counts: Counts
    seed: int | None = None
    service_assets: list[ServiceAssets] = []
