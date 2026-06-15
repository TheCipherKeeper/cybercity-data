"""Pydantic model-level tests: parsing, enums, patterns."""

import pytest
from pydantic import ValidationError

from cybercity_data import CityNetwork


def test_tiny_fixture_parses(tiny_network: CityNetwork) -> None:
    assert len(tiny_network.organizations) == 3
    assert sum(len(o.networks) for o in tiny_network.organizations) == 3
    assert len(tiny_network.services) == 4
    assert len(tiny_network.links) == 1
    assert tiny_network.version == "3.0.0"


def test_bad_org_kind_rejected() -> None:
    raw = {
        "version": "3.0.0",
        "organizations": [
            {
                "id": "bad",
                "name": "Bad",
                "kind": "non-existent",
            }
        ],
    }
    with pytest.raises(ValidationError):
        CityNetwork.model_validate(raw)


def test_id_pattern_kebab_case() -> None:
    raw = {
        "version": "3.0.0",
        "organizations": [{"id": "Has_Caps", "name": "x", "kind": "government"}],
    }
    with pytest.raises(ValidationError):
        CityNetwork.model_validate(raw)


def test_extra_field_rejected() -> None:
    raw = {
        "version": "3.0.0",
        "organizations": [
            {
                "id": "x",
                "name": "X",
                "kind": "government",
                "smuggled": True,
            }
        ],
    }
    with pytest.raises(ValidationError):
        CityNetwork.model_validate(raw)


def test_removed_network_index_rejected() -> None:
    """network_index is no longer part of the declarative model."""
    raw = {
        "version": "3.0.0",
        "organizations": [{"id": "x", "name": "X", "kind": "government", "network_index": 1}],
    }
    with pytest.raises(ValidationError):
        CityNetwork.model_validate(raw)


def test_version_pattern() -> None:
    bad = {
        "version": "v1",
    }
    with pytest.raises(ValidationError):
        CityNetwork.model_validate(bad)


def test_service_requires_host_fqdn() -> None:
    raw = {
        "version": "3.0.0",
        "organizations": [{"id": "x", "name": "X", "kind": "government"}],
        "services": [
            {
                "id": "svc",
                "org_id": "x",
                "name": "S",
                "kind": "web",
                "exposure": "public",
                "host": "not_valid_host",
            }
        ],
    }
    with pytest.raises(ValidationError):
        CityNetwork.model_validate(raw)


def test_cve_id_pattern() -> None:
    raw = {
        "version": "3.0.0",
        "organizations": [{"id": "x", "name": "X", "kind": "government"}],
        "services": [
            {
                "id": "svc",
                "org_id": "x",
                "name": "S",
                "kind": "web",
                "exposure": "public",
                "host": "s.example",
                "software": {
                    "vendor": "x",
                    "product": "y",
                    "cve_id": "not-a-cve",
                },
            }
        ],
    }
    with pytest.raises(ValidationError):
        CityNetwork.model_validate(raw)


def test_service_ports_pattern() -> None:
    raw = {
        "version": "3.0.0",
        "organizations": [{"id": "x", "name": "X", "kind": "government"}],
        "services": [
            {
                "id": "svc",
                "org_id": "x",
                "name": "S",
                "kind": "web",
                "exposure": "public",
                "host": "s.example",
                "ports": ["tcp/70000"],
            }
        ],
    }
    with pytest.raises(ValidationError):
        CityNetwork.model_validate(raw)


def test_service_ports_accepts_valid() -> None:
    raw = {
        "version": "3.0.0",
        "organizations": [{"id": "x", "name": "X", "kind": "government"}],
        "services": [
            {
                "id": "svc",
                "org_id": "x",
                "name": "S",
                "kind": "web",
                "exposure": "public",
                "host": "s.example",
                "ports": ["tcp/443", "udp/53"],
            }
        ],
    }
    network = CityNetwork.model_validate(raw)
    assert network.services[0].ports == ["tcp/443", "udp/53"]


def test_default_version_is_schema_version() -> None:
    network = CityNetwork(organizations=[])
    assert network.version == "3.0.0"


def test_known_weakness_rejected() -> None:
    """known_weakness was removed in the city-simulation refactor."""
    raw = {
        "version": "3.0.0",
        "organizations": [{"id": "x", "name": "X", "kind": "government"}],
        "services": [
            {
                "id": "svc",
                "org_id": "x",
                "name": "S",
                "kind": "web",
                "exposure": "public",
                "host": "s.example",
                "known_weakness": "unpatched",
            }
        ],
    }
    with pytest.raises(ValidationError):
        CityNetwork.model_validate(raw)


def test_attack_chain_rejected() -> None:
    """attack_chain was removed from links."""
    raw = {
        "version": "3.0.0",
        "organizations": [{"id": "x", "name": "X", "kind": "government"}],
        "services": [
            {
                "id": "a",
                "org_id": "x",
                "name": "A",
                "kind": "web",
                "exposure": "public",
                "host": "a.example",
            },
            {
                "id": "b",
                "org_id": "x",
                "name": "B",
                "kind": "web",
                "exposure": "public",
                "host": "b.example",
            },
        ],
        "links": [
            {
                "from_service": "a",
                "to_service": "b",
                "kind": "api-call",
                "attack_chain": ["scn-01"],
            }
        ],
    }
    with pytest.raises(ValidationError):
        CityNetwork.model_validate(raw)
