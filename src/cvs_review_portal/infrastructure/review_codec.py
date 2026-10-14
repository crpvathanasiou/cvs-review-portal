"""Serialize and parse versioned review documents without rewriting legacy files."""

from __future__ import annotations

import json
from typing import Any, cast

from pydantic import ValidationError

from cvs_review_portal.domain.constants import SCHEMA_V1, SCHEMA_V2
from cvs_review_portal.domain.errors import InvalidArtifactError
from cvs_review_portal.domain.models import ReviewRecord
from cvs_review_portal.domain.review_document import (
    LoadedReview,
    ReviewDocumentV2,
    project_review_document,
    project_review_record,
)


def parse_review_payload(payload: object, *, artifact: str = "review") -> LoadedReview:
    """Parse schema v1 or v2 review JSON into a normalized LoadedReview."""
    if not isinstance(payload, dict):
        raise InvalidArtifactError(
            "Invalid review artifact.",
            safe_context=f"artifact={artifact}",
        )
    raw = cast(dict[str, Any], payload)
    schema = raw.get("schema_version")
    try:
        if schema == SCHEMA_V1:
            record = ReviewRecord.model_validate(raw)
            return project_review_record(record)
        if schema == SCHEMA_V2:
            document = ReviewDocumentV2.model_validate(raw)
            return project_review_document(document)
    except ValidationError as exc:
        raise InvalidArtifactError(
            "Invalid review artifact.",
            safe_context=f"artifact={artifact}",
        ) from exc
    raise InvalidArtifactError(
        "Unsupported review schema_version.",
        safe_context=f"artifact={artifact}",
    )


def serialize_review_document(document: ReviewDocumentV2) -> bytes:
    """Serialize a schema-v2 document to UTF-8 JSON bytes (read-compat / tests)."""
    payload = document.model_dump(mode="json")
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    return text.encode("utf-8")


def serialize_review_record(record: ReviewRecord) -> bytes:
    """Serialize a schema-v1 current-state review record for persistence."""
    payload = record.model_dump(mode="json")
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    return text.encode("utf-8")
