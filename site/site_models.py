"""Pydantic models for robot composition and site admission — pure data."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from policy.policy_models import POLICY_MODE_STUB, ModuleAttestationRef


class RobotComposition(BaseModel):
    """Tier 2 trust verdict: a robot identity composed from attested module refs."""

    model_config = ConfigDict(extra="forbid")

    robot_id: str
    vendor_key_id: str
    module_refs: list[ModuleAttestationRef]
    composed: bool
    reasons: list[str]
    ledger_seq: int = Field(ge=1)
    chain_head: str = Field(min_length=64, max_length=64)


class ComposeRobotRequest(BaseModel):
    """Request to compose a robot from enrolled modules (re-attests each module)."""

    model_config = ConfigDict(extra="forbid")

    robot_id: str
    vendor_key_id: str
    module_ids: list[str]


class SiteAdmissionRequest(BaseModel):
    """Request to admit or refuse a composed robot at the site gate."""

    model_config = ConfigDict(extra="forbid")

    robot_id: str
    task_class: str
    zone: str
    robot_composed_seq: int = Field(ge=1)


class SiteAdmissionVerdict(BaseModel):
    """Signed site-gate admission verdict — clearance/provenance only, never dispatch."""

    model_config = ConfigDict(extra="forbid")

    robot_id: str
    admitted: bool
    reasons: list[str]
    robot_composed_seq: int = Field(ge=1)
    task_class: str
    zone: str
    policy_mode: str = POLICY_MODE_STUB
    authority_public_key_hex: str
    signature_hex: str
    ledger_seq: int = Field(ge=1)
    chain_head: str = Field(min_length=64, max_length=64)
