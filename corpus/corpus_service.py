"""Corpus ingest orchestration — validates provenance, appends telemetry entries.

Every sample must resolve ``attestation_ref`` to a real ``attestation`` ledger
entry before append. This guard is structural: dangling telemetry is rejected,
not logged and forgotten.
"""

from __future__ import annotations

from ledger import EntryKind, Ledger, LedgerEntry

from corpus.corpus_errors import DanglingTelemetryError
from corpus.corpus_models import TelemetrySample


def _validate_attestation_ref(ledger: Ledger, attestation_ref: int) -> None:
    try:
        entry = ledger.get(attestation_ref)
    except IndexError as exc:
        raise DanglingTelemetryError(
            attestation_ref, "no ledger entry at that sequence"
        ) from exc

    if entry.kind != EntryKind.ATTESTATION:
        raise DanglingTelemetryError(
            attestation_ref,
            f"entry kind is {entry.kind.value}, expected attestation",
        )


class CorpusService:
    """Validate provenance-linked telemetry and append to the forensic ledger."""

    def __init__(self, ledger: Ledger) -> None:
        self._ledger = ledger

    def ingest(self, sample: TelemetrySample) -> LedgerEntry:
        """Reject dangling refs; append ``telemetry`` on success."""
        _validate_attestation_ref(self._ledger, sample.attestation_ref)
        return self._ledger.append(
            EntryKind.TELEMETRY,
            sample.config_id,
            sample.model_dump(mode="json"),
            occurred_at=sample.ts,
        )
