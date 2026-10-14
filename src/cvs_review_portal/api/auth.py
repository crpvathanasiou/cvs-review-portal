"""Authentication dependency and CSRF / same-origin guards for cookie writes."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import urlparse

from fastapi import Depends, Header, HTTPException, Request

from cvs_review_portal.api.deps import get_identity_provider
from cvs_review_portal.application.identity import AuthenticatedPrincipal, IdentityProvider
from cvs_review_portal.domain.errors import AuthenticationError, AuthorizationError


def require_principal(
    request: Request,
    identity: Annotated[IdentityProvider, Depends(get_identity_provider)],
) -> AuthenticatedPrincipal:
    try:
        return identity.resolve(request)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=401,
            detail={"message": str(exc), **_ctx(exc.safe_context)},
        ) from exc
    except AuthorizationError as exc:
        raise HTTPException(
            status_code=403,
            detail={"message": str(exc), **_ctx(exc.safe_context)},
        ) from exc


def require_json_mutation(
    request: Request,
    content_type: Annotated[str | None, Header(alias="content-type")] = None,
    origin: Annotated[str | None, Header()] = None,
    referer: Annotated[str | None, Header()] = None,
) -> None:
    """Enforce JSON request contract and same-origin checks for mutating requests.

    Cookie-authenticated writes must not be triggered by cross-site form posts.
    CORS is not opened: browsers must use same-origin fetches with credentials.
    """
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    normalized = (content_type or "").split(";")[0].strip().lower()
    if normalized != "application/json":
        raise HTTPException(
            status_code=415,
            detail={
                "message": "Mutating requests must use Content-Type: application/json.",
                "context": "content_type",
            },
        )
    if not _same_origin(request, origin=origin, referer=referer):
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Cross-origin mutating requests are not allowed.",
                "context": "csrf=origin",
            },
        )


def _same_origin(
    request: Request,
    *,
    origin: str | None,
    referer: str | None,
) -> bool:
    expected_host = request.url.hostname
    expected_scheme = request.url.scheme
    if expected_host is None:
        return False

    if origin:
        parsed = urlparse(origin)
        return (
            parsed.scheme == expected_scheme
            and parsed.hostname == expected_host
            and _ports_compatible(parsed.port, request.url.port, expected_scheme)
        )

    if referer:
        parsed = urlparse(referer)
        return (
            parsed.scheme == expected_scheme
            and parsed.hostname == expected_host
            and _ports_compatible(parsed.port, request.url.port, expected_scheme)
        )

    # Non-browser clients (tests, curl) may omit Origin/Referer; allow only when
    # both are absent. Browser credentialed navigations should send one of them.
    return True


def _ports_compatible(parsed_port: int | None, request_port: int | None, scheme: str) -> bool:
    default = 443 if scheme == "https" else 80
    left = parsed_port if parsed_port is not None else default
    right = request_port if request_port is not None else default
    return left == right


def _ctx(safe_context: str | None) -> dict[str, str]:
    if safe_context:
        return {"context": safe_context}
    return {}
