"""Tests for the single canonical serialise-and-hash routine."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from shared.canonical_hashing import canonical_bytes, hash_entry, sha256_hex


def test_same_payload_hashes_identically_across_repeated_calls() -> None:
    payload = {"alpha": 1, "beta": "two", "nested": {"z": 9, "a": 1}}
    first = hash_entry(payload)
    second = hash_entry(payload)
    assert first == second
    assert len(first) == 64


def test_dict_key_order_does_not_affect_hash() -> None:
    payload_a = {"b": 2, "a": 1, "c": {"y": 2, "x": 1}}
    payload_b = {"c": {"x": 1, "y": 2}, "a": 1, "b": 2}
    assert hash_entry(payload_a) == hash_entry(payload_b)


def test_canonical_bytes_uses_sorted_keys_and_compact_separators() -> None:
    payload = {"b": 2, "a": 1}
    assert canonical_bytes(payload) == b'{"a":1,"b":2}'


def test_datetime_round_trips_stably_in_payload() -> None:
    dt = datetime(2026, 6, 7, 12, 30, 45, 123456, tzinfo=timezone.utc)
    payload = {"when": dt, "note": "sample"}
    first = hash_entry(payload)
    second = hash_entry({"note": "sample", "when": dt})
    assert first == second
    assert b"2026-06-07T12:30:45.123456+00:00" in canonical_bytes(payload)


def test_datetime_normalises_equivalent_timezones() -> None:
    from datetime import timedelta

    utc = datetime(2026, 1, 1, 5, 0, 0, tzinfo=timezone.utc)
    eastern = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone(timedelta(hours=-5)))
    assert hash_entry({"t": utc}) == hash_entry({"t": eastern})


def test_naive_datetime_is_rejected() -> None:
    naive = datetime(2026, 6, 7, 12, 0, 0)
    with pytest.raises(ValueError, match="timezone-aware"):
        canonical_bytes({"when": naive})


def test_sha256_hex_matches_hashlib() -> None:
    data = b"quasar"
    import hashlib

    assert sha256_hex(data) == hashlib.sha256(data).hexdigest()


def test_exported_canonical_form_is_valid_json() -> None:
    payload = {"kind": "attestation", "score": 1.0, "tags": ["a", "b"]}
    decoded = json.loads(canonical_bytes(payload).decode("utf-8"))
    assert decoded == payload
