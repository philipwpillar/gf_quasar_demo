"""Attestation routes — module enrolment and mate-time attestation."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from attestation import AttestationService, ModuleIdentity
from attestation.attestation_models import AttestationResult

router = APIRouter(tags=["attestation"])


class EnrolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_id: str


class EnrolResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_id: str
    public_key_hex: str


class AttestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_id: str


@router.post("/modules/enrol", response_model=EnrolResponse)
def enrol_module(request_body: EnrolRequest, request: Request) -> EnrolResponse:
    """Register a module identity and its demo-held signing key."""
    attestation: AttestationService = request.app.state.attestation
    module_signers: dict = request.app.state.module_signers

    signer = request.app.state.new_module_signer()
    identity: ModuleIdentity = attestation.enrol(request_body.module_id, signer)
    module_signers[identity.module_id] = signer

    return EnrolResponse(
        module_id=identity.module_id,
        public_key_hex=identity.public_key_hex,
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
