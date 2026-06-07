"""Clearance route — the core demo endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request

from policy import ClearanceRequest, ClearanceService, ClearanceVerdict

router = APIRouter(tags=["clearance"])


@router.post("/clearance", response_model=ClearanceVerdict)
def request_clearance(
    request_body: ClearanceRequest, request: Request
) -> ClearanceVerdict:
    """Evaluate clearance from attestation results + curated policy rules.

    Verdict is signed by the clearance authority and written to the ledger.
    No LLM / narrator code participates in this path.
    """
    clearance: ClearanceService = request.app.state.clearance
    module_signers: dict = request.app.state.module_signers

    return clearance.clear(request_body, module_signers)
