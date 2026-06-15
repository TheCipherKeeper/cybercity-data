"""CLI response schemas and rendering.

These are the presentation-level DTOs used by the controller layer.  Each
handler maps its service result to a dedicated response schema (similar to a
FastAPI ``response_model``).  ``present()`` renders a schema as JSON or human
text.
"""

import json
from pathlib import Path

import typer
from pydantic import BaseModel, ConfigDict

from ..domain.checker import Issue
from ..dto import BuildResult, CheckResult, Counts, InitResult


class CliResponse(BaseModel):
    """Base response schema shared by all CLI commands."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    exit_code: int
    path: Path


class ErrorResponse(CliResponse):
    """Response schema for application or unexpected errors."""

    error: str


class CheckResponse(CliResponse):
    """Response schema for the ``check`` command."""

    strict: bool
    counts: Counts | None = None
    errors: list[Issue] = []
    warnings: list[Issue] = []
    allocation_seed: int | None = None
    service_assets: int = 0

    @classmethod
    def from_check_result(cls, result: CheckResult) -> "CheckResponse":
        return cls(
            path=result.path,
            ok=result.ok,
            exit_code=0 if result.ok else 1,
            strict=result.strict,
            counts=result.counts,
            errors=result.errors,
            warnings=result.warnings,
            allocation_seed=result.seed,
            service_assets=len(result.service_assets),
        )


class BuildResponse(CheckResponse):
    """Response schema for the ``build`` command."""

    rendered: list[Path] | None = None
    render_skipped: str | None = None

    @classmethod
    def from_build_result(cls, result: BuildResult) -> "BuildResponse":
        check = result.check
        return cls(
            path=check.path,
            ok=result.ok,
            exit_code=0 if result.ok else 1,
            strict=check.strict,
            counts=check.counts,
            errors=check.errors,
            warnings=check.warnings,
            allocation_seed=check.seed,
            service_assets=len(check.service_assets),
            rendered=result.rendered,
            render_skipped=result.skipped_reason,
        )


class InitResponse(CliResponse):
    """Response schema for the ``init`` command."""

    config_path: Path | None = None
    error: str | None = None

    @classmethod
    def from_init_result(cls, result: InitResult, *, path: Path) -> "InitResponse":
        return cls(
            path=path,
            ok=result.ok,
            exit_code=0 if result.ok else 1,
            config_path=result.config_path,
            error=result.error,
        )


def present(response: CliResponse, json_out: bool) -> None:
    """Render ``response`` as JSON or human-readable text."""
    if json_out:
        payload = response.model_dump(mode="json", exclude_none=True)
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    _render_human(response)


def _render_human(response: CliResponse) -> None:
    if isinstance(response, ErrorResponse):
        typer.echo(response.error, err=True)
        return

    if isinstance(response, InitResponse):
        if response.error is not None:
            typer.echo(response.error, err=True)
            return
        if response.config_path is not None:
            typer.echo(f"Wrote {response.config_path}")
        return

    if isinstance(response, CheckResponse):
        for issue in response.errors:
            typer.echo(f"ERROR [{issue.code}] {issue.path}: {issue.message}", err=True)
        for issue in response.warnings:
            typer.echo(f"WARN  [{issue.code}] {issue.path}: {issue.message}")

        if response.counts is not None:
            c = response.counts
            typer.echo(
                f"OK: {c.organizations} orgs, {c.networks} networks, "
                f"{c.services} services, {c.links} links; "
                f"{len(response.errors)} errors, {len(response.warnings)} warnings."
            )
        if response.allocation_seed is not None:
            typer.echo(f"Allocation seed: {response.allocation_seed}")

    if isinstance(response, BuildResponse):
        if response.render_skipped is not None:
            typer.echo(response.render_skipped)
        if response.rendered is not None:
            for p in response.rendered:
                typer.echo(f"Wrote {p}")
