"""Controller layer: CLI commands and entry point."""

from .app import app
from .commands import register_commands
from .handlers import build, check, init  # noqa: F401

register_commands(app)

__all__ = ["app"]
