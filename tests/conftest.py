"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from cybercity_data import CityNetwork
from cybercity_data.loader import load_network

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def tiny_path() -> Path:
    return FIXTURES / "tiny"


@pytest.fixture
def broken_path() -> Path:
    return FIXTURES / "broken"


@pytest.fixture
def tiny_network(tiny_path: Path) -> CityNetwork:
    network, _ = load_network(tiny_path)
    return network
