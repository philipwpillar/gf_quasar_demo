"""Ledger audit routes — third-party verify and export."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from ledger import Ledger

router = APIRouter(tags=["ledger"])


class LedgerVerifyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intact: bool
    first_broken_seq: int | None


@router.get("/ledger/verify", response_model=LedgerVerifyResponse)
def verify_ledger(request: Request) -> LedgerVerifyResponse:
    """Recompute the hash chain; any third party can run the same check offline."""
    ledger: Ledger = request.app.state.ledger
    intact, first_broken_seq = ledger.verify()
    return LedgerVerifyResponse(intact=intact, first_broken_seq=first_broken_seq)


@router.get("/ledger/export")
def export_ledger(request: Request) -> list[dict]:
    """Return the full chain JSON for offline forensic review."""
    ledger: Ledger = request.app.state.ledger
    return ledger.export()
