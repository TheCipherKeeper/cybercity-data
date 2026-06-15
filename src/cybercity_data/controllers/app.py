"""Typer application definition and global CLI options."""

from typing import Annotated

import typer

from ..__version__ import __version__

app = typer.Typer(
    name="cybercity-data",
    help="Build and validate the cybercity network model.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"cybercity-data {__version__}")
        raise typer.Exit


@app.callback()
def _root(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Print version and exit.",
        ),
    ] = False,
) -> None:
    pass
