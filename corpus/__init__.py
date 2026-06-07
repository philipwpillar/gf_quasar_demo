"""Telemetry sink + synthetic seed generator.  [STUBBED — depth]

Seeded with synthetic telemetry, not a real fleet. Schema is
full-fidelity (insurance-grade + exchange-grade) from day one.
Every sample carries an attestation_ref back to a real ledger entry;
telemetry detached from a verified configuration is worthless by design.
"""

from corpus.corpus_errors import CorpusError, DanglingTelemetryError
from corpus.corpus_models import EnvironmentTag, TelemetrySample
from corpus.corpus_seed import generate_samples
from corpus.corpus_service import CorpusService

__all__ = [
    "CorpusError",
    "CorpusService",
    "DanglingTelemetryError",
    "EnvironmentTag",
    "TelemetrySample",
    "generate_samples",
]
