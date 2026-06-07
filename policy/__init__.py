"""Clearance engine.  [STUBBED — breadth]

Curated rule set for ONE task class (industrial inspection), not the
full configuration-space optimiser. Disclosed as stubbed on screen via
``policy_mode`` on every ``ClearanceVerdict``.
"""

from policy.policy_errors import (
    ClearanceError,
    MissingModuleSignerError,
    UnknownTaskClassError,
)
from policy.policy_models import (
    POLICY_MODE_STUB,
    ClearanceRequest,
    ClearanceVerdict,
    ModuleAttestationRef,
)
from policy.policy_service import ClearanceService, verify_verdict

__all__ = [
    "POLICY_MODE_STUB",
    "ClearanceError",
    "ClearanceRequest",
    "ClearanceService",
    "ClearanceVerdict",
    "MissingModuleSignerError",
    "ModuleAttestationRef",
    "UnknownTaskClassError",
    "verify_verdict",
]
