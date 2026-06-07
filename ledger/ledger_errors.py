"""Ledger-specific exceptions."""


class LedgerError(Exception):
    """Base class for ledger failures."""


class ChainBrokenError(LedgerError):
    """Raised when a hash-chain link no longer holds."""

    def __init__(self, seq: int, message: str | None = None) -> None:
        self.seq = seq
        super().__init__(message or f"Ledger chain broken at sequence {seq}")


class LedgerIntegrityError(LedgerError):
    """Raised when an entry fails integrity validation."""

    def __init__(self, seq: int | None = None, message: str | None = None) -> None:
        self.seq = seq
        if message is None:
            if seq is None:
                message = "Ledger integrity check failed"
            else:
                message = f"Ledger integrity check failed at sequence {seq}"
        super().__init__(message)
