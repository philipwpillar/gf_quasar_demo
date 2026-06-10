"""Module identity + mate-time attestation.  [REAL — load-bearing]

Freshness-bound challenge-response with algorithm-aware verification.
Ed25519 and ECDSA P-256 in software custody today; secure-element custody
for P-256 arrives in step 8b. The enrolled identity records key_algorithm.
We claim a real attestation protocol. We do NOT claim a full hardware
root-of-trust.
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
    KeyAlgorithm,
    ModuleIdentity,
)
from attestation.attestation_service import AttestationService
from attestation.attestation_signer import (
    Signer,
    SoftwareEd25519Signer,
    SoftwareP256Signer,
)

__all__ = [
    "AttestationError",
    "AttestationReason",
    "AttestationResult",
    "AttestationService",
    "Challenge",
    "DuplicateEnrolmentError",
    "KeyAlgorithm",
    "ModuleAlreadyRevokedError",
    "ModuleIdentity",
    "Signer",
    "SoftwareEd25519Signer",
    "SoftwareP256Signer",
    "UnknownModuleError",
    "issue_challenge",
    "verify_response",
]
