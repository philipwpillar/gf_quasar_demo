"""Policy-specific exceptions for the api/ layer to map to HTTP."""


class ClearanceError(Exception):
    """Base class for clearance failures."""


class UnknownTaskClassError(ClearanceError):
    """Raised when a clearance request targets an unsupported task class."""

    def __init__(self, task_class: str, message: str | None = None) -> None:
        self.task_class = task_class
        super().__init__(
            message or f"Unknown or unsupported task class: {task_class}"
        )


class MissingModuleSignerError(ClearanceError):
    """Raised when a module has no demo signer available for attestation."""

    def __init__(self, module_id: str, message: str | None = None) -> None:
        self.module_id = module_id
        super().__init__(
            message or f"No signer available for module: {module_id}"
        )
