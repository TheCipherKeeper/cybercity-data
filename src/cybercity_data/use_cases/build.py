"""Build use case: validate, then render and write artifacts."""

from pathlib import Path

from ..data.filesystem import FileSystemGateway
from ..data.renderer import ArtifactRenderer
from ..data.zip import EngineZipWriter
from ..dto import BuildResult, CheckResult
from .validate_step import ValidateCityStep


class BuildUseCase:
    """Run the validation step and, if successful, write build artifacts."""

    def __init__(
        self,
        validate_step: ValidateCityStep,
        renderer: ArtifactRenderer,
        writer: FileSystemGateway,
        zip_writer: EngineZipWriter,
    ) -> None:
        self._validate = validate_step
        self._renderer = renderer
        self._writer = writer
        self._zip = zip_writer

    def execute(
        self,
        path: Path,
        out: Path,
        strict: bool,
        clean: bool,
        seed: int | None = None,
    ) -> BuildResult:
        """Validate and, if successful, render and write artifacts."""
        check_result = self._validate.execute(path, strict=strict, seed=seed)
        if not check_result.ok:
            return self._skip(check_result)

        artifacts = self._renderer.render(
            check_result.network,
            check_result.allocation,
            check_result.service_assets,
        )

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
