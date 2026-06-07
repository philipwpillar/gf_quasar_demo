"""Pydantic models for the read-only LLM narrator — pure boundary shapes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class NarratorQuery(BaseModel):
    """Natural-language question over a read-only ledger + policy view."""

    model_config = ConfigDict(extra="forbid")

    question: str
    config_id: str | None = None
    robot_id: str | None = None


class NarratorAnswer(BaseModel):
    """Plain-language explanation grounded on ledger sequence references."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    grounded_on: list[int] = Field(default_factory=list)
    llm_configured: bool
