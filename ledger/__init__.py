"""Append-only, hash-chained decision ledger.  [REAL — load-bearing]

Each entry carries the hash of the previous entry. verify() recomputes
the chain and names the first broken sequence. Deterministic
serialisation (sorted keys, fixed separators) is the load-bearing
discipline: non-deterministic serialisation silently breaks the chain.
"""

from ledger.ledger_chain import Ledger
from ledger.ledger_errors import ChainBrokenError, LedgerError, LedgerIntegrityError
from ledger.ledger_models import EntryKind, LedgerEntry

__all__ = [
    "ChainBrokenError",
    "EntryKind",
    "Ledger",
    "LedgerEntry",
    "LedgerError",
    "LedgerIntegrityError",
]
