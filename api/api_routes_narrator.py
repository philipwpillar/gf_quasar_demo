"""Narrator routes — read-only Q&A; cannot affect any verdict."""

from __future__ import annotations

from fastapi import APIRouter, Request

from narrator import NarratorAnswer, NarratorQuery, NarratorService

router = APIRouter(tags=["narrator"])


@router.post("/assistant/query", response_model=NarratorAnswer)
def assistant_query(query: NarratorQuery, request: Request) -> NarratorAnswer:
    """Plain-language explanation over the ledger. Read-only — never in decision paths."""
    narrator: NarratorService = request.app.state.narrator
    return narrator.query(query)
