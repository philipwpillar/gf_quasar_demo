"""Corpus-specific exceptions — imported by api/ for HTTP mapping."""


class CorpusError(Exception):
    """Base class for corpus boundary errors."""


class DanglingTelemetryError(CorpusError):
    """Telemetry ``attestation_ref`` does not resolve to an attestation entry."""

    def __init__(self, attestation_ref: int, detail: str) -> None:
        self.attestation_ref = attestation_ref
        self.detail = detail
        super().__init__(
            f"attestation_ref {attestation_ref} is dangling or invalid: {detail}"
        )
