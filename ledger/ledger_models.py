"""Pydantic models for ledger entries — pure data, no chain behaviour."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from shared.canonical_hashing import hash_entry

# Genesis entries anchor to a fixed 64-character zero prev_hash (32-byte SHA-256 width).
GENESIS_PREV_HASH = "0" * 64


class EntryKind(str, Enum):
    """All eight entry kinds carried by the ledger spine from line one."""

    MODULE_ENROLLED = "module_enrolled"
    VENDOR_ENROLLED = "vendor_enrolled"
    ATTESTATION = "attestation"
    ROBOT_COMPOSED = "robot_composed"
    SITE_ADMISSION = "site_admission"
    CLEARANCE_DECISION = "clearance_decision"
    TELEMETRY = "telemetry"
    DECOMMISSION = "decommission"


class LedgerEntry(BaseModel):
    """One append-only ledger record in the hash chain."""

    model_config = ConfigDict(extra="forbid")

    seq: int = Field(ge=1)
    kind: EntryKind
    occurred_at: datetime
    config_id: str
    payload: dict
    prev_hash: str = Field(min_length=64, max_length=64)
    entry_hash: str = Field(min_length=64, max_length=64)


def entry_hashable_view(
    *,
    seq: int,
    kind: EntryKind,
    occurred_at: datetime,
    config_id: str,
    payload: dict,
    prev_hash: str,
) -> dict:
    """Return the dict whose canonical serialisation is digested for ``entry_hash``.

    Covered fields (tamper-evident chain link):
      seq, kind, occurred_at, config_id, payload, prev_hash

    Excluded:
      entry_hash — it is the digest of this view, not part of its own preimage.
    """
    return {
        "seq": seq,
        "kind": kind.value,
        "occurred_at": occurred_at,
        "config_id": config_id,
        "payload": payload,
        "prev_hash": prev_hash,
    }


def compute_entry_hash(
    *,
    seq: int,
    kind: EntryKind,
    occurred_at: datetime,
    config_id: str,
    payload: dict,
    prev_hash: str,
) -> str:
    """Compute ``entry_hash`` from the hashable view."""
    return hash_entry(
        entry_hashable_view(
            seq=seq,
            kind=kind,
            occurred_at=occurred_at,
            config_id=config_id,
            payload=payload,
            prev_hash=prev_hash,
        )
    )
