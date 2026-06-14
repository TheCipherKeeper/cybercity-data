"""cybercity-data — canonical declarative city model.

Public surface: pydantic models, loader, checker, and builder.
"""

from .build import Builder, build_artifacts
from .check import Issue, NetworkChecker, Report, check
from .loader import NetworkLoader, load_network
from .models import (
    SCHEMA_VERSION,
    AuthMethod,
    CityNetwork,
    DataClassification,
    DecoyBlock,
    DecoyFingerprint,
    DecoyKind,
    Exposure,
    Link,
    LinkEncryption,
    LinkKind,
    Network,
    NetworkKind,
    Organization,
    OrgKind,
    Regulation,
    Segment,
    Service,
    Software,
    SvcKind,
    ThirdParty,
    WeaknessKind,
)

__version__ = "0.4.0"

__all__ = [
    # Models
    "AuthMethod",
    "CityNetwork",
    "DataClassification",
    "DecoyBlock",
    "DecoyFingerprint",
    "DecoyKind",
    "Exposure",
    "Link",
    "LinkEncryption",
    "LinkKind",
    "Network",
    "NetworkKind",
    "OrgKind",
    "Organization",
    "Regulation",
    "SCHEMA_VERSION",
    "Segment",
    "Service",
    "Software",
    "SvcKind",
    "ThirdParty",
    "WeaknessKind",
    # Pipeline
    "Issue",
    "Report",
    "NetworkChecker",
    "check",
    "NetworkLoader",
    "load_network",
    "Builder",
    "build_artifacts",
    "__version__",
]
