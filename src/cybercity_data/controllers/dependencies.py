"""Service factories for the CLI controller layer.

Think of this as a tiny dependency-injection container: handlers ask for a
service by type, and this module resolves it through a configurable factory.
Tests or plugins can override factories via ``register_factory`` without
touching handler code.
"""

from collections.abc import Callable
from pathlib import Path
from typing import cast

from ..services import BuildService, CheckService, InitService
from ..services.build import create_build_service
from ..services.check import create_check_service
from ..services.init import create_init_service

type _Service = CheckService | BuildService | InitService

_FACTORIES: dict[type[_Service], Callable[[Path], _Service]] = {
    CheckService: create_check_service,
    BuildService: create_build_service,
    InitService: create_init_service,
}


def resolve[S: _Service](service_type: type[S], path: Path) -> S:
    """Return a service instance of ``service_type`` wired for ``path``."""
    factory = _FACTORIES.get(service_type)  # type: ignore[arg-type]
    if factory is None:
        raise KeyError(f"no factory registered for {service_type.__name__}")
    return cast(S, factory(path))


def register_factory[S: _Service](
    service_type: type[S],
    factory: Callable[[Path], S],
) -> None:
    """Override the factory used to build ``service_type``.

    Useful for tests that want to inject a fake service without monkeypatching.
    """
    _FACTORIES[service_type] = factory  # type: ignore[index]
