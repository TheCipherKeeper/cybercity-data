"""Check command handler."""

from pathlib import Path
from typing import Annotated

import typer

from ...services import CheckService
from ..commands import cli_command
from ..dependencies import resolve
from ..responses import CheckResponse, CliResponse


@cli_command(name="check")
def check_cmd(
    path: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=False, dir_okay=True, readable=True),
    ] = Path("."),
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit a single JSON object to stdout."),
    ] = False,
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Treat warnings as errors (useful near v1.0)."),
    ] = False,
    seed: Annotated[
        int | None,
        typer.Option("--seed", help="Optional allocation seed for reproducibility."),
    ] = None,
) -> CliResponse:
    """Validate the per-org layout under PATH."""
    result = resolve(CheckService, path).run(path, strict=strict, seed=seed)
    return CheckResponse.from_check_result(result)
