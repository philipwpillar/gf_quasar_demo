"""Pydantic models for clearance policy — pure data, no chain behaviour.

Policy breadth is STUBBED: ``ClearanceRequest`` carries task_class and zone
fields that feed a curated single-task rule set, not the full
configuration-space optimiser. ``policy_mode`` on ``ClearanceVerdict`` must
always disclose ``stub_curated_single_task`` on screen.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

POLICY_MODE_STUB = "stub_curated_single_task"


class ClearanceRequest(BaseModel):
    """Request to evaluate clearance for an assembled module configuration."""

    model_config = ConfigDict(extra="forbid")

    config_id: str
    module_ids: list[str]
    task_class: str
    zone: str


class ModuleAttestationRef(BaseModel):
    """Provenance link to a mate-time attestation ledger entry — not a free bool."""

    model_config = ConfigDict(extra="forbid")

    module_id: str
    attested: bool
    ledger_seq: int = Field(ge=1)


class ClearanceVerdict(BaseModel):
    """Signed cleared / not-cleared verdict with plain-language reasons.

    ``reasons`` are operator- and narrator-facing plain language (e.g.
    "cleared for inspection in zone B" or
    "not cleared: module mod-002 failed attestation"). They are not error codes.
    """

    model_config = ConfigDict(extra="forbid")

    config_id: str
    cleared: bool
    reasons: list[str]
    attestation_refs: list[ModuleAttestationRef]
    policy_mode: str = POLICY_MODE_STUB
    authority_public_key_hex: str
    signature_hex: str
    ledger_seq: int = Field(ge=1)
    chain_head: str = Field(min_length=64, max_length=64)
