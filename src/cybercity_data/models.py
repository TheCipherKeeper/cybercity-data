"""Pydantic models for the cybercity network model.

Schema goals for v2.0 (explicit-only):
  * Everything is declared: networks, IP addresses, and service placement.
  * org_id is still injected by the loader to avoid repeating it in every service.
  * Decoys are services with a `decoy` block; their honeypot role is separate from service kind.
  * `extra="forbid"` keeps typos loud.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "OrgKind",
    "Segment",
    "SvcKind",
    "Exposure",
    "NetworkKind",
    "AuthMethod",
    "DataClassification",
    "Software",
    "LinkKind",
    "LinkEncryption",
    "DecoyKind",
    "DecoyFingerprint",
    "WeaknessKind",
    "Regulation",
    "Network",
    "ThirdParty",
    "Organization",
    "Service",
    "Link",
    "CityNetwork",
    "SCHEMA_VERSION",
]

# ─────────────────────────────────────────────────────────────────────
# Schema version
# ─────────────────────────────────────────────────────────────────────
SCHEMA_VERSION = "2.0.0"

# ─────────────────────────────────────────────────────────────────────
# Enums (Literal — pydantic emits a clear error on a bad value)
# ─────────────────────────────────────────────────────────────────────
OrgKind = Literal[
    "government",
    "healthcare",
    "infra-utilities",
    "finance",
    "retail",
    "media-telecom",
    "education",
    "msp",
]

Segment = Literal["corp", "ot", "mgmt", "public"]

SvcKind = Literal[
    "web",
    "api",
    "pos",
    "identity",
    "db",
    "file-share",
    "rmm",
    "vpn",
    "ot",
    "cctv",
    "mail",
    "dns",
    "ntp",
    "backup",
    "log",
    "erp",
    "hrms",
    "billing",
    "tickets",
    "wiki",
    "crm",
    "pharmacy-front",
    "iot",
]

Exposure = Literal["public", "intranet", "ot", "mgmt"]

NetworkKind = Literal["dmz", "lan", "ot", "mgmt", "internet"]

AuthMethod = Literal["none", "local", "sso", "mfa", "certificate"]

DataClassification = Literal[
    "public",
    "internal",
    "confidential",
    "restricted",
    "pii",
    "phi",
    "pci",
]

LinkKind = Literal[
    "api-call",
    "auth",
    "db-read",
    "db-write",
    "log-sink",
    "backup-of",
    "trusts",
    "lateral",
    "m2m",
    "vendor-vpn",
    "phishing-source",
    "watering-hole",
]

LinkEncryption = Literal["none", "tls", "mtls", "ipsec", "sso-trust"]

DecoyKind = Literal[
    "http",
    "ssh",
    "rdp",
    "printer",
    "iot",
    "nas",
    "camera",
    "random",
]

DecoyFingerprint = Literal[
    "realistic",
    "default-creds",
    "known-cve",
    "decoy-banner",
]

WeaknessKind = Literal[
    "default-creds",
    "unpatched",
    "exposed-internet",
    "missing-mfa",
    "ot-flat-network",
    "supply-chain",
    "stale-account",
    "open-share",
]

Regulation = Literal["hipaa", "pci-dss", "gdpr", "nerc-cip", "sox", "ferpa"]

# ─────────────────────────────────────────────────────────────────────
# Patterns
# ─────────────────────────────────────────────────────────────────────
_KEBAB = r"^[a-z][a-z0-9-]*$"
_SEMVER = r"^\d+\.\d+\.\d+$"
_PORT = r"^(tcp|udp)/(6553[0-5]|655[0-2]\d|65[0-4]\d\d|6[0-4]\d{3}|[1-5]\d{4}|[1-9]\d{0,3})$"
_FQDN = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$"
_CIDR = r"^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$"
_IPV4 = r"^\d{1,3}(\.\d{1,3}){3}$"
_SOFTWARE_VERSION = r"^(\d+(\.\d+){0,3}(-[\w.]+)?|unknown|any)$"
_CVE = r"^CVE-\d{4}-\d{4,}$"

# ─────────────────────────────────────────────────────────────────────
# Base model
# ─────────────────────────────────────────────────────────────────────
class _StrictModel(BaseModel):
    """Common config: forbid unknown fields, validate on assignment."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


