"""Telemetry sample models — full-fidelity schema, STUBBED synthetic data.

Depth is STUBBED (synthetic generator, not a real fleet) but the schema is
full-fidelity from day one (insurance-grade + exchange-grade). Every sample
MUST carry ``attestation_ref`` — the ledger seq of the attestation that cleared
its configuration. Telemetry detached from a verified configuration is worthless
by design; that link is structural, not cosmetic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EnvironmentTag = Literal[
    "terrestrial_indoor",
    "terrestrial_outdoor",
    "subterranean",
    "marine",
    "aerial",
    "lunar",
]


class TelemetrySample(BaseModel):
    """One behaviour sample, provenance-linked to a mate-time attestation entry."""

    model_config = ConfigDict(extra="forbid")

    config_id: str
    module_id: str
    attestation_ref: int = Field(ge=1)
    ts: datetime

    actuation_load: float | None = None
    fault_flag: bool = False
    fault_class: str | None = None
    cycles_since_mate: int = Field(ge=0, default=0)

    utilisation: float | None = None
    location_hash: str | None = None
    environment_tag: EnvironmentTag | None = None

    extra: dict = Field(default_factory=dict)

    @field_validator("ts")
    @classmethod
    def ts_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("ts must be timezone-aware")
        return value
