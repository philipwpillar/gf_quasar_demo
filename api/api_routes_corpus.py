"""Corpus routes — provenance-linked telemetry ingest and dev seed."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from corpus import CorpusService, TelemetrySample, generate_samples
from ledger import LedgerEntry

router = APIRouter(tags=["corpus"])


class TelemetryIngestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ledger_seq: int = Field(ge=1)
    chain_head: str = Field(min_length=64, max_length=64)


class CorpusSeedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int = Field(ge=1, le=500, default=10)
    seed: int = 42


class CorpusSeedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated: int
    ingested: int
    seed: int


@router.post("/telemetry", response_model=TelemetryIngestResponse)
def ingest_telemetry(
    sample: TelemetrySample, request: Request
) -> TelemetryIngestResponse:
    """Ingest one telemetry sample; ``attestation_ref`` must resolve to attestation."""
    corpus: CorpusService = request.app.state.corpus
    entry: LedgerEntry = corpus.ingest(sample)
    return TelemetryIngestResponse(
        ledger_seq=entry.seq,
        chain_head=entry.entry_hash,
    )


@router.post("/corpus/seed", response_model=CorpusSeedResponse)
def seed_corpus(request_body: CorpusSeedRequest, request: Request) -> CorpusSeedResponse:
    """Generate synthetic samples against existing attestation entries (dev-gated)."""
    if os.environ.get("QUASAR_ENABLE_DEV_HOOKS", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        raise HTTPException(status_code=404, detail="Dev hooks disabled")

    ledger = request.app.state.ledger
    corpus: CorpusService = request.app.state.corpus
    samples = generate_samples(
        ledger, count=request_body.count, seed=request_body.seed
    )
    for sample in samples:
        corpus.ingest(sample)

    return CorpusSeedResponse(
        generated=len(samples),
        ingested=len(samples),
        seed=request_body.seed,
    )