# ─────────────────────────────────────────────────────────────────────
# Network (first-class in v2.0)
# ─────────────────────────────────────────────────────────────────────
class Network(_StrictModel):
    """A layer-3 network that belongs to exactly one organization."""

    id: str = Field(pattern=_KEBAB)
    org_id: str = Field(pattern=_KEBAB)
    name: str | None = None
    kind: NetworkKind
    cidr: str = Field(pattern=_CIDR)
    description: str | None = None


# ─────────────────────────────────────────────────────────────────────
# Supporting models
# ─────────────────────────────────────────────────────────────────────
class Software(_StrictModel):
    """Product fingerprint for a service."""

    vendor: str
    product: str
    version: str | None = Field(default=None, pattern=_SOFTWARE_VERSION)
    cve_id: str | None = Field(default=None, pattern=_CVE)


class ThirdParty(_StrictModel):
    """Vendor / MSP / 3rd-party tied to one organization."""

    name: str
    role: str
    note: str | None = None


class DecoyBlock(_StrictModel):
    """Turns an ordinary Service into a decoy / honeypot."""

    kind: DecoyKind = "http"
    fingerprint: DecoyFingerprint = "realistic"
    os_hint: str | None = None
    note: str | None = None


# ─────────────────────────────────────────────────────────────────────
# Organization
# ─────────────────────────────────────────────────────────────────────
class Organization(_StrictModel):
    id: str = Field(pattern=_KEBAB)
    name: str
    kind: OrgKind
    segment: Segment

    description: str | None = None
    third_party: list[ThirdParty] = []
    notes: list[str] = []
    tags: list[str] = []
    regulated: list[Regulation] = []
    headcount_estimate: int | None = Field(default=None, ge=0)

    # Networks must be declared explicitly in v2.0.
    networks: list[Network] = []


# ─────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────
class Service(_StrictModel):
    id: str = Field(pattern=_KEBAB)
    org_id: str = Field(pattern=_KEBAB)
    name: str
    kind: SvcKind
    exposure: Exposure
    host: str = Field(pattern=_FQDN)

    # Concrete network placement must be declared explicitly in v2.0.
    network_id: str | None = Field(default=None, pattern=_KEBAB)
    bind_ip: str | None = Field(default=None, pattern=_IPV4)

    software: Software | None = None
    auth: AuthMethod = "local"
    data_classification: DataClassification = "internal"
    ports: list[Annotated[str, Field(pattern=_PORT)]] = Field(default_factory=list)
    owner_team: str | None = None
    known_weakness: WeaknessKind | None = None
    decoy: DecoyBlock | None = None


# ─────────────────────────────────────────────────────────────────────
# Link
# ─────────────────────────────────────────────────────────────────────
class Link(_StrictModel):
    from_service: str = Field(pattern=_KEBAB)
    to_service: str = Field(pattern=_KEBAB)
    kind: LinkKind
    protocol: str | None = Field(default=None, pattern=_PORT)

    encryption: LinkEncryption = "tls"
    bidirectional: bool = False
    label: str | None = None
    attack_chain: list[str] = []


# ─────────────────────────────────────────────────────────────────────
# Root model
# ─────────────────────────────────────────────────────────────────────
class CityNetwork(_StrictModel):
    """Assembled city: organizations, services, links."""

    version: str = Field(default=SCHEMA_VERSION, pattern=_SEMVER)
    organizations: list[Organization] = []
    services: list[Service] = []
    links: list[Link] = []
