"""Attestation routes — module enrolment and mate-time attestation."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from attestation import (
    AttestationService,
    KeyAlgorithm,
    ModuleIdentity,
    SoftwareEd25519Signer,
    SoftwareP256Signer,
)
from attestation.attestation_models import AttestationResult
from attestation.attestation_signer import Signer

router = APIRouter(tags=["attestation"])


def _module_signer_for_algorithm(key_algorithm: KeyAlgorithm) -> Signer:
    if key_algorithm == KeyAlgorithm.ECDSA_P256:
        return SoftwareP256Signer()
    return SoftwareEd25519Signer()


class EnrolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_id: str
    key_algorithm: KeyAlgorithm = KeyAlgorithm.ED25519


class EnrolResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_id: str
    public_key_hex: str
    key_algorithm: KeyAlgorithm


class AttestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_id: str


@router.post("/modules/enrol", response_model=EnrolResponse)
def enrol_module(request_body: EnrolRequest, request: Request) -> EnrolResponse:
    """Register a module identity and its demo-held signing key."""
    attestation: AttestationService = request.app.state.attestation
    module_signers: dict = request.app.state.module_signers

    signer = _module_signer_for_algorithm(request_body.key_algorithm)
    identity: ModuleIdentity = attestation.enrol(request_body.module_id, signer)
    module_signers[identity.module_id] = signer

    return EnrolResponse(
        module_id=identity.module_id,
        public_key_hex=identity.public_key_hex,
        key_algorithm=identity.key_algorithm,
    )


class RevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_id: str
    reason: str


class RevokeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_id: str
    ledger_seq: int
    revoked_at: str


@router.post("/modules/revoke", response_model=RevokeResponse)
def revoke_module(request_body: RevokeRequest, request: Request) -> RevokeResponse:
    """Administratively revoke an enrolled module (governance deprovisioning).

    Records a ``decommission`` ledger entry and marks the module revoked so
    subsequent attestations fail without issuing a challenge. This does NOT
    prove the physical module is disabled.
    """
    attestation: AttestationService = request.app.state.attestation
    entry = attestation.revoke(request_body.module_id, request_body.reason)
    return RevokeResponse(
        module_id=request_body.module_id,
        ledger_seq=entry.seq,
        revoked_at=entry.payload["revoked_at"],
    )


@router.post("/attest", response_model=AttestationResult)
def attest_module(request_body: AttestRequest, request: Request) -> AttestationResult:
    """Run mate-time challenge-response for one enrolled module."""
    attestation: AttestationService = request.app.state.attestation
    module_signers: dict = request.app.state.module_signers

    signer = module_signers.get(request_body.module_id)
    if signer is None:
        from attestation import UnknownModuleError

        raise UnknownModuleError(request_body.module_id)

    return attestation.attest(request_body.module_id, signer)


class CorruptSignerRequest(BaseModel):
    """Dev-only: swap a module signer to trigger mate-time attestation failure."""

    model_config = ConfigDict(extra="forbid")

    module_id: str


class CorruptSignerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_id: str
    message: str


@router.post("/dev/corrupt-module-signer", response_model=CorruptSignerResponse)
def corrupt_module_signer(
    request_body: CorruptSignerRequest, request: Request
) -> CorruptSignerResponse:
    """Replace a demo-held module signer (env-gated; for propagation-failure demo only)."""
    if os.environ.get("QUASAR_ENABLE_DEV_HOOKS", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        raise HTTPException(status_code=404, detail="Dev hooks disabled")

    module_signers: dict = request.app.state.module_signers
    if request_body.module_id not in module_signers:
        from attestation import UnknownModuleError

        raise UnknownModuleError(request_body.module_id)

    module_signers[request_body.module_id] = SoftwareEd25519Signer()
    return CorruptSignerResponse(
        module_id=request_body.module_id,
        message=(
            "Demo signer swapped — next compose will record mate-time attestation "
            "failure for this module."
        ),
    )
