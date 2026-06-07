"""LLM assistant over a read-only ledger view.  [STUB / READ-ONLY]

Explains the record; never decides. Output is NEVER an input to clearance,
robot composition, or site admission.
"""

from narrator.narrator_errors import NarratorContextError, NarratorError
from narrator.narrator_llm import NOT_CONFIGURED_MESSAGE, call_llm, llm_configured
from narrator.narrator_models import NarratorAnswer, NarratorQuery
from narrator.narrator_service import NarratorService

__all__ = [
    "NOT_CONFIGURED_MESSAGE",
    "NarratorAnswer",
    "NarratorContextError",
    "NarratorError",
    "NarratorQuery",
    "NarratorService",
    "call_llm",
    "llm_configured",
]
