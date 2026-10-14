"""Typed domain and application errors for portal read and write paths."""


class PortalError(Exception):
    """Base error for portal use cases."""

    def __init__(self, message: str, *, safe_context: str | None = None) -> None:
        super().__init__(message)
        self.safe_context = safe_context


class ResourceNotFoundError(PortalError):
    """Requested dataset, run, image, or related resource does not exist."""


class InvalidArtifactError(PortalError):
    """Stored JSON or image artifact failed validation or consistency checks."""


class DataStoreUnavailableError(PortalError):
    """Configured data root is missing or unreadable."""


class InvalidIdentifierError(PortalError, ValueError):
    """An identifier or relative storage key violates safety rules.

    Inherits `ValueError` so Pydantic field validators convert bad stored values
    into `ValidationError` (mapped to controlled 500s). Direct API checks still
    catch this type for 422 responses.
    """


class AuthenticationError(PortalError):
    """Missing or invalid authentication."""


class AuthorizationError(PortalError):
    """Authenticated principal is not permitted to access the portal."""


class ReviewConflictError(PortalError):
    """Stale revision, request-ID reuse with different content, or storage precondition failure."""

    def __init__(
        self,
        message: str,
        *,
        safe_context: str | None = None,
        conflict_kind: str = "revision",
    ) -> None:
        super().__init__(message, safe_context=safe_context)
        self.conflict_kind = conflict_kind


class ReviewMutationRejectedError(PortalError):
    """Mutation payload contains unsupported fields or invalid comment content."""


class ReviewDocumentTooLargeError(PortalError):
    """Persisting the review would exceed the documented per-image document size bound."""


class StorageConflictError(PortalError):
    """Storage-layer compare-and-write precondition failed (maps to application conflict)."""


class ConfigurationError(PortalError):
    """Required configuration is missing or unsafe for the selected mode."""
