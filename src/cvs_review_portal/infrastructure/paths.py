"""Path containment helpers for local portal storage."""

from __future__ import annotations

from pathlib import Path

from cvs_review_portal.domain.errors import InvalidIdentifierError
from cvs_review_portal.domain.identifiers import validate_relative_storage_key


def resolve_under_root(root: Path, *relative_parts: str) -> Path:
    """Resolve a path under `root`, rejecting escape via `..` or symlinks."""
    root_resolved = root.resolve()
    candidate = root_resolved.joinpath(*relative_parts)
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise InvalidIdentifierError(
            "Resolved path escapes configured root.",
            safe_context="reason=path-escape",
        ) from exc
    return resolved


def resolve_relative_key(root: Path, relative_key: str) -> Path:
    """Resolve a validated relative storage key under `root`."""
    safe_key = validate_relative_storage_key(relative_key)
    parts = safe_key.split("/")
    return resolve_under_root(root, *parts)
