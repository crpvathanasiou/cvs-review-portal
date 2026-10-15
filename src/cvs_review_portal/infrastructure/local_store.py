"""Local filesystem implementation of the portal data store."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import TypeVar, cast

from filelock import FileLock, Timeout
from pydantic import BaseModel, ValidationError

from cvs_review_portal.application.ports import (
    ReviewMutationResult,
    ReviewMutator,
    ReviewWriteCommit,
)
from cvs_review_portal.application.video_catalog import parse_videos_csv, videos_csv_storage_key
from cvs_review_portal.domain.constants import MAX_REVIEW_DOCUMENT_BYTES
from cvs_review_portal.domain.errors import (
    DataStoreUnavailableError,
    InvalidArtifactError,
    ResourceNotFoundError,
    ReviewDocumentTooLargeError,
    StorageConflictError,
)
from cvs_review_portal.domain.identifiers import validate_identifier
from cvs_review_portal.domain.models import (
    Catalog,
    DatasetVersion,
    EvaluationSnapshot,
    MetricsArtifact,
    PredictionsArtifact,
    RunManifest,
    VideoArtifact,
    VideoCatalog,
)
from cvs_review_portal.domain.review_document import LoadedReview
from cvs_review_portal.infrastructure.paths import resolve_relative_key, resolve_under_root
from cvs_review_portal.infrastructure.review_codec import (
    parse_review_payload,
    serialize_review_record,
)
from cvs_review_portal.infrastructure.video_cache import VideoArtifactCache
from cvs_review_portal.settings import DatasetLayout

logger = logging.getLogger("cvs_review_portal.infrastructure.local_store")

T = TypeVar("T", bound=BaseModel)

_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

# Cross-process lock timeout for a single review mutation (seconds).
_REVIEW_LOCK_TIMEOUT_SECONDS = 30.0


class LocalPortalDataStore:
    """Read/write published portal artifacts under a configured local data root."""

    def __init__(
        self,
        data_root: Path,
        *,
        dataset_layout: DatasetLayout = "legacy",
    ) -> None:
        self._data_root = data_root
        self._dataset_layout: DatasetLayout = dataset_layout
        self._runs_output = data_root / "runs-output"
        self._raw_images = data_root / "raw-images"
        self._reviews = data_root / "reviews"
        self._video_cache = VideoArtifactCache()

    @property
    def dataset_layout(self) -> DatasetLayout:
        return self._dataset_layout

    def ensure_available(self) -> None:
        """Raise when the data root or catalog cannot be used for reads."""
        if not self._data_root.exists() or not self._data_root.is_dir():
            raise DataStoreUnavailableError(
                "Configured data root is missing or not a directory.",
                safe_context="data_root=unavailable",
            )
        catalog_path = self._runs_output / "catalog.json"
        if not catalog_path.is_file():
            raise DataStoreUnavailableError(
                "Portal catalog is missing under the configured data root.",
                safe_context="artifact=catalog",
            )

    def load_catalog(self) -> Catalog:
        self.ensure_available()
        path = resolve_under_root(self._runs_output, "catalog.json")
        return self._load_json_model(path, Catalog, artifact="catalog")

    def load_dataset(self, dataset_id: str, dataset_version: str) -> DatasetVersion:
        self.ensure_available()
        if self._dataset_layout == "video_catalog":
            raise InvalidArtifactError(
                "Legacy dataset.json is not used when DATASET_LAYOUT=video_catalog.",
                safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
            )
        dataset_id = validate_identifier(dataset_id, field="dataset_id")
        dataset_version = validate_identifier(dataset_version, field="dataset_version")
        path = resolve_under_root(
            self._runs_output,
            "datasets",
            dataset_id,
            dataset_version,
            "dataset.json",
        )
        if not path.is_file():
            raise ResourceNotFoundError(
                "Dataset version not found.",
                safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
            )
        dataset = self._load_dataset_json(path)
        if dataset.dataset_id != dataset_id or dataset.dataset_version != dataset_version:
            raise InvalidArtifactError(
                "Dataset identity does not match storage location.",
                safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
            )
        return dataset

    def load_video_catalog(self, dataset_id: str, dataset_version: str) -> VideoCatalog:
        self.ensure_available()
        if self._dataset_layout != "video_catalog":
            raise InvalidArtifactError(
                "Video catalog is only available when DATASET_LAYOUT=video_catalog.",
                safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
            )
        dataset_id = validate_identifier(dataset_id, field="dataset_id")
        dataset_version = validate_identifier(dataset_version, field="dataset_version")
        key = videos_csv_storage_key(dataset_id, dataset_version)
        path = resolve_relative_key(self._data_root, key)
        if not path.is_file():
            raise InvalidArtifactError(
                "videos.csv is missing for a published dataset version.",
                safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
            )
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            logger.exception("invalid_artifact artifact=videos_csv")
            raise InvalidArtifactError(
                "videos.csv could not be read.",
                safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
            ) from exc
        return parse_videos_csv(text, dataset_id=dataset_id, dataset_version=dataset_version)

    def load_video(self, dataset_id: str, dataset_version: str, video_id: str) -> VideoArtifact:
        self.ensure_available()
        if self._dataset_layout != "video_catalog":
            raise InvalidArtifactError(
                "Per-video metadata is only available when DATASET_LAYOUT=video_catalog.",
                safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
            )
        dataset_id = validate_identifier(dataset_id, field="dataset_id")
        dataset_version = validate_identifier(dataset_version, field="dataset_version")
        video_id = validate_identifier(video_id, field="video_id")
        catalog = self.load_video_catalog(dataset_id, dataset_version)
        entry = catalog.get_entry(video_id)
        if entry is None:
            raise ResourceNotFoundError(
                "Video is not in the active videos.csv catalog.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"video_id={video_id}"
                ),
            )
        path = resolve_relative_key(self._data_root, entry.metadata_path)
        if not path.is_file():
            raise InvalidArtifactError(
                "Active video metadata JSON is missing.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"video_id={video_id}"
                ),
            )
        try:
            fingerprint = f"{path.stat().st_mtime_ns}:{path.stat().st_size}"
        except OSError as exc:
            raise InvalidArtifactError(
                "Active video metadata JSON is unreadable.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"video_id={video_id}"
                ),
            ) from exc
        cached = self._video_cache.get(
            dataset_id, dataset_version, video_id, fingerprint=fingerprint
        )
        if cached is not None:
            return cached
        artifact = self._load_video_json(path)
        if (
            artifact.dataset_id != dataset_id
            or artifact.dataset_version != dataset_version
            or artifact.video_id != video_id
        ):
            raise InvalidArtifactError(
                "Video artifact identity does not match the catalog entry.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"video_id={video_id}"
                ),
            )
        if artifact.video_name != entry.video_name:
            raise InvalidArtifactError(
                "Video artifact video_name does not match videos.csv.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"video_id={video_id}"
                ),
            )
        self._video_cache.put(
            dataset_id,
            dataset_version,
            video_id,
            fingerprint=fingerprint,
            artifact=artifact,
        )
        return artifact

    def load_run(self, run_id: str) -> RunManifest:
        self.ensure_available()
        run_id = validate_identifier(run_id, field="run_id")
        path = resolve_under_root(self._runs_output, "runs", run_id, "run.json")
        if not path.is_file():
            raise ResourceNotFoundError(
                "Run not found.",
                safe_context=f"run_id={run_id}",
            )
        run = self._load_json_model(path, RunManifest, artifact="run")
        if run.run_id != run_id:
            raise InvalidArtifactError(
                "Run identity does not match storage location.",
                safe_context=f"run_id={run_id}",
            )
        return run

    def load_predictions(self, run: RunManifest) -> PredictionsArtifact:
        path = resolve_relative_key(
            resolve_under_root(self._runs_output, "runs", run.run_id),
            run.predictions_artifact,
        )
        if not path.is_file():
            raise InvalidArtifactError(
                "Predictions artifact is missing for run.",
                safe_context=f"run_id={run.run_id}",
            )
        return self._load_json_model(path, PredictionsArtifact, artifact="predictions")

    def load_metrics(self, run: RunManifest) -> MetricsArtifact | None:
        if run.metrics_artifact is None:
            return None
        path = resolve_relative_key(
            resolve_under_root(self._runs_output, "runs", run.run_id),
            run.metrics_artifact,
        )
        if not path.is_file():
            raise InvalidArtifactError(
                "Metrics artifact is declared but missing.",
                safe_context=f"run_id={run.run_id}",
            )
        return self._load_json_model(path, MetricsArtifact, artifact="metrics")

    def load_evaluation_snapshot(self, run: RunManifest) -> EvaluationSnapshot | None:
        if run.evaluation_snapshot_artifact is None:
            return None
        path = resolve_relative_key(
            resolve_under_root(self._runs_output, "runs", run.run_id),
            run.evaluation_snapshot_artifact,
        )
        if not path.is_file():
            raise InvalidArtifactError(
                "Evaluation snapshot artifact is declared but missing.",
                safe_context=f"run_id={run.run_id}",
            )
        return self._load_json_model(path, EvaluationSnapshot, artifact="evaluation_snapshot")

    def load_review(
        self, dataset_id: str, dataset_version: str, image_id: str
    ) -> LoadedReview | None:
        dataset_id = validate_identifier(dataset_id, field="dataset_id")
        dataset_version = validate_identifier(dataset_version, field="dataset_version")
        image_id = validate_identifier(image_id, field="image_id")
        path = resolve_under_root(self._reviews, dataset_id, dataset_version, f"{image_id}.json")
        if not path.is_file():
            return None
        return self._load_review_file(path, dataset_id, dataset_version, image_id)

    def mutate_review(
        self,
        dataset_id: str,
        dataset_version: str,
        image_id: str,
        mutator: ReviewMutator,
    ) -> ReviewMutationResult:
        """Serialize the complete read/check/write transaction across processes.

        Uses a cross-process file lock (not merely a threading lock), writes to a
        temporary file, then atomically replaces the review file. Supports Windows.
        """
        dataset_id = validate_identifier(dataset_id, field="dataset_id")
        dataset_version = validate_identifier(dataset_version, field="dataset_version")
        image_id = validate_identifier(image_id, field="image_id")
        review_dir = resolve_under_root(self._reviews, dataset_id, dataset_version)
        review_dir.mkdir(parents=True, exist_ok=True)
        path = resolve_under_root(self._reviews, dataset_id, dataset_version, f"{image_id}.json")
        lock_path = resolve_under_root(
            self._reviews, dataset_id, dataset_version, f"{image_id}.json.lock"
        )
        lock = FileLock(str(lock_path), timeout=_REVIEW_LOCK_TIMEOUT_SECONDS)
        try:
            with lock:
                before = (
                    self._load_review_file(path, dataset_id, dataset_version, image_id)
                    if path.is_file()
                    else None
                )
                decision = mutator(before)
                assert isinstance(decision, ReviewWriteCommit)
                payload = serialize_review_record(decision.record)
                if len(payload) > MAX_REVIEW_DOCUMENT_BYTES:
                    raise ReviewDocumentTooLargeError(
                        "Review document would exceed the supported per-image size limit.",
                        safe_context=f"limit_bytes={MAX_REVIEW_DOCUMENT_BYTES}",
                    )
                self._atomic_write_bytes(path, payload)
                after = self._load_review_file(path, dataset_id, dataset_version, image_id)
                return ReviewMutationResult(
                    loaded_before=before,
                    loaded_after=after,
                    wrote=True,
                    committed_record=decision.record,
                )
        except Timeout as exc:
            raise StorageConflictError(
                "Could not acquire review write lock.",
                safe_context="conflict=lock_timeout",
            ) from exc

    def close(self) -> None:
        return None

    def read_raw_image_bytes(
        self, dataset_id: str, dataset_version: str, raw_image_key: str
    ) -> tuple[bytes, str]:
        dataset_id = validate_identifier(dataset_id, field="dataset_id")
        dataset_version = validate_identifier(dataset_version, field="dataset_version")
        image_root = resolve_under_root(self._raw_images, dataset_id, dataset_version)
        path = resolve_relative_key(image_root, raw_image_key)
        if not path.is_file():
            raise ResourceNotFoundError(
                "Raw image not found.",
                safe_context=(f"dataset_id={dataset_id} dataset_version={dataset_version}"),
            )
        try:
            content = path.read_bytes()
        except OSError as exc:
            logger.exception(
                "failed_reading_image dataset_id=%s dataset_version=%s",
                dataset_id,
                dataset_version,
            )
            raise InvalidArtifactError(
                "Raw image could not be read.",
                safe_context=(f"dataset_id={dataset_id} dataset_version={dataset_version}"),
            ) from exc
        media_type = _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")
        return content, media_type

    def _load_dataset_json(self, path: Path) -> DatasetVersion:
        """Load a dataset artifact, ignoring only the retired editability field."""
        try:
            raw_text = path.read_text(encoding="utf-8")
            payload = json.loads(raw_text)
            payload = _strip_retired_ground_truth_editable(payload)
            return DatasetVersion.model_validate(payload)
        except FileNotFoundError as exc:
            raise ResourceNotFoundError(
                "dataset not found.",
                safe_context="artifact=dataset",
            ) from exc
        except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as exc:
            logger.exception("invalid_artifact artifact=dataset")
            raise InvalidArtifactError(
                "Invalid dataset artifact.",
                safe_context="artifact=dataset",
            ) from exc

    def _load_video_json(self, path: Path) -> VideoArtifact:
        try:
            raw_text = path.read_text(encoding="utf-8")
            payload = json.loads(raw_text)
            payload = _strip_retired_ground_truth_editable(payload)
            return VideoArtifact.model_validate(payload)
        except FileNotFoundError as exc:
            raise ResourceNotFoundError(
                "video metadata not found.",
                safe_context="artifact=video",
            ) from exc
        except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as exc:
            logger.exception("invalid_artifact artifact=video")
            raise InvalidArtifactError(
                "Invalid video metadata artifact.",
                safe_context="artifact=video",
            ) from exc

    def _load_json_model(self, path: Path, model_type: type[T], *, artifact: str) -> T:
        try:
            raw_text = path.read_text(encoding="utf-8")
            payload = json.loads(raw_text)
            return model_type.model_validate(payload)
        except FileNotFoundError as exc:
            raise ResourceNotFoundError(
                f"{artifact} not found.",
                safe_context=f"artifact={artifact}",
            ) from exc
        except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as exc:
            logger.exception("invalid_artifact artifact=%s", artifact)
            raise InvalidArtifactError(
                f"Invalid {artifact} artifact.",
                safe_context=f"artifact={artifact}",
            ) from exc

    def _load_review_file(
        self,
        path: Path,
        dataset_id: str,
        dataset_version: str,
        image_id: str,
    ) -> LoadedReview:
        try:
            raw_text = path.read_text(encoding="utf-8")
            payload = json.loads(raw_text)
            review = parse_review_payload(payload, artifact="review")
        except FileNotFoundError as exc:
            raise ResourceNotFoundError(
                "review not found.",
                safe_context="artifact=review",
            ) from exc
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            logger.exception("invalid_artifact artifact=review")
            raise InvalidArtifactError(
                "Invalid review artifact.",
                safe_context="artifact=review",
            ) from exc
        if (
            review.dataset_id != dataset_id
            or review.dataset_version != dataset_version
            or review.image_id != image_id
        ):
            raise InvalidArtifactError(
                "Review identity does not match storage location.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"image_id={image_id}"
                ),
            )
        return review

    def _atomic_write_bytes(self, path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, path)
        except OSError as exc:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                logger.exception("failed_removing_review_temp")
            logger.exception("failed_writing_review")
            raise InvalidArtifactError(
                "Review could not be written.",
                safe_context="artifact=review",
            ) from exc


def _as_str_object_map(value: object) -> dict[str, object] | None:
    """Convert a JSON object to ``dict[str, object]`` for strict typing."""
    if not isinstance(value, dict):
        return None
    untyped = cast(dict[object, object], value)
    typed: dict[str, object] = {}
    for key, item in untyped.items():
        typed[str(key)] = item
    return typed


def _strip_retired_ground_truth_editable(payload: object) -> object:
    """Drop legacy ``ground_truth_editable`` from dataset images only.

    Other unknown or invalid fields remain subject to normal schema validation.
    The stripped field is never returned through active models or API views.
    """
    raw_payload = _as_str_object_map(payload)
    if raw_payload is None:
        return payload

    images_obj = raw_payload.get("images")
    if not isinstance(images_obj, list):
        return raw_payload

    cleaned_images: list[object] = []
    changed = False
    for image_obj in cast(list[object], images_obj):
        image_map = _as_str_object_map(image_obj)
        if image_map is not None and "ground_truth_editable" in image_map:
            cleaned = {
                key: value for key, value in image_map.items() if key != "ground_truth_editable"
            }
            cleaned_images.append(cleaned)
            changed = True
        else:
            cleaned_images.append(image_obj)
    if not changed:
        return raw_payload
    return {**raw_payload, "images": cleaned_images}
