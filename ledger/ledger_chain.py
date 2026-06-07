"""In-memory append-only hash chain behind the ``Ledger`` public contract."""

from __future__ import annotations

from datetime import datetime, timezone

from ledger.ledger_errors import ChainBrokenError
from ledger.ledger_models import (
    GENESIS_PREV_HASH,
    EntryKind,
    LedgerEntry,
    compute_entry_hash,
    entry_hashable_view,
)
from shared.canonical_hashing import hash_entry


class Ledger:
    """Append-only, hash-chained decision log.

    Production replaces the in-memory store with an append-only table and WORM
    storage while preserving this contract and ``verify()`` semantics.
    """

    def __init__(self) -> None:
        self._entries: list[LedgerEntry] = []

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def head_hash(self) -> str | None:
        """Return the ``entry_hash`` of the latest entry, or ``None`` if empty."""
        if not self._entries:
            return None
        return self._entries[-1].entry_hash

    def get(self, seq: int) -> LedgerEntry:
        """Return the entry at *seq* (1-based)."""
        if seq < 1 or seq > len(self._entries):
            raise IndexError(f"No ledger entry at sequence {seq}")
        return self._entries[seq - 1]

    def append(
        self,
        kind: EntryKind,
        config_id: str,
        payload: dict,
        occurred_at: datetime | None = None,
    ) -> LedgerEntry:
        """Append a new entry. Existing entries are never mutated or deleted."""
        if occurred_at is None:
            occurred_at = datetime.now(timezone.utc)
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")

        seq = len(self._entries) + 1
        prev_hash = self._entries[-1].entry_hash if self._entries else GENESIS_PREV_HASH
        entry_hash = compute_entry_hash(
            seq=seq,
            kind=kind,
            occurred_at=occurred_at,
            config_id=config_id,
            payload=payload,
            prev_hash=prev_hash,
        )
        entry = LedgerEntry(
            seq=seq,
            kind=kind,
            occurred_at=occurred_at,
            config_id=config_id,
            payload=payload,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )
        self._entries.append(entry)
        return entry

    def verify(self) -> tuple[bool, int | None]:
        """Recompute the chain and return ``(True, None)`` or ``(False, first_broken_seq)``."""
        expected_prev_hash = GENESIS_PREV_HASH
        for entry in self._entries:
            if entry.prev_hash != expected_prev_hash:
                return False, entry.seq

            recomputed = compute_entry_hash(
                seq=entry.seq,
                kind=entry.kind,
                occurred_at=entry.occurred_at,
                config_id=entry.config_id,
                payload=entry.payload,
                prev_hash=entry.prev_hash,
            )
            if recomputed != entry.entry_hash:
                return False, entry.seq

            expected_prev_hash = entry.entry_hash

        return True, None

    def verify_or_raise(self) -> None:
        """Like ``verify()`` but raises ``ChainBrokenError`` on failure."""
        ok, broken_seq = self.verify()
        if not ok:
            assert broken_seq is not None
            raise ChainBrokenError(broken_seq)

    def export(self) -> list[dict]:
        """Return a JSON-serialisable snapshot for offline forensic review."""
        return [entry.model_dump(mode="json") for entry in self._entries]

    @staticmethod
    def verify_export(entries: list[dict]) -> tuple[bool, int | None]:
        """Re-verify an exported snapshot without a live ``Ledger`` instance."""
        expected_prev_hash = GENESIS_PREV_HASH
        for raw in entries:
            seq = raw["seq"]
            kind = EntryKind(raw["kind"])
            occurred_at = datetime.fromisoformat(raw["occurred_at"])
            config_id = raw["config_id"]
            payload = raw["payload"]
            prev_hash = raw["prev_hash"]
            entry_hash = raw["entry_hash"]

            if prev_hash != expected_prev_hash:
                return False, seq

            recomputed = hash_entry(
                entry_hashable_view(
                    seq=seq,
                    kind=kind,
                    occurred_at=occurred_at,
                    config_id=config_id,
                    payload=payload,
                    prev_hash=prev_hash,
                )
            )
            if recomputed != entry_hash:
                return False, seq

            expected_prev_hash = entry_hash

        return True, None
