"""Deterministic serialise-and-hash primitives for the Quasar trust layer.

Why determinism is load-bearing
--------------------------------
The forensic ledger is a hash chain: each entry's digest binds to the previous
entry's digest. If two implementations (or two runs of the same code) serialise
the same logical payload to different bytes, they produce different hashes for
identical decisions. The chain still *looks* valid locally but third-party
``verify()`` tooling — and any other component that recomputes digests — will
report a break at the first divergent entry. That failure is silent until someone
runs verify, and it destroys the demo's central claim: that provenance is
forensically legible and independently checkable.

There must be exactly ONE canonical serialisation routine in this repository.
Ledger code, tests, and external verify tooling must all call these functions.
No component-specific logic belongs here.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def _format_datetime(dt: datetime) -> str:
    """Encode a timezone-aware datetime as fixed ISO-8601 UTC with microseconds."""
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    utc = dt.astimezone(timezone.utc)
    return utc.isoformat(timespec="microseconds")


def _json_default(obj: Any) -> str:
    if isinstance(obj, datetime):
        return _format_datetime(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serialisable")


def canonical_bytes(payload: dict) -> bytes:
    """Return UTF-8 bytes of the canonical JSON form of *payload*.

    Uses sorted keys, ``(",", ":")`` separators, ``ensure_ascii=False``, and
    encodes timezone-aware datetimes as fixed ISO-8601 UTC strings.
    """
    canonical_json = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    )
    return canonical_json.encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def hash_entry(payload: dict) -> str:
    """Return ``sha256_hex(canonical_bytes(payload))``."""
    return sha256_hex(canonical_bytes(payload))
