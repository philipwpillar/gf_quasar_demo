"""Robot composition and site-gate admission.  [Tier 2 + Tier 3]

Tier 2 composes attested module refs into a robot identity (``robot_composed``).
Tier 3 records a signed site-gate admission verdict (``site_admission``).
Site policy breadth reuses the curated single-task stub from ``policy``.
"""

from .site_admission import admit, verify_site_verdict
from .site_composition import compose_robot, composition_from_ledger_entry
from .site_errors import RobotCompositionNotFoundError, RobotIdMismatchError, SiteError
from .site_models import (
    ComposeRobotRequest,
    RobotComposition,
    SiteAdmissionRequest,
    SiteAdmissionVerdict,
)
from .site_service import SiteService

__all__ = [
    "ComposeRobotRequest",
    "RobotComposition",
    "RobotCompositionNotFoundError",
    "RobotIdMismatchError",
    "SiteAdmissionRequest",
    "SiteAdmissionVerdict",
    "SiteError",
    "SiteService",
    "verify_site_verdict",
]
