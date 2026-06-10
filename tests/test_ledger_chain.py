"""Tests for the append-only hash-chained ledger."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from ledger import ChainBrokenError, EntryKind, Ledger, LedgerEntry
from ledger.ledger_models import GENESIS_PREV_HASH, compute_entry_hash


def _sample_time(seq: int) -> datetime:
    return datetime(2026, 6, 7, 12, 0, seq, tzinfo=timezone.utc)


def _append_three(ledger: Ledger) -> list[LedgerEntry]:
    entries = [
        ledger.append(
            EntryKind.MODULE_ENROLLED,
            "cfg-demo",
            {"module_id": "mod-001", "public_key": "abc"},
            occurred_at=_sample_time(1),
        ),
        ledger.append(
            EntryKind.ATTESTATION,
            "cfg-demo",
            {"module_id": "mod-001", "result": "pass"},
            occurred_at=_sample_time(2),
        ),
        ledger.append(
            EntryKind.ROBOT_COMPOSED,
            "cfg-demo",
            {"robot_id": "bot-001", "modules": ["mod-001"]},
            occurred_at=_sample_time(3),
        ),
    ]
    return entries


def test_clean_multi_entry_chain_verifies() -> None:
    ledger = Ledger()
    _append_three(ledger)
    assert ledger.verify() == (True, None)
    assert len(ledger) == 3


def test_genesis_prev_hash_is_sixty_four_zeros() -> None:
    ledger = Ledger()
    entry = ledger.append(
        EntryKind.MODULE_ENROLLED,
        "cfg-demo",
        {"module_id": "mod-001"},
        occurred_at=_sample_time(1),
    )
    assert entry.prev_hash == GENESIS_PREV_HASH
    assert entry.prev_hash == "0" * 64


def test_seq_is_strictly_increasing_with_no_gaps() -> None:
    ledger = Ledger()
    entries = _append_three(ledger)
    assert [entry.seq for entry in entries] == [1, 2, 3]
    assert ledger.get(1).seq == 1
    assert ledger.get(3).seq == 3


def test_head_hash_matches_last_entry() -> None:
    ledger = Ledger()
    entries = _append_three(ledger)
    assert ledger.head_hash == entries[-1].entry_hash


@pytest.mark.parametrize(
    ("target_seq", "field", "tampered_value"),
    [
        (1, "payload", {"module_id": "mod-TAMPERED"}),
        (2, "payload", {"module_id": "mod-001", "result": "fail"}),
        (3, "payload", {"robot_id": "bot-TAMPERED", "modules": ["mod-001"]}),
    ],
)
def test_payload_tamper_is_caught_at_exact_seq(
    target_seq: int,
    field: str,
    tampered_value: dict,
) -> None:
    ledger = Ledger()
    _append_three(ledger)
    broken = ledger.get(target_seq)
    tampered = broken.model_copy(update={field: tampered_value})
    ledger._entries[target_seq - 1] = tampered
    assert ledger.verify() == (False, target_seq)


def test_prev_hash_tamper_is_caught_at_exact_seq() -> None:
    ledger = Ledger()
    _append_three(ledger)
    middle = ledger.get(2)
    tampered = middle.model_copy(update={"prev_hash": "f" * 64})
    ledger._entries[1] = tampered
    assert ledger.verify() == (False, 2)


def test_broken_link_from_prior_entry_surfaces_at_next_seq() -> None:
    ledger = Ledger()
    _append_three(ledger)
    first = ledger.get(1)
    tampered_payload = {"module_id": "mod-TAMPERED"}
    recomputed_hash = compute_entry_hash(
        seq=first.seq,
        kind=first.kind,
        occurred_at=first.occurred_at,
        config_id=first.config_id,
        payload=tampered_payload,
        prev_hash=first.prev_hash,
    )
    tampered_first = first.model_copy(
        update={"payload": tampered_payload, "entry_hash": recomputed_hash}
    )
    ledger._entries[0] = tampered_first
    assert ledger.verify() == (False, 2)


def test_export_is_json_serialisable_and_reverifiable() -> None:
    ledger = Ledger()
    _append_three(ledger)
    exported = ledger.export()
    serialised = json.dumps(exported)
    round_trip = json.loads(serialised)
    assert round_trip == exported
    assert Ledger.verify_export(round_trip) == (True, None)


def test_verify_or_raise_on_intact_chain() -> None:
    ledger = Ledger()
    _append_three(ledger)
    ledger.verify_or_raise()


def test_verify_or_raise_raises_chain_broken_error() -> None:
    ledger = Ledger()
    _append_three(ledger)
    last = ledger.get(3)
    ledger._entries[2] = last.model_copy(update={"payload": {"robot_id": "broken"}})
    with pytest.raises(ChainBrokenError) as exc_info:
        ledger.verify_or_raise()
    assert exc_info.value.seq == 3


def test_all_entry_kinds_are_defined() -> None:
    expected = {
        "module_enrolled",
        "vendor_enrolled",
        "attestation",
        "robot_composed",
        "site_admission",
        "clearance_decision",
        "telemetry",
        "decommission",
    }
    assert {kind.value for kind in EntryKind} == expected
