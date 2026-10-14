"""Comments-only Save: latest comment + revision concurrency (no audit history)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from cvs_review_portal.application.ports import (
    PortalDataStore,
    ReviewMutationResult,
    ReviewWriteCommit,
)
from cvs_review_portal.domain.constants import (
    MAX_COMMENT_LENGTH,
    MAX_REVIEW_DOCUMENT_BYTES,
    SCHEMA_V1,
)
from cvs_review_portal.domain.errors import (
    InvalidArtifactError,
    ResourceNotFoundError,
    ReviewConflictError,
    ReviewDocumentTooLargeError,
    ReviewMutationRejectedError,
    StorageConflictError,
)
from cvs_review_portal.domain.identifiers import validate_identifier
from cvs_review_portal.domain.models import DatasetVersion, ReviewRecord
from cvs_review_portal.domain.review_document import (
    LoadedReview,
    expected_revision_or_zero,
    project_review_record,
)
from cvs_review_portal.domain.types import parse_nonnegative_int
from cvs_review_portal.infrastructure.review_codec import serialize_review_record


@dataclass(frozen=True, slots=True)
class SaveCommentsResult:
    """Outcome of a comments-only Save — the persisted current review state."""

    current: LoadedReview


class PortalReviewService:
    """Validate targets and persist comments-only review mutations."""

    def __init__(self, store: PortalDataStore) -> None:
        self._store = store

    def get_review(
        self, dataset_id: str, dataset_version: str, image_id: str
    ) -> LoadedReview | None:
        dataset = self._require_image(dataset_id, dataset_version, image_id)
        return self._store.load_review(dataset.dataset_id, dataset.dataset_version, image_id)

    def save_comments(
        self,
        *,
        dataset_id: str,
        dataset_version: str,
        image_id: str,
        comments: str,
        expected_revision: int,
        actor: str,
    ) -> SaveCommentsResult:
        if len(comments) > MAX_COMMENT_LENGTH:
            raise ReviewMutationRejectedError(
                f"comments exceed maximum length of {MAX_COMMENT_LENGTH} characters.",
                safe_context="field=comments reason=too-long",
            )
        expected = parse_nonnegative_int(expected_revision)
        if not actor or not actor.strip():
            raise ReviewMutationRejectedError(
                "actor is required.",
                safe_context="field=actor",
            )

        dataset = self._require_image(dataset_id, dataset_version, image_id)
        now = datetime.now(UTC)

        def mutator(current: LoadedReview | None) -> ReviewWriteCommit:
            return self._decide_write(
                current=current,
                dataset_id=dataset.dataset_id,
                dataset_version=dataset.dataset_version,
                image_id=image_id,
                comments=comments,
                expected_revision=expected,
                actor=actor,
                now=now,
            )

        try:
            result = self._store.mutate_review(
                dataset.dataset_id,
                dataset.dataset_version,
                image_id,
                mutator,
            )
        except StorageConflictError as exc:
            raise ReviewConflictError(
                "Concurrent review write conflict.",
                safe_context=exc.safe_context or "conflict=storage_precondition",
                conflict_kind="storage",
            ) from exc
        return self._to_save_result(result)

    def _decide_write(
        self,
        *,
        current: LoadedReview | None,
        dataset_id: str,
        dataset_version: str,
        image_id: str,
        comments: str,
        expected_revision: int,
        actor: str,
        now: datetime,
    ) -> ReviewWriteCommit:
        actual_revision = expected_revision_or_zero(current)
        if actual_revision != expected_revision:
            raise ReviewConflictError(
                "expected_revision does not match the current review revision.",
                safe_context=(
                    f"expected_revision={expected_revision} actual_revision={actual_revision}"
                ),
                conflict_kind="revision",
            )

        preserved_override = None if current is None else current.ground_truth_override
        new_revision = 1 if current is None else current.revision + 1
        record = ReviewRecord(
            schema_version=SCHEMA_V1,  # type: ignore[arg-type]
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            image_id=image_id,
            ground_truth_override=preserved_override,
            comments=comments,
            revision=new_revision,
            actor=actor,
            updated_at=now,
        )
        self._ensure_record_size(record)
        return ReviewWriteCommit(record=record)

    def _to_save_result(self, result: ReviewMutationResult) -> SaveCommentsResult:
        committed = result.committed_record
        assert committed is not None
        # Prefer post-write read when available; otherwise project the committed record.
        if result.loaded_after is not None:
            current = result.loaded_after
        else:
            current = project_review_record(committed)
        return SaveCommentsResult(current=current)

    def _ensure_record_size(self, record: ReviewRecord) -> None:
        payload = serialize_review_record(record)
        if len(payload) > MAX_REVIEW_DOCUMENT_BYTES:
            raise ReviewDocumentTooLargeError(
                "Review document would exceed the supported per-image size limit.",
                safe_context=f"limit_bytes={MAX_REVIEW_DOCUMENT_BYTES}",
            )

    def _require_image(
        self, dataset_id: str, dataset_version: str, image_id: str
    ) -> DatasetVersion:
        dataset_id = validate_identifier(dataset_id, field="dataset_id")
        dataset_version = validate_identifier(dataset_version, field="dataset_version")
        image_id = validate_identifier(image_id, field="image_id")
        catalog = self._store.load_catalog()
        if not catalog.has_dataset(dataset_id, dataset_version):
            raise ResourceNotFoundError(
                "Dataset version not found.",
                safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
            )
        try:
            dataset = self._store.load_dataset(dataset_id, dataset_version)
        except ResourceNotFoundError as exc:
            raise InvalidArtifactError(
                "Catalog references a dataset version that is missing or unreadable.",
                safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
            ) from exc
        if dataset.dataset_id != dataset_id or dataset.dataset_version != dataset_version:
            raise InvalidArtifactError(
                "Dataset artifact identity does not match the catalog reference.",
                safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
            )
        if not any(image.image_id == image_id for image in dataset.images):
            raise ResourceNotFoundError(
                "Image not found in dataset version.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"image_id={image_id}"
                ),
            )
        return dataset
