"""CLI command registration and wrapping.

This module is the infrastructure glue that lets handlers stay as plain
functions returning response schemas.  ``@cli_command(name)`` registers a
Typer command, wraps it in exception handling, renders the response, and exits
with the correct code.
"""

import functools
import importlib
import inspect
import pkgutil
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer

from ..services import ApplicationError
from .responses import CliResponse, ErrorResponse, present


def cli_command[F: Callable[..., Any]](name: str) -> Callable[[F], F]:
    """Mark a function as a CLI command named ``name``.

    The decorated function should accept Typer parameters and return a
    ``CliResponse``.  Actual Typer registration happens later via
    ``register_commands()``.
    """

    def decorator(fn: F) -> F:
        fn._cli_command_name = name  # type: ignore[attr-defined]
        return fn

    return decorator


def _extract_context(bound: inspect.BoundArguments) -> tuple[Path, bool]:
    """Pull the CLI context values used by the wrapper from bound arguments."""
    path = bound.arguments.get("path", Path("."))
    json_out = bound.arguments.get("json_out", False)
    return path, json_out


def _wrap_command(fn: Callable[..., CliResponse]) -> Callable[..., None]:
    """Return a Typer-compatible callable for ``fn``.

    Handles exceptions, renders the response, and exits with the right code.
    This is the CLI equivalent of a FastAPI route + exception handler + response
    rendering pipeline.
    """
    sig = inspect.signature(fn)

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        path, json_out = _extract_context(bound)

        try:
            response = fn(*args, **kwargs)
        except typer.Exit:
            raise
        except ApplicationError as exc:
            response = ErrorResponse(path=path, ok=False, exit_code=1, error=exc.message)
        except Exception:
            response = ErrorResponse(
                path=path, ok=False, exit_code=1, error=traceback.format_exc()
            )

        present(response, json_out)
        raise typer.Exit(code=response.exit_code)

    return wrapper


def register_commands(
    app: typer.Typer,
    package: str = "cybercity_data.controllers.handlers",
) -> None:
    """Import all handler modules and register functions marked by ``@cli_command``.

    Modules are imported for their side effects; any top-level function with the
    ``_cli_command_name`` attribute is registered on ``app``.
    """
    pkg = __import__(package, fromlist=["__path__"])
    for _, module_name, _ in pkgutil.iter_modules(pkg.__path__, prefix=f"{package}."):
        module = importlib.import_module(module_name)
        for name in dir(module):
            obj = getattr(module, name)
            if callable(obj) and hasattr(obj, "_cli_command_name"):
                app.command(name=obj._cli_command_name)(_wrap_command(obj))
