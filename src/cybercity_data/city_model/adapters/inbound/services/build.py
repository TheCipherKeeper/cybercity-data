"""Build service: facade for validate-render-write pipeline.

The service wires the rendering and IO adapters required by the build use case
and exposes a single ``run()`` entry point.  Internally it is split into named
pipeline steps (``_validate``, ``_render``, ``_write``) so that each step can
be exercised independently in tests.
"""

from pathlib import Path

from ..data.filesystem import FileSystemGateway
from ..data.git import GitChangesGateway
from ..data.loader import NetworkLoader, ServiceAssets
from ..data.renderer import ArtifactRenderer
from ..data.zip import EngineZipWriter
from ..domain.allocator import Allocation
from ..domain.models import CityNetwork
from ..dto import BuildResult, CheckResult
from ..use_cases.validate_step import ValidateCityStep
from .exceptions import ApplicationError


class BuildService:
    """Facade for the build pipeline.

    Hides all rendering and IO adapters from the controller.
    """

    def __init__(
        self,
        validate_step: ValidateCityStep,
        renderer: ArtifactRenderer,
        writer: FileSystemGateway,
        zip_writer: EngineZipWriter,
    ) -> None:
        self._validate_step = validate_step
        self._renderer = renderer
        self._writer = writer
        self._zip = zip_writer

    def run(
        self,
        path: Path,
        out: Path,
        strict: bool,
        clean: bool,
        seed: int | None = None,
    ) -> BuildResult:
        """Validate, render and write artifacts under ``path/out``."""
        try:
            check_result = self._validate(path, strict=strict, seed=seed)
            if not check_result.ok:
                return self._skip(check_result)

            artifacts = self._render(
                check_result.network,
                check_result.allocation,
                check_result.service_assets,
            )
            return self._write(
                path=path,
                out=out,
                artifacts=artifacts,
                check_result=check_result,
                clean=clean,
            )
        except ApplicationError:
            raise
        except Exception as exc:
            raise ApplicationError(str(exc)) from exc

    def _validate(self, path: Path, strict: bool, seed: int | None) -> CheckResult:
        """Run the validation pipeline and return its result."""
        return self._validate_step.execute(path, strict=strict, seed=seed)

    def _render(
        self,
        network: CityNetwork,
        allocation: Allocation,
        service_assets: list[ServiceAssets],
    ) -> dict[str, str]:
        """Generate artifact content strings from a validated city model."""
        return self._renderer.render(
            network,
            allocation=allocation,
            service_assets=service_assets,
        )

    def _write(
        self,
        path: Path,
        out: Path,
        artifacts: dict[str, str],
        check_result: CheckResult,
        clean: bool,
    ) -> BuildResult:
        """Persist rendered artifacts and bundle the engine runtime package."""
        target = (path / out).resolve()
        if clean:
            self._writer.clean_directory(target)

        rendered = self._writer.write_artifacts(target, artifacts)
        zip_path = self._zip.bundle(
            target, artifacts, check_result.network, check_result.service_assets
        )
        rendered.append(zip_path)

        return BuildResult(ok=True, check=check_result, rendered=rendered)

    def _skip(self, check_result: CheckResult) -> BuildResult:
        """Return a build result explaining why rendering was skipped."""
        reason = f"build skipped: {len(check_result.errors)} validation error(s)"
        if check_result.strict and check_result.warnings:
            reason += f" and {len(check_result.warnings)} warning(s) (strict mode)"
        return BuildResult(ok=False, check=check_result, skipped_reason=reason)


def create_build_service(path: Path) -> BuildService:
    """Wire the loader, renderer, writer and zip bundler for ``build``."""
    loader = NetworkLoader(path)
    return BuildService(
        validate_step=ValidateCityStep(loader),
        renderer=ArtifactRenderer(git=GitChangesGateway(path)),
        writer=FileSystemGateway(path),
        zip_writer=EngineZipWriter(),
    )
