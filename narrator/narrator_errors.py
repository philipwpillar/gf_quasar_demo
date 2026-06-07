"""Narrator-specific exceptions — imported by api/ for HTTP mapping."""


class NarratorError(Exception):
    """Base class for narrator boundary errors."""


class NarratorContextError(NarratorError):
    """The read-only context could not be built for the query."""
