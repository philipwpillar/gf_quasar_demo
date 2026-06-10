"""Site routes — vendor enrolment, robot composition (Tier 2), site admission (Tier 3)."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from attestation import SoftwareEd25519Signer
from quasar_site import (
    ComposeRobotRequest,
    RobotComposition,
    SiteAdmissionRequest,
    SiteAdmissionVerdict,
    SiteService,
    VendorIdentity,
)

router = APIRouter(tags=["site"])


class VendorEnrolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor_id: str


class VendorEnrolResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor_id: str
    public_key_hex: str
    ledger_seq: int


@router.post("/vendors/enrol", response_model=VendorEnrolResponse)
def enrol_vendor(request_body: VendorEnrolRequest, request: Request) -> VendorEnrolResponse:
    """Register a vendor authority and its demo-held signing key."""
    site: SiteService = request.app.state.site
    vendor_signers: dict = request.app.state.vendor_signers

    signer = request.app.state.new_vendor_signer()
    identity: VendorIdentity = site.enrol_vendor(request_body.vendor_id, signer)
    vendor_signers[identity.vendor_id] = signer

    ledger = request.app.state.ledger
    return VendorEnrolResponse(
        vendor_id=identity.vendor_id,
        public_key_hex=identity.public_key_hex,
        ledger_seq=len(ledger),
    )


@router.post("/robots/compose", response_model=RobotComposition)
def compose_robot(
    request_body: ComposeRobotRequest, request: Request
) -> RobotComposition:
    """Compose a robot from enrolled modules (re-attests each module).

    Writes ``robot_composed`` to the ledger. No LLM / narrator code participates.
    """
    site: SiteService = request.app.state.site
    module_signers: dict = request.app.state.module_signers
    vendor_signers: dict = request.app.state.vendor_signers

    return site.compose_robot(request_body, module_signers, vendor_signers)


@router.post("/site/admit", response_model=SiteAdmissionVerdict)
def admit_robot(
    request_body: SiteAdmissionRequest, request: Request
) -> SiteAdmissionVerdict:
    """Admit or refuse a composed robot for a task in a zone.

    Writes a signed ``site_admission`` provenance event — never task dispatch.
    """
    site: SiteService = request.app.state.site
    return site.admit_robot(request_body)


class CorruptVendorSignerRequest(BaseModel):
    """Dev-only: swap a vendor signer to trigger forged-vendor-identity demo."""

    model_config = ConfigDict(extra="forbid")

    vendor_id: str


class CorruptVendorSignerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor_id: str
    message: str


@router.post("/dev/corrupt-vendor-signer", response_model=CorruptVendorSignerResponse)
def corrupt_vendor_signer(
    request_body: CorruptVendorSignerRequest, request: Request
) -> CorruptVendorSignerResponse:
    """Replace a demo-held vendor signer (env-gated; forged-vendor demo only)."""
    if os.environ.get("QUASAR_ENABLE_DEV_HOOKS", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        raise HTTPException(status_code=404, detail="Dev hooks disabled")

    vendor_signers: dict = request.app.state.vendor_signers
    if request_body.vendor_id not in vendor_signers:
        from quasar_site import UnknownVendorError

        raise UnknownVendorError(request_body.vendor_id)

    vendor_signers[request_body.vendor_id] = SoftwareEd25519Signer()
    return CorruptVendorSignerResponse(
        vendor_id=request_body.vendor_id,
        message=(
            "Demo vendor signer swapped — next compose will present a forged "
            "vendor identity at the site gate."
        ),
    )
