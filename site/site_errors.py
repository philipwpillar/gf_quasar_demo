"""Site-specific exceptions for the api/ layer to map to HTTP."""


class SiteError(Exception):
    """Base class for site composition and admission failures."""


class DuplicateVendorError(SiteError):
    """Raised when a vendor_id is enrolled more than once."""

    def __init__(self, vendor_id: str, message: str | None = None) -> None:
        self.vendor_id = vendor_id
        super().__init__(
            message or f"Vendor {vendor_id!r} is already enrolled"
        )


class UnknownVendorError(SiteError):
    """Raised when compose or admission references an unregistered vendor."""

    def __init__(self, vendor_id: str, message: str | None = None) -> None:
        self.vendor_id = vendor_id
        super().__init__(
            message or f"Unknown vendor {vendor_id!r} — enrol before composing"
        )


class RobotCompositionNotFoundError(SiteError):
    """Raised when a robot_composed ledger entry cannot be resolved."""

    def __init__(self, robot_composed_seq: int, message: str | None = None) -> None:
        self.robot_composed_seq = robot_composed_seq
        super().__init__(
            message
            or f"No robot_composed entry at ledger sequence {robot_composed_seq}"
        )


class RobotIdMismatchError(SiteError):
    """Raised when admission request robot_id does not match the composition."""

    def __init__(
        self,
        *,
        request_robot_id: str,
        composition_robot_id: str,
        message: str | None = None,
    ) -> None:
        self.request_robot_id = request_robot_id
        self.composition_robot_id = composition_robot_id
        super().__init__(
            message
            or (
                f"robot_id mismatch: request has {request_robot_id!r}, "
                f"composition has {composition_robot_id!r}"
            )
        )
