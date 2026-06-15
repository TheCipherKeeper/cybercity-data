"""cybercity-data — canonical declarative city model.

Public surface: pydantic models, loader, checker, allocator, and renderer.
"""

from .__version__ import __version__
from .data.loader import NetworkLoader, ServiceAssets, load_network
from .data.renderer import ArtifactRenderer as Builder
from .data.renderer import build_artifacts
from .domain.allocator import Allocation, AllocationError, Allocator
from .domain.checker import Issue, NetworkChecker, Report, check
from .domain.models import (
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

__all__ = [
    # Version
    "__version__",
    # Allocation
    "Allocation",
    "AllocationError",
    "Allocator",
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
    # Validation
    "Issue",
    "Report",
    "NetworkChecker",
    "check",
    # Loading / IO
    "NetworkLoader",
    "ServiceAssets",
    "load_network",
    # Rendering
    "Builder",
    "build_artifacts",
]
