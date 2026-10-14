"""Azure App Service built-in authentication header adapter.

Trust assumptions (deployment must enforce):

* The App Service authentication / Easy Auth layer validates the user session.
* That layer strips client-supplied identity headers and injects validated ones
  (``X-MS-CLIENT-PRINCIPAL``, ``X-MS-CLIENT-PRINCIPAL-ID``, ``X-MS-CLIENT-PRINCIPAL-NAME``).
* The application is not reachable by bypassing that layer (no direct public
  exposure of the container/process).

Parsing a base64 principal header alone is **not** authentication; it is only
safe behind the configured hosting trust boundary above. Login alone does not
grant access — the actor must also match the configured allowed-user policy.

Canonical actor format (Entra): ``aad:{tenant_id}:{object_id}``.

Convenience headers must not change the actor format. When
``X-MS-CLIENT-PRINCIPAL-ID`` is present it must equal the object id derived from
claims; otherwise the request is rejected as inconsistent. Historical stored
actor strings are never rewritten.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, cast

from starlette.requests import Request

from cvs_review_portal.application.identity import AuthenticatedPrincipal
from cvs_review_portal.domain.errors import AuthenticationError, AuthorizationError

logger = logging.getLogger("cvs_review_portal.infrastructure.identity_azure")

_HEADER_PRINCIPAL = "x-ms-client-principal"
_HEADER_PRINCIPAL_ID = "x-ms-client-principal-id"
_HEADER_PRINCIPAL_NAME = "x-ms-client-principal-name"

_OID_CLAIM_TYPES = (
    "oid",
    "objectId",
    "http://schemas.microsoft.com/identity/claims/objectidentifier",
)
_TID_CLAIM_TYPES = (
    "tid",
    "tenantId",
    "http://schemas.microsoft.com/identity/claims/tenantid",
)


class AzureAppServiceIdentityProvider:
    """Derive a stable actor from trusted App Service identity headers."""

    def __init__(self, *, allowed_actors: frozenset[str]) -> None:
        if not allowed_actors:
            raise ValueError("allowed_actors must not be empty for Azure identity mode")
        self._allowed = frozenset(a.strip() for a in allowed_actors if a and a.strip())
        if not self._allowed:
            raise ValueError("allowed_actors must not be empty for Azure identity mode")

    def resolve(self, request: Request) -> AuthenticatedPrincipal:
        actor = self._derive_actor(request)
        if actor not in self._allowed:
            raise AuthorizationError(
                "Authenticated user is not permitted to access this portal.",
                safe_context="identity=azure_app_service reason=not_allowed",
            )
        return AuthenticatedPrincipal(actor=actor, identity_source="azure_app_service")

    def _derive_actor(self, request: Request) -> str:
        encoded = (request.headers.get(_HEADER_PRINCIPAL) or "").strip()
        if not encoded:
            raise AuthenticationError(
                "Missing or invalid Azure authentication identity.",
                safe_context="identity=azure_app_service reason=missing_principal",
            )
        claims = _parse_principal_claims(encoded)
        oid = _first_claim(claims, _OID_CLAIM_TYPES)
        tid = _first_claim(claims, _TID_CLAIM_TYPES)
        if not oid or not tid:
            raise AuthenticationError(
                "Missing or invalid Azure authentication identity.",
                safe_context="identity=azure_app_service reason=missing_tenant_or_object",
            )
        if _conflicting_claim_values(claims, _OID_CLAIM_TYPES, oid):
            raise AuthenticationError(
                "Missing or invalid Azure authentication identity.",
                safe_context="identity=azure_app_service reason=conflicting_object",
            )
        if _conflicting_claim_values(claims, _TID_CLAIM_TYPES, tid):
            raise AuthenticationError(
                "Missing or invalid Azure authentication identity.",
                safe_context="identity=azure_app_service reason=conflicting_tenant",
            )

        principal_id = (request.headers.get(_HEADER_PRINCIPAL_ID) or "").strip()
        if principal_id and principal_id != oid:
            raise AuthenticationError(
                "Missing or invalid Azure authentication identity.",
                safe_context="identity=azure_app_service reason=inconsistent_principal_id",
            )
        # Name header is informational only and must not change actor format.
        _ = (request.headers.get(_HEADER_PRINCIPAL_NAME) or "").strip()
        return f"aad:{tid}:{oid}"


def _parse_principal_claims(encoded: str) -> dict[str, Any]:
    try:
        padded = encoded + "=" * (-len(encoded) % 4)
        raw = base64.b64decode(padded.encode("ascii"), validate=False)
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuthenticationError(
            "Missing or invalid Azure authentication identity.",
            safe_context="identity=azure_app_service reason=principal_parse",
        ) from exc
    if not isinstance(payload, dict):
        raise AuthenticationError(
            "Missing or invalid Azure authentication identity.",
            safe_context="identity=azure_app_service reason=principal_shape",
        )
    return cast(dict[str, Any], payload)


def _claim_value(payload: dict[str, Any], key: str) -> str | None:
    claims = payload.get("claims")
    if isinstance(claims, list):
        for item in cast(list[object], claims):
            if not isinstance(item, dict):
                continue
            claim = cast(dict[str, object], item)
            typ = claim.get("typ") or claim.get("type")
            if typ == key:
                val = claim.get("val") or claim.get("value")
                if isinstance(val, str) and val.strip():
                    return val.strip()
    direct = payload.get(key)
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    return None


def _first_claim(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _claim_value(payload, key)
        if value:
            return value
    return None


def _conflicting_claim_values(
    payload: dict[str, Any], keys: tuple[str, ...], expected: str
) -> bool:
    for key in keys:
        value = _claim_value(payload, key)
        if value is not None and value != expected:
            return True
    return False
