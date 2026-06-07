"""Read-only LLM narrator orchestration — explains, never decides.

The narrator reads a rendered ledger + policy snapshot and answers in plain
language. Its output is NEVER an input to clearance, compose, or admit. For
integrity questions it reports the backend ``ledger.verify()`` result; it does
not compute verdicts itself.
"""

from __future__ import annotations

from ledger import Ledger

from narrator.narrator_context import build_narrator_context
from narrator.narrator_llm import LlmCallable, call_llm
from narrator.narrator_models import NarratorAnswer, NarratorQuery


class NarratorService:
    """Read-only Q&A over the forensic ledger — never in the decision path."""

    def __init__(
        self,
        ledger: Ledger,
        *,
        llm_callable: LlmCallable | None = None,
    ) -> None:
        self._ledger = ledger
        self._llm_callable = llm_callable or call_llm

    def query(self, query: NarratorQuery) -> NarratorAnswer:
        context, grounded_on = build_narrator_context(
            self._ledger,
            question=query.question,
            config_id=query.config_id,
            robot_id=query.robot_id,
        )
        answer, configured = self._llm_callable(context, query.question)
        return NarratorAnswer(
            answer=answer,
            grounded_on=grounded_on,
            llm_configured=configured,
        )
