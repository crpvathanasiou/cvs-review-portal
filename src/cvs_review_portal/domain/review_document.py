"""Versioned review document contracts and legacy projection helpers.

Schema v1 ``ReviewRecord`` is the writable current-state format. Existing schema v2
envelopes remain readable (current comments and ground-truth overrides are projected);
the portal no longer appends audit history or operation receipts on Save.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, ValidationInfo, field_validator, model_validator

from cvs_review_portal.domain.constants import MAX_COMMENT_LENGTH, SCHEMA_V1, SCHEMA_V2
from cvs_review_portal.domain.identifiers import validate_identifier
from cvs_review_portal.domain.models import PortalModel, ReviewRecord
from cvs_review_portal.domain.types import (
    NonNegativeInt,
    OptionalBinaryLabel,
    PositiveInt,
    parse_nonnegative_int,
)

HistoryKind = Literal["imported_baseline", "comment_change", "legacy_record"]
SchemaV2 = Literal["2"]


class ReviewOperationReceipt(PortalModel):
    """Receipt for a committed Save, scoped to one image review document.

    ``expected_revision`` is required on all newly written receipts. Older v2
    documents may omit it; callers must use narrow history-based inference rather
    than fabricating a value or silently relaxing comparison for new receipts.
    """

    request_id: UUID
    actor: str
    comments: str
    committed_revision: PositiveInt
    committed_at: datetime
    expected_revision: NonNegativeInt | None = None

    @field_validator("comments")
    @classmethod
    def _comment_length(cls, value: str) -> str:
        if len(value) > MAX_COMMENT_LENGTH:
            raise ValueError("comments exceed maximum length")
        return value

    @field_validator("committed_at")
    @classmethod
    def _tz_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("committed_at must be timezone-aware")
        return value

    @field_validator("actor")
    @classmethod
    def _actor_nonempty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("actor must be non-empty")
        return value


class ReviewHistoryEntry(PortalModel):
    """One persisted history entry inside a schema-v2 review document."""

    kind: HistoryKind
    revision: PositiveInt
    comments: str | None = None
    actor: str
    updated_at: datetime
    ground_truth_override: OptionalBinaryLabel = None
    request_id: UUID | None = None

    @field_validator("updated_at")
    @classmethod
    def _tz_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("updated_at must be timezone-aware")
        return value

    @field_validator("actor")
    @classmethod
    def _actor_nonempty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("actor must be non-empty")
        return value

    @field_validator("comments")
    @classmethod
    def _comment_length(cls, value: str | None) -> str | None:
        if value is not None and len(value) > MAX_COMMENT_LENGTH:
            raise ValueError("comments exceed maximum length")
        return value


class ReviewCurrentState(PortalModel):
    """Authoritative current review fields inside a schema-v2 document."""

    comments: str | None = None
    ground_truth_override: OptionalBinaryLabel = None
    revision: PositiveInt
    actor: str
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def _tz_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("updated_at must be timezone-aware")
        return value

    @field_validator("actor")
    @classmethod
    def _actor_nonempty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("actor must be non-empty")
        return value

    @field_validator("comments")
    @classmethod
    def _comment_length(cls, value: str | None) -> str | None:
        if value is not None and len(value) > MAX_COMMENT_LENGTH:
            raise ValueError("comments exceed maximum length")
        return value


class ReviewDocumentV2(PortalModel):
    """Schema-v2 envelope: current state + history + operation receipts."""

    schema_version: SchemaV2
    dataset_id: str
    dataset_version: str
    image_id: str
    current: ReviewCurrentState
    history: list[ReviewHistoryEntry] = Field(default_factory=list[ReviewHistoryEntry])
    operations: list[ReviewOperationReceipt] = Field(default_factory=list[ReviewOperationReceipt])

    @field_validator("dataset_id", "dataset_version", "image_id")
    @classmethod
    def _ids(cls, value: str, info: ValidationInfo) -> str:
        return validate_identifier(value, field=str(info.field_name))

    @model_validator(mode="after")
    def _operations_unique(self) -> ReviewDocumentV2:
        seen: set[UUID] = set()
        for receipt in self.operations:
            if receipt.request_id in seen:
                raise ValueError("duplicate operation request_id in review document")
            seen.add(receipt.request_id)
        return self

    def find_operation(self, request_id: UUID) -> ReviewOperationReceipt | None:
        for receipt in self.operations:
            if receipt.request_id == request_id:
                return receipt
        return None

    def inferred_expected_revision(self, receipt: ReviewOperationReceipt) -> NonNegativeInt | None:
        """Infer expected_revision for a legacy receipt lacking the field.

        Returns a value only when history makes the base revision unambiguous:
        the matching comment_change entry exists and the prior head revision is
        exactly ``committed_revision - 1`` (or ``0`` for the first revision).
        """
        if receipt.expected_revision is not None:
            return parse_nonnegative_int(receipt.expected_revision)
        matching = [
            entry
            for entry in self.history
            if entry.request_id == receipt.request_id
            and entry.revision == receipt.committed_revision
            and entry.kind == "comment_change"
        ]
        if len(matching) != 1:
            return None
        if receipt.committed_revision == 1:
            priors = [entry.revision for entry in self.history if entry.revision < 1]
            if priors:
                return None
            return parse_nonnegative_int(0)
        priors = [
            entry.revision for entry in self.history if entry.revision < receipt.committed_revision
        ]
        if not priors:
            return None
        max_prior = max(priors)
        if max_prior != receipt.committed_revision - 1:
            return None
        return parse_nonnegative_int(max_prior)


class LoadedReview(PortalModel):
    """Normalized review projection used by application composition and Save."""

    schema_version: Literal["1", "2"]
    dataset_id: str
    dataset_version: str
    image_id: str
    comments: str | None
    ground_truth_override: OptionalBinaryLabel
    revision: PositiveInt
    actor: str
    updated_at: datetime
    document: ReviewDocumentV2 | None = None
    legacy_record: ReviewRecord | None = None

    @property
    def persisted_revision(self) -> int:
        return self.revision


def project_review_record(record: ReviewRecord) -> LoadedReview:
    """Project a schema-v1 record without rewriting storage."""
    return LoadedReview(
        schema_version=SCHEMA_V1,  # type: ignore[arg-type]
        dataset_id=record.dataset_id,
        dataset_version=record.dataset_version,
        image_id=record.image_id,
        comments=record.comments,
        ground_truth_override=record.ground_truth_override,
        revision=record.revision,
        actor=record.actor,
        updated_at=record.updated_at,
        document=None,
        legacy_record=record,
    )


def project_review_document(document: ReviewDocumentV2) -> LoadedReview:
    """Project a schema-v2 document's current state."""
    return LoadedReview(
        schema_version=SCHEMA_V2,  # type: ignore[arg-type]
        dataset_id=document.dataset_id,
        dataset_version=document.dataset_version,
        image_id=document.image_id,
        comments=document.current.comments,
        ground_truth_override=document.current.ground_truth_override,
        revision=document.current.revision,
        actor=document.current.actor,
        updated_at=document.current.updated_at,
        document=document,
        legacy_record=None,
    )


def expected_revision_or_zero(loaded: LoadedReview | None) -> NonNegativeInt:
    """Revision 0 means no persisted review exists."""
    if loaded is None:
        return parse_nonnegative_int(0)
    return parse_nonnegative_int(loaded.revision)
