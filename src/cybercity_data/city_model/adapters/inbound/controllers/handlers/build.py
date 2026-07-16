"""Build command handler."""

from pathlib import Path
from typing import Annotated

import typer

from ...services import BuildService
from ..commands import cli_command
from ..dependencies import resolve
from ..responses import BuildResponse, CliResponse


@cli_command(name="build")
def build_cmd(
    path: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=False, dir_okay=True, readable=True),
    ] = Path("."),
    out: Annotated[
        Path,
        typer.Option("--out", help="Output directory for artifacts (default: build/)."),
    ] = Path("build"),
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit a single JSON object to stdout."),
    ] = False,
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Treat warnings as errors (useful near v1.0)."),
    ] = False,
    clean: Annotated[
        bool,
        typer.Option("--clean", help="Remove existing output directory before build."),
    ] = False,
    seed: Annotated[
        int | None,
        typer.Option("--seed", help="Optional allocation seed for reproducibility."),
    ] = None,
) -> CliResponse:
    """Validate and build artifacts under <PATH>/<out>/ (default: build/)."""
    result = resolve(BuildService, path).run(path, out=out, strict=strict, clean=clean, seed=seed)
    return BuildResponse.from_build_result(result)
