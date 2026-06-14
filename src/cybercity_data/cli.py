"""CLI entry point.

Commands:
    cybercity-data check [PATH] [--json] [--strict]
    cybercity-data build [PATH] [--out DIR] [--json] [--strict]
    cybercity-data init ID --kind KIND --segment SEGMENT [--path PATH]

Exit codes:
    0 — OK
    1 — any problem (data issue, validation error, or internal bug)
"""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, NamedTuple

import typer
import yaml
from pydantic import ValidationError

from . import __version__
from .build import Builder
from .check import Issue, NetworkChecker
from .loader import NetworkLoader
from .models import CityNetwork

app = typer.Typer(
    name="cybercity-data",
    help="Build and validate the cybercity network model.",
    no_args_is_help=True,
    add_completion=False,
)


class Counts(NamedTuple):
    organizations: int
    networks: int
    services: int
    links: int


@dataclass
class Result:
    path: Path
    ok: bool
    strict: bool = False
    counts: Counts | None = None
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    error: str | None = None
    rendered: list[Path] | None = None
    render_skipped: str | None = None

    @property
    def exit_code(self) -> int:
        return 0 if self.ok else 1

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "ok": self.ok,
            "exit_code": self.exit_code,
            "path": str(self.path),
            "strict": self.strict,
        }
        if self.counts is not None:
            out["counts"] = self.counts._asdict()
        if self.error is not None:
            out["error"] = self.error
        out["errors"] = [i.__dict__ for i in self.errors]
        out["warnings"] = [i.__dict__ for i in self.warnings]
        if self.rendered is not None:
            out["rendered"] = [str(p) for p in self.rendered]
        if self.render_skipped is not None:
            out["render_skipped"] = self.render_skipped
        return out

    def print_human(self) -> None:
        for issue in self.errors:
            typer.echo(f"ERROR [{issue.code}] {issue.path}: {issue.message}", err=True)
        for issue in self.warnings:
            typer.echo(f"WARN  [{issue.code}] {issue.path}: {issue.message}")

        if self.error is not None:
            typer.echo(self.error, err=True)
            return

        if self.counts is not None:
            c = self.counts
            typer.echo(
                f"OK: {c.organizations} orgs, {c.networks} networks, "
                f"{c.services} services, {c.links} links; "
                f"{len(self.errors)} errors, {len(self.warnings)} warnings."
            )
        if self.rendered is not None:
            for p in self.rendered:
                typer.echo(f"Wrote {p}")
        if self.render_skipped is not None:
            typer.echo(self.render_skipped)


# ─────────────────────────────────────────────────────────────────────
# Core pipeline
# ─────────────────────────────────────────────────────────────────────
def _load(path: Path) -> tuple[CityNetwork, list[Issue]]:
    loader = NetworkLoader(path)
    network = loader.load()
    return network, list(loader.issues)


def _run_check(path: Path, strict: bool) -> Result:
    result = Result(path=path, ok=False, strict=strict)
    try:
        network, loader_issues = _load(path)
    except FileNotFoundError as exc:
        result.error = str(exc)
        return result
    except yaml.YAMLError as exc:
        result.error = f"YAML error: {exc}"
        return result
    except ValidationError as exc:
        result.error = _format_validation_error(exc)
        return result
    except Exception:
        result.error = traceback.format_exc()
        return result

    report = NetworkChecker().check(network)
    all_issues = [*loader_issues, *report.issues]
    result.errors = [i for i in all_issues if i.level == "error"]
    result.warnings = [i for i in all_issues if i.level == "warning"]
    result.ok = not result.errors and (not strict or not result.warnings)
    result.counts = Counts(
        organizations=len(network.organizations),
        networks=sum(len(o.networks) for o in network.organizations),
        services=len(network.services),
        links=len(network.links),
    )
    return result


def _run_build(path: Path, out: Path, strict: bool) -> Result:
    result = _run_check(path, strict=strict)
    if not result.ok or result.error is not None:
        if result.error is None:
            result.render_skipped = (
                f"build skipped: {len(result.errors)} validation error(s)"
            )
            if strict and result.warnings:
                result.render_skipped += (
                    f" and {len(result.warnings)} warning(s) (strict mode)"
                )
        return result

    try:
        network, _ = _load(path)
        target = (path / out).resolve()
        rendered = Builder(network).render(target)
        result.rendered = rendered
    except Exception:
        result.ok = False
        result.error = traceback.format_exc()
    return result


def _format_validation_error(exc: ValidationError) -> str:
    bits = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err["loc"]) or "<root>"
        bits.append(f"{loc}: {err['msg']}")
    return "schema errors: " + "; ".join(bits)


# ─────────────────────────────────────────────────────────────────────
# Typer commands
# ─────────────────────────────────────────────────────────────────────
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


@app.command(name="check")
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
        typer.Option(
            "--strict", help="Treat warnings as errors (useful near v1.0)."
        ),
    ] = False,
) -> None:
    """Validate the per-org layout under PATH."""
    result = _run_check(path, strict=strict)
    _emit(result, json_out)
    raise typer.Exit(code=result.exit_code)


@app.command(name="build")
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
        typer.Option(
            "--strict", help="Treat warnings as errors (useful near v1.0)."
        ),
    ] = False,
) -> None:
    """Validate and build artifacts under <PATH>/<out>/ (default: build/)."""
    result = _run_build(path, out, strict=strict)
    _emit(result, json_out)
    raise typer.Exit(code=result.exit_code)


@app.command(name="init")
def init_cmd(
    org_id: Annotated[str, typer.Argument(help="Organization kebab-case id.")],
    kind: Annotated[
        str,
        typer.Option("--kind", help="Organization kind (e.g. healthcare, finance)."),
    ],
    segment: Annotated[
        str,
        typer.Option("--segment", help="Segment: corp | ot | mgmt | public."),
    ],
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            help="Repository root containing organizations/ (default: .).",
        ),
    ] = Path("."),
) -> None:
    """Scaffold a new organization under organizations/<org_id>/."""
    orgs_root = path / "organizations"
    if not orgs_root.is_dir():
        typer.echo(f"ERROR: missing directory: {orgs_root}", err=True)
        raise typer.Exit(code=1)

    target_dir = orgs_root / org_id
    if target_dir.exists():
        typer.echo(f"ERROR: already exists: {target_dir}", err=True)
        raise typer.Exit(code=1)

    target_dir.mkdir()
    config_path = target_dir / "config.yml"
    name = " ".join(part.capitalize() for part in org_id.split("-"))
    content = (
        f"id: {org_id}\n"
        f'name: "{name}"\n'
        f"kind: {kind}\n"
        f"segment: {segment}\n"
        "\n"
        "description: |\n"
        "  Опиши роль организации, типичные сервисы и известные слабости.\n"
        "\n"
        "services: []\n"
        "links: []\n"
    )
    config_path.write_text(content, encoding="utf-8")
    typer.echo(f"Created {config_path}")


def _emit(result: Result, json_out: bool) -> None:
    if json_out:
        typer.echo(json.dumps(result.to_json(), ensure_ascii=False, indent=2))
    else:
        result.print_human()


if __name__ == "__main__":
    app()
