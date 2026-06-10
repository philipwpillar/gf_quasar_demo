"""Module identity + mate-time attestation.  [REAL — load-bearing]

Freshness-bound challenge-response verified against a secure element.
Ed25519 in software for the demo; signing step swaps onto an
ATECC608 / TPM 2.0 dev board without changing the protocol.
We claim a real secure element and a real attestation protocol.
We do NOT claim a full hardware root-of-trust.
"""

from attestation.attestation_core import issue_challenge, verify_response
from attestation.attestation_errors import (
    AttestationError,
    DuplicateEnrolmentError,
    ModuleAlreadyRevokedError,
    UnknownModuleError,
)
from attestation.attestation_models import (
    AttestationReason,
    AttestationResult,
    Challenge,
    ModuleIdentity,
)
from attestation.attestation_service import AttestationService
from attestation.attestation_signer import Signer, SoftwareEd25519Signer

__all__ = [
    "AttestationError",
    "AttestationReason",
    "AttestationResult",
    "AttestationService",
    "Challenge",
    "DuplicateEnrolmentError",
    "ModuleAlreadyRevokedError",
    "ModuleIdentity",
    "Signer",
    "SoftwareEd25519Signer",
    "UnknownModuleError",
    "issue_challenge",
    "verify_response",
]
