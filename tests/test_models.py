"""Pydantic model-level tests: parsing, enums, patterns."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cybercity_data import CityNetwork


def _meta():
    return {"city": "x", "allocation": _allocation()}


def _allocation():
    return {
        "corp": "10.10.0.0/16",
        "ot": "10.20.0.0/16",
        "mgmt": "10.30.0.0/16",
        "internet": "203.0.113.0/24",
    }


def test_tiny_fixture_parses(tiny_network: CityNetwork) -> None:
    assert len(tiny_network.organizations) == 3
    assert sum(len(o.networks) for o in tiny_network.organizations) == 8
    assert len(tiny_network.services) == 4
    assert len(tiny_network.links) == 1


def test_bad_org_kind_rejected() -> None:
    raw = {
        "version": "1.0.0",
        "meta": _meta(),
        "organizations": [
            {
                "id": "bad",
                "name": "Bad",
                "kind": "non-existent",
                "segment": "corp",
            }
        ],
    }
    with pytest.raises(ValidationError):
        CityNetwork.model_validate(raw)


def test_id_pattern_kebab_case() -> None:
    raw = {
        "version": "1.0.0",
        "meta": _meta(),
        "organizations": [
            {"id": "Has_Caps", "name": "x", "kind": "government", "segment": "corp"}
        ],
    }
    with pytest.raises(ValidationError):
        CityNetwork.model_validate(raw)


def test_extra_field_rejected() -> None:
    raw = {
        "version": "1.0.0",
        "meta": _meta(),
        "organizations": [
            {
                "id": "city-x",
                "name": "X",
                "kind": "government",
                "segment": "corp",
                "smuggled": True,
            }
        ],
    }
    with pytest.raises(ValidationError):
        CityNetwork.model_validate(raw)


def test_version_pattern() -> None:
    bad = {
        "version": "v1",
        "meta": _meta(),
    }
    with pytest.raises(ValidationError):
        CityNetwork.model_validate(bad)


def test_service_requires_host_fqdn() -> None:
    raw = {
        "version": "1.0.0",
        "meta": _meta(),
        "organizations": [
            {"id": "city-x", "name": "X", "kind": "government", "segment": "corp"}
        ],
        "services": [
            {
                "id": "svc",
                "org_id": "city-x",
                "name": "S",
                "kind": "web",
                "exposure": "public",
                "host": "not_valid_host",
            }
        ],
    }
    with pytest.raises(ValidationError):
        CityNetwork.model_validate(raw)


def test_allocation_required() -> None:
    raw = {
        "version": "1.0.0",
        "meta": {"city": "x"},
    }
    with pytest.raises(ValidationError):
        CityNetwork.model_validate(raw)


def test_cve_id_pattern() -> None:
    raw = {
        "version": "1.0.0",
        "meta": _meta(),
        "organizations": [
            {"id": "city-x", "name": "X", "kind": "government", "segment": "corp"}
        ],
        "services": [
            {
                "id": "svc",
                "org_id": "city-x",
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
