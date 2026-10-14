"""Explicit request/response models for comments-only review APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cvs_review_portal.domain.constants import MAX_COMMENT_LENGTH
from cvs_review_portal.domain.models import BinaryLabel
from cvs_review_portal.domain.types import NonNegativeInt, parse_nonnegative_int


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SaveCommentsRequest(ApiModel):
    """Comments-only Save payload.

    Unsupported fields (ground truth, editability, actor, timestamps, etc.) are
    rejected via ``extra='forbid'`` rather than silently ignored.
    """

    comments: str
    expected_revision: NonNegativeInt

    @field_validator("comments")
    @classmethod
    def _comment_length(cls, value: str) -> str:
        if len(value) > MAX_COMMENT_LENGTH:
            raise ValueError(f"comments must be at most {MAX_COMMENT_LENGTH} characters")
        return value

    @field_validator("expected_revision", mode="before")
    @classmethod
    def _revision(cls, value: object) -> int:
        return parse_nonnegative_int(value)


class ReviewStateResponse(ApiModel):
    ground_truth_override: BinaryLabel | None
    comments: str | None
    revision: int
    actor: str
    updated_at: datetime


class GetReviewResponse(ApiModel):
    dataset_id: str
    dataset_version: str
    image_id: str
    persisted_revision: int
    review: ReviewStateResponse | None


class SaveCommentsResponse(ApiModel):
    """Save outcome — the persisted current review state after a successful write."""

    current: ReviewStateResponse
    persisted_revision: int = Field(ge=1)
