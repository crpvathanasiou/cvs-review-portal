"""HTTP cache helpers for the raw image-content endpoint.

Browser caching only: successful image responses may be stored privately for one
hour. ETags are strong SHA-256 digests of the response body. Mutable JSON
endpoints must not reuse these helpers.
"""

from __future__ import annotations

import hashlib

from starlette.responses import Response

IMAGE_CACHE_CONTROL = "private, max-age=3600"
IMAGE_ERROR_CACHE_CONTROL = "no-store"
_IMAGE_VARY_TOKENS = ("Cookie", "Authorization")


def strong_etag_for_bytes(content: bytes) -> str:
    """Return a quoted strong ETag for the given response body bytes."""
    digest = hashlib.sha256(content).hexdigest()
    return f'"{digest}"'


def merge_vary(existing: str | None, *required: str) -> str:
    """Merge Vary tokens, preserving existing values and appending required ones."""
    tokens: list[str] = []
    seen: set[str] = set()

    def add(token: str) -> None:
        key = token.casefold()
        if key in seen:
            return
        seen.add(key)
        tokens.append(token)

    if existing:
        for part in existing.split(","):
            cleaned = part.strip()
            if cleaned:
                add(cleaned)
    for token in required:
        add(token)
    return ", ".join(tokens)


def _opaque_tag(entity_tag: str) -> str | None:
    """Extract the opaque-tag value for weak comparison, or None if malformed."""
    value = entity_tag.strip()
    if len(value) >= 2 and value[:2].upper() == "W/":
        value = value[2:].lstrip()
    if len(value) < 2 or value[0] != '"' or value[-1] != '"':
        return None
    return value[1:-1]


def if_none_match_satisfied(header_value: str | None, current_etag: str) -> bool:
    """Return True when If-None-Match matches under standard GET weak comparison.

    Supports ``*``, quoted strong tags, weak tags (``W/"..."``), and comma-separated
    lists. Malformed input never raises — it is treated as a non-match.
    """
    if header_value is None:
        return False
    try:
        raw = header_value.strip()
        if not raw:
            return False
        if raw == "*":
            return True
        current_opaque = _opaque_tag(current_etag)
        if current_opaque is None:
            return False
        for part in raw.split(","):
            candidate = part.strip()
            if not candidate or candidate == "*":
                # Bare * must be the whole field value; mixed forms are ignored.
                continue
            opaque = _opaque_tag(candidate)
            if opaque is not None and opaque == current_opaque:
                return True
        return False
    except Exception:
        return False


def apply_successful_image_cache_headers(response: Response, *, etag: str) -> None:
    """Attach private cache policy, ETag, and Vary for a successful image response."""
    response.headers["Cache-Control"] = IMAGE_CACHE_CONTROL
    response.headers["ETag"] = etag
    response.headers["Vary"] = merge_vary(response.headers.get("Vary"), *_IMAGE_VARY_TOKENS)


def image_error_headers() -> dict[str, str]:
    """Headers for image-content error responses (never cacheable)."""
    return {"Cache-Control": IMAGE_ERROR_CACHE_CONTROL}


def is_image_content_path(path: str) -> bool:
    """True for the protected raw-image content route."""
    return path.startswith("/api/datasets/") and "/images/" in path and path.endswith("/content")
