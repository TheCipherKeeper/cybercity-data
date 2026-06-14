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
    Criticality,
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
    Service,
    Software,
    SvcKind,
)

__version__ = "0.4.0"

__all__ = [
    # Models
    "AuthMethod",
    "CityNetwork",
    "Criticality",
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
    "SCHEMA_VERSION",
    "Service",
    "Software",
    "SvcKind",
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
