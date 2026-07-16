"""Shared validation step used by multiple use cases.

This is a reusable pipeline step, not a top-level use case by itself.  It loads
the per-org layout, allocates concrete IP addresses, and runs cross-field
rules.  Both ``CheckUseCase`` and ``BuildUseCase`` compose it.
"""

from pathlib import Path

from ..data.loader import NetworkLoader
from ..domain.allocator import Allocator
from ..domain.checker import NetworkChecker
from ..dto import CheckResult, Counts


class ValidateCityStep:
    """Load the per-org layout, allocate addresses, and run cross-field rules."""

    def __init__(self, loader: NetworkLoader) -> None:
        self._loader = loader

    def execute(self, path: Path, strict: bool, seed: int | None = None) -> CheckResult:
        """Run the validation pipeline and return a structured result."""
        network = self._loader.load()
        loader_issues = list(self._loader.issues)

        allocator = Allocator(network, seed=seed)
        allocation = allocator.allocate()

        report = NetworkChecker(allocation=allocation).check(network)
        all_issues = [*loader_issues, *report.issues]
        errors = [i for i in all_issues if i.level == "error"]
        warnings = [i for i in all_issues if i.level == "warning"]
        ok = not errors and (not strict or not warnings)

        counts = Counts(
            organizations=len(network.organizations),
            networks=sum(len(o.networks) for o in network.organizations),
            services=len(network.services),
            links=len(network.links),
        )

        return CheckResult(
            path=path,
            ok=ok,
            strict=strict,
            network=network,
            allocation=allocation,
            errors=errors,
            warnings=warnings,
            counts=counts,
            seed=allocator.seed,
            service_assets=list(self._loader.service_assets),
        )
