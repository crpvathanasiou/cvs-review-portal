"""Development identity mode for loopback-only local testing.

This is **not** production authentication. The actor is server-configured
(``DEVELOPMENT_ACTOR``) and never taken from the browser or request body.
Must be enabled explicitly via ``IDENTITY_MODE=development``.
"""

from __future__ import annotations

from starlette.requests import Request

from cvs_review_portal.application.identity import AuthenticatedPrincipal
from cvs_review_portal.domain.errors import AuthenticationError, AuthorizationError

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "testclient"})


class DevelopmentIdentityProvider:
    """Authorize a fixed development actor on loopback requests only."""

    def __init__(self, *, actor: str, allowed_actors: frozenset[str] | None = None) -> None:
        if not actor or not actor.strip():
            raise ValueError("development actor must be non-empty")
        self._actor = actor.strip()
        allowed = allowed_actors if allowed_actors is not None else frozenset({self._actor})
        self._allowed = frozenset(a.strip() for a in allowed if a and a.strip())

    def resolve(self, request: Request) -> AuthenticatedPrincipal:
        client = request.client
        host = client.host if client is not None else None
        if host not in _LOOPBACK_HOSTS:
            raise AuthenticationError(
                "Development identity is limited to loopback clients.",
                safe_context="identity=development reason=non_loopback",
            )
        if self._actor not in self._allowed:
            raise AuthorizationError(
                "Development actor is not in the allowed-user policy.",
                safe_context="identity=development reason=not_allowed",
            )
        return AuthenticatedPrincipal(actor=self._actor, identity_source="development")
