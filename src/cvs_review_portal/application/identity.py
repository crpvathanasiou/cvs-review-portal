"""Injectable identity / access boundary for portal routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from starlette.requests import Request


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """Stable actor derived from validated identity (never from the request body)."""

    actor: str
    identity_source: str


class IdentityProvider(Protocol):
    """Resolve and authorize the caller for protected portal routes."""

    def resolve(self, request: Request) -> AuthenticatedPrincipal:
        """Return an authorized principal or raise Authentication/AuthorizationError."""
        ...
