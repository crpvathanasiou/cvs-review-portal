"""Shared portal constants for review persistence and validation."""

from __future__ import annotations

# Maximum length of a comments string accepted by Save (backend and UI).
# Intentional empty string is allowed; oversize requests are rejected (never truncated).
MAX_COMMENT_LENGTH = 8000

# Practical upper bound for one per-image review document (UTF-8 JSON bytes).
# History is never truncated silently; writes that would exceed this fail explicitly.
MAX_REVIEW_DOCUMENT_BYTES = 512_000

# Schema version literals.
SCHEMA_V1 = "1"
SCHEMA_V2 = "2"
