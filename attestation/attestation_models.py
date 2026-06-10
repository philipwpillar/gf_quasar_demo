"""Pydantic models for mate-time attestation — pure data, no chain behaviour."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AttestationReason(str, Enum):
    """Outcome of a mate-time challenge-response verification."""

    OK = "ok"
    CHALLENGE_EXPIRED = "challenge_expired"
    SIGNATURE_INVALID = "signature_invalid"
    UNKNOWN_MODULE = "unknown_module"
    MODULE_REVOKED = "module_revoked"


class ModuleIdentity(BaseModel):
    """Enrolled module identity bound to an Ed25519 public key."""

    model_config = ConfigDict(extra="forbid")

    module_id: str
    public_key_hex: str


class Challenge(BaseModel):
    """Freshness-bound challenge issued to a module at mate-time."""

    model_config = ConfigDict(extra="forbid")

    module_id: str
    nonce_hex: str = Field(min_length=64, max_length=64)
    issued_at: datetime

    @field_validator("issued_at")
    @classmethod
    def issued_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("issued_at must be timezone-aware")
        return value


class AttestationResult(BaseModel):
    """Structured result of a mate-time attestation attempt."""

    model_config = ConfigDict(extra="forbid")

    module_id: str
    verified: bool
    reason: AttestationReason
    challenge_nonce_hex: str
    verified_at: datetime

    @field_validator("verified_at")
    @classmethod
    def verified_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("verified_at must be timezone-aware")
        return value
