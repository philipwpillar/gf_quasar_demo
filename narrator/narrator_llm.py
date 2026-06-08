"""Isolated LLM provider boundary — env-driven, swappable behind one interface.

Uses the OpenAI-compatible ``/chat/completions`` shape (OpenRouter in the demo).
Key, model, and base URL are read from the environment at runtime; never
hardcoded or logged. When ``QUASAR_LLM_API_KEY`` is unset the narrator degrades
gracefully with a structured not-configured response.
"""

from __future__ import annotations

import os
from typing import Callable

import httpx

NOT_CONFIGURED_MESSAGE = (
    "LLM narrator is not configured. Set QUASAR_LLM_API_KEY (and optionally "
    "QUASAR_LLM_MODEL, QUASAR_LLM_BASE_URL) to enable plain-language answers "
    "over the read-only ledger view."
)

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"
REQUEST_TIMEOUT_SECONDS = 20.0

LlmCallable = Callable[[str, str], tuple[str, bool]]


def llm_configured() -> bool:
    return bool(os.environ.get("QUASAR_LLM_API_KEY", "").strip())


def _read_llm_config() -> tuple[str, str, str]:
    api_key = os.environ.get("QUASAR_LLM_API_KEY", "").strip()
    model = os.environ.get("QUASAR_LLM_MODEL", "").strip() or DEFAULT_MODEL
    base_url = os.environ.get("QUASAR_LLM_BASE_URL", "").strip() or DEFAULT_BASE_URL
    return api_key, model, base_url.rstrip("/")


def call_llm(context: str, question: str) -> tuple[str, bool]:
    """Call the configured provider; return (answer_text, llm_configured)."""
    api_key, model, base_url = _read_llm_config()
    if not api_key:
        return NOT_CONFIGURED_MESSAGE, False

    system_prompt = (
        "You are the GravitonForge Quasar read-only narrator. Explain the ledger "
        "record in plain language. You never decide clearance, admission, or "
        "integrity — you report what the record shows. When integrity data is "
        "present, quote the backend verify() result exactly."
    )
    user_prompt = f"{context}\n\nAnswer the question above using only this record."

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            payload = response.json()
        answer = payload["choices"][0]["message"]["content"].strip()
        return answer, True
    except httpx.TimeoutException:
        return (
            "The model took too long to respond (it may be busy or rate-limited). "
            "Try again or switch QUASAR_LLM_MODEL.",
            True,
        )
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 404:
            return (
                "Model not found — check QUASAR_LLM_MODEL is a current OpenRouter slug.",
                True,
            )
        if status == 429:
            return (
                "Rate-limited by the provider (free-tier limits). Wait a moment and retry.",
                True,
            )
        return (
            "The LLM provider returned an error. Check your API key and model settings, then retry.",
            True,
        )
    except httpx.RequestError:
        return (
            "Could not reach the LLM provider. Check QUASAR_LLM_BASE_URL and your network connection.",
            True,
        )
