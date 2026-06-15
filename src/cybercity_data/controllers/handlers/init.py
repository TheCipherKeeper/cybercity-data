"""Init command handler."""

from pathlib import Path
from typing import Annotated

import typer

from ...services import InitService
from ..commands import cli_command
from ..dependencies import resolve
from ..responses import CliResponse, InitResponse


@cli_command(name="init")
def init_cmd(
    org_id: Annotated[str, typer.Argument(help="Organization kebab-case id.")],
    kind: Annotated[
        str,
        typer.Option("--kind", help="Organization kind (e.g. healthcare, finance)."),
    ],
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            help="Repository root containing organizations/ (default: .).",
        ),
    ] = Path("."),
    empty: Annotated[
        bool,
        typer.Option("--empty", help="Create a minimal config with empty lists."),
    ] = False,
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit a single JSON object to stdout."),
    ] = False,
) -> CliResponse:
    """Scaffold a new organization under organizations/<id>/."""
    result = resolve(InitService, path).run(path, org_id=org_id, kind=kind, empty=empty)
    return InitResponse.from_init_result(result, path=path)
