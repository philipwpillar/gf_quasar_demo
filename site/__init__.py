"""Robot composition and site-gate admission.  [Tier 2 + Tier 3]

Tier 2 composes attested module refs into a vendor-signed robot identity
(``robot_composed``). Tier 3 records a signed site-gate admission verdict
(``site_admission``). Vendor signatures are REAL Ed25519; demo custody is
server-side software signers — production custody is vendor-side.

Site policy breadth reuses the curated single-task stub from ``policy``.
"""

from .site_admission import admit, verify_site_verdict
from .site_composition import (
    compose_robot,
    composition_from_ledger_entry,
    composition_hashable_view,
    verify_composition,
)
from .site_errors import (
    DuplicateVendorError,
    RobotCompositionNotFoundError,
    RobotIdMismatchError,
    SiteError,
    UnknownVendorError,
)
from .site_models import (
    ComposeRobotRequest,
    RobotComposition,
    SiteAdmissionRequest,
    SiteAdmissionVerdict,
    VendorIdentity,
)
from .site_service import SiteService

__all__ = [
    "ComposeRobotRequest",
    "DuplicateVendorError",
    "RobotComposition",
    "RobotCompositionNotFoundError",
    "RobotIdMismatchError",
    "SiteAdmissionRequest",
    "SiteAdmissionVerdict",
    "SiteError",
    "SiteService",
    "UnknownVendorError",
    "VendorIdentity",
    "composition_hashable_view",
    "verify_composition",
    "verify_site_verdict",
]
