"""Identifier and relative-key validation invariants."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from cvs_review_portal.domain.errors import InvalidIdentifierError

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def validate_identifier(name: str, *, field: str) -> str:
    """Return a safe portal identifier or raise `InvalidIdentifierError`."""
    if not name or not _IDENTIFIER_PATTERN.fullmatch(name):
        raise InvalidIdentifierError(
            f"Invalid {field}.",
            safe_context=f"field={field}",
        )
    return name


def validate_relative_storage_key(key: str, *, field: str = "raw_image_key") -> str:
    """Validate a relative storage key that must stay under a configured root."""
    if not key or key != key.strip():
        raise InvalidIdentifierError(
            f"Invalid {field}.",
            safe_context=f"field={field}",
        )
    if Path(key).is_absolute() or PurePosixPath(key).is_absolute():
        raise InvalidIdentifierError(
            f"Invalid {field}.",
            safe_context=f"field={field} reason=absolute",
        )
    parts = PurePosixPath(key.replace("\\", "/")).parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise InvalidIdentifierError(
            f"Invalid {field}.",
            safe_context=f"field={field} reason=path-parts",
        )
    for part in parts[:-1]:
        validate_identifier(part, field=field)
    # Final segment may include an extension; validate stem-like safety.
    final = parts[-1]
    if final.startswith(".") or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", final):
        raise InvalidIdentifierError(
            f"Invalid {field}.",
            safe_context=f"field={field} reason=final-segment",
        )
    return "/".join(parts)
