"""Attestation-specific exceptions for the api/ layer to map to HTTP."""


class AttestationError(Exception):
    """Base class for attestation failures."""


class UnknownModuleError(AttestationError):
    """Raised when an operation targets a module that is not enrolled."""

    def __init__(self, module_id: str, message: str | None = None) -> None:
        self.module_id = module_id
        super().__init__(message or f"Unknown module: {module_id}")


class DuplicateEnrolmentError(AttestationError):
    """Raised when enrolment is attempted for an already-enrolled module."""

    def __init__(self, module_id: str, message: str | None = None) -> None:
        self.module_id = module_id
        super().__init__(message or f"Module already enrolled: {module_id}")
