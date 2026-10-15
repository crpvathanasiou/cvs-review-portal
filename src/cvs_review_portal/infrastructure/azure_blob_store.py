"""Azure Blob Storage adapter for portal artifacts and atomic review writes.

Uses one private container with prefixes ``raw-images/``, ``runs-output/``, and
``reviews/`` (same logical layout as the local adapter). Credentials come from
Azure Identity (managed identity intended for deployment). Missing configuration
fails closed — there is no fallback to local data.

SDK clients are created lazily (never at import time) and closed via ``close()``.
"""

from __future__ import annotations

import json
import logging
from typing import TypeVar, cast

from azure.core import MatchConditions
from azure.core.exceptions import AzureError, ClientAuthenticationError, ResourceExistsError
from azure.core.exceptions import ResourceNotFoundError as AzureResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient, BlobServiceClient, ContentSettings
from pydantic import BaseModel, ValidationError

from cvs_review_portal.application.ports import (
    ReviewMutationResult,
    ReviewMutator,
    ReviewWriteCommit,
)
from cvs_review_portal.application.video_catalog import parse_videos_csv, videos_csv_storage_key
from cvs_review_portal.domain.constants import MAX_REVIEW_DOCUMENT_BYTES
from cvs_review_portal.domain.errors import (
    ConfigurationError,
    DataStoreUnavailableError,
    InvalidArtifactError,
    ResourceNotFoundError,
    ReviewDocumentTooLargeError,
    StorageConflictError,
)
from cvs_review_portal.domain.identifiers import validate_identifier, validate_relative_storage_key
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
from cvs_review_portal.infrastructure.review_codec import (
    parse_review_payload,
    serialize_review_record,
)
from cvs_review_portal.infrastructure.video_cache import VideoArtifactCache
from cvs_review_portal.settings import DatasetLayout

logger = logging.getLogger("cvs_review_portal.infrastructure.azure_blob_store")

T = TypeVar("T", bound=BaseModel)

_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


class AzureBlobPortalDataStore:
    """Blob-backed portal store with ETag conditional review create/update."""

    def __init__(
        self,
        *,
        account_url: str,
        container_name: str,
        credential: object | None = None,
        dataset_layout: DatasetLayout = "legacy",
    ) -> None:
        if not account_url or not account_url.strip():
            raise ConfigurationError(
                "Azure Blob account URL is required.",
                safe_context="config=azure_storage_account_url",
            )
        if not container_name or not container_name.strip():
            raise ConfigurationError(
                "Azure Blob container name is required.",
                safe_context="config=azure_blob_container",
            )
        self._account_url = account_url.rstrip("/")
        self._container_name = container_name
        self._dataset_layout: DatasetLayout = dataset_layout
        self._injected_credential = credential
        self._owned_credential: DefaultAzureCredential | None = None
        self._service_client: BlobServiceClient | None = None
        self._video_cache = VideoArtifactCache()

    @property
    def dataset_layout(self) -> DatasetLayout:
        return self._dataset_layout

    def close(self) -> None:
        client = self._service_client
        self._service_client = None
        if client is not None:
            client.close()
        owned = self._owned_credential
        self._owned_credential = None
        if owned is not None:
            owned.close()

    def _service(self) -> BlobServiceClient:
        if self._service_client is None:
            if self._injected_credential is not None:
                credential = self._injected_credential
            else:
                self._owned_credential = DefaultAzureCredential()
                credential = self._owned_credential
            self._service_client = BlobServiceClient(
                account_url=self._account_url,
                credential=credential,  # type: ignore[arg-type]
            )
        return self._service_client

    def _blob(self, key: str) -> BlobClient:
        safe_key = validate_relative_storage_key(key, field="blob_key")
        return self._service().get_blob_client(container=self._container_name, blob=safe_key)

    def ensure_available(self) -> None:
        try:
            blob = self._blob("runs-output/catalog.json")
            if not blob.exists():
                raise DataStoreUnavailableError(
                    "Portal catalog is missing under the configured Azure container.",
                    safe_context="artifact=catalog",
                )
        except (ClientAuthenticationError, AzureError) as exc:
            logger.exception("azure_store_unavailable")
            raise DataStoreUnavailableError(
                "Azure Blob Storage is unavailable or credentials are invalid.",
                safe_context="storage=azure_blob",
            ) from exc

    def load_catalog(self) -> Catalog:
        self.ensure_available()
        return self._load_json_model("runs-output/catalog.json", Catalog, artifact="catalog")

    def load_dataset(self, dataset_id: str, dataset_version: str) -> DatasetVersion:
        self.ensure_available()
        if self._dataset_layout == "video_catalog":
            raise InvalidArtifactError(
                "Legacy dataset.json is not used when DATASET_LAYOUT=video_catalog.",
                safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
            )
        dataset_id = validate_identifier(dataset_id, field="dataset_id")
        dataset_version = validate_identifier(dataset_version, field="dataset_version")
        key = f"runs-output/datasets/{dataset_id}/{dataset_version}/dataset.json"
        dataset = self._load_dataset_json(key)
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
        try:
            raw = self._download_bytes(key)
        except ResourceNotFoundError as exc:
            raise InvalidArtifactError(
                "videos.csv is missing for a published dataset version.",
                safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
            ) from exc
        try:
            text = raw.decode("utf-8")
        except UnicodeError as exc:
            raise InvalidArtifactError(
                "videos.csv could not be decoded as UTF-8.",
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
        blob = self._blob(entry.metadata_path)
        # Check metadata freshness (ETag/size) before downloading the JSON body.
        try:
            props = blob.get_blob_properties()
            etag = cast(str | None, getattr(props, "etag", None)) or ""
            size = getattr(props, "size", None)
            fingerprint = f"{etag}:{size}"
        except AzureResourceNotFoundError as exc:
            raise InvalidArtifactError(
                "Active video metadata JSON is missing.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"video_id={video_id}"
                ),
            ) from exc
        except (ClientAuthenticationError, AzureError) as exc:
            logger.exception("azure_video_properties_failed")
            raise DataStoreUnavailableError(
                "Azure Blob Storage is unavailable or credentials are invalid.",
                safe_context="storage=azure_blob",
            ) from exc

        cached = self._video_cache.get(
            dataset_id, dataset_version, video_id, fingerprint=fingerprint
        )
        if cached is not None:
            return cached

        try:
            raw = bytes(blob.download_blob().readall())
        except AzureResourceNotFoundError as exc:
            raise InvalidArtifactError(
                "Active video metadata JSON is missing.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"video_id={video_id}"
                ),
            ) from exc
        except (ClientAuthenticationError, AzureError) as exc:
            logger.exception("azure_video_read_failed")
            raise DataStoreUnavailableError(
                "Azure Blob Storage is unavailable or credentials are invalid.",
                safe_context="storage=azure_blob",
            ) from exc
        artifact = self._parse_video_payload(raw)
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
        run = self._load_json_model(
            f"runs-output/runs/{run_id}/run.json", RunManifest, artifact="run"
        )
        if run.run_id != run_id:
            raise InvalidArtifactError(
                "Run identity does not match storage location.",
                safe_context=f"run_id={run_id}",
            )
        return run

    def load_predictions(self, run: RunManifest) -> PredictionsArtifact:
        key = f"runs-output/runs/{run.run_id}/{run.predictions_artifact}"
        validate_relative_storage_key(run.predictions_artifact, field="predictions_artifact")
        try:
            return self._load_json_model(key, PredictionsArtifact, artifact="predictions")
        except ResourceNotFoundError as exc:
            raise InvalidArtifactError(
                "Predictions artifact is missing for run.",
                safe_context=f"run_id={run.run_id}",
            ) from exc

    def load_metrics(self, run: RunManifest) -> MetricsArtifact | None:
        if run.metrics_artifact is None:
            return None
        validate_relative_storage_key(run.metrics_artifact, field="metrics_artifact")
        key = f"runs-output/runs/{run.run_id}/{run.metrics_artifact}"
        try:
            return self._load_json_model(key, MetricsArtifact, artifact="metrics")
        except ResourceNotFoundError as exc:
            raise InvalidArtifactError(
                "Metrics artifact is declared but missing.",
                safe_context=f"run_id={run.run_id}",
            ) from exc

    def load_evaluation_snapshot(self, run: RunManifest) -> EvaluationSnapshot | None:
        if run.evaluation_snapshot_artifact is None:
            return None
        validate_relative_storage_key(
            run.evaluation_snapshot_artifact, field="evaluation_snapshot_artifact"
        )
        key = f"runs-output/runs/{run.run_id}/{run.evaluation_snapshot_artifact}"
        try:
            return self._load_json_model(key, EvaluationSnapshot, artifact="evaluation_snapshot")
        except ResourceNotFoundError as exc:
            raise InvalidArtifactError(
                "Evaluation snapshot artifact is declared but missing.",
                safe_context=f"run_id={run.run_id}",
            ) from exc

    def load_review(
        self, dataset_id: str, dataset_version: str, image_id: str
    ) -> LoadedReview | None:
        dataset_id = validate_identifier(dataset_id, field="dataset_id")
        dataset_version = validate_identifier(dataset_version, field="dataset_version")
        image_id = validate_identifier(image_id, field="image_id")
        key = f"reviews/{dataset_id}/{dataset_version}/{image_id}.json"
        try:
            raw = self._download_bytes(key)
        except ResourceNotFoundError:
            return None
        return self._parse_review(raw, dataset_id, dataset_version, image_id)

    def mutate_review(
        self,
        dataset_id: str,
        dataset_version: str,
        image_id: str,
        mutator: ReviewMutator,
    ) -> ReviewMutationResult:
        """Read document+ETag from the same blob version; write conditionally.

        Create only if the blob does not exist (If-None-Match: *). Update only
        against the observed ETag (If-Match). Precondition failures map to
        ``StorageConflictError`` — never unconditional overwrite.
        """
        dataset_id = validate_identifier(dataset_id, field="dataset_id")
        dataset_version = validate_identifier(dataset_version, field="dataset_version")
        image_id = validate_identifier(image_id, field="image_id")
        key = f"reviews/{dataset_id}/{dataset_version}/{image_id}.json"
        blob = self._blob(key)

        before: LoadedReview | None = None
        etag: str | None = None
        try:
            download = blob.download_blob()
            raw = download.readall()
            props = download.properties
            etag = cast(str | None, getattr(props, "etag", None))
            before = self._parse_review(raw, dataset_id, dataset_version, image_id)
        except AzureResourceNotFoundError:
            before = None
            etag = None
        except (ClientAuthenticationError, AzureError) as exc:
            logger.exception("azure_review_read_failed")
            raise DataStoreUnavailableError(
                "Azure Blob Storage is unavailable or credentials are invalid.",
                safe_context="storage=azure_blob",
            ) from exc

        decision = mutator(before)
        assert isinstance(decision, ReviewWriteCommit)
        payload = serialize_review_record(decision.record)
        if len(payload) > MAX_REVIEW_DOCUMENT_BYTES:
            raise ReviewDocumentTooLargeError(
                "Review document would exceed the supported per-image size limit.",
                safe_context=f"limit_bytes={MAX_REVIEW_DOCUMENT_BYTES}",
            )

        content_settings = ContentSettings(content_type="application/json; charset=utf-8")
        try:
            if etag is None:
                # Conditional create: succeed only if the blob does not exist.
                blob.upload_blob(
                    payload,
                    overwrite=False,
                    match_condition=MatchConditions.IfMissing,
                    content_settings=content_settings,
                )
            else:
                # Conditional update against the ETag observed with the read.
                blob.upload_blob(
                    payload,
                    overwrite=True,
                    etag=etag,
                    match_condition=MatchConditions.IfNotModified,
                    content_settings=content_settings,
                )
        except ResourceExistsError as exc:
            raise StorageConflictError(
                "Review create precondition failed.",
                safe_context="conflict=blob_exists",
            ) from exc
        except AzureError as exc:
            # Precondition / ETag mismatch surfaces as AzureError with status 412.
            status = getattr(exc, "status_code", None)
            if status == 412:
                raise StorageConflictError(
                    "Review update precondition failed.",
                    safe_context="conflict=etag_mismatch",
                ) from exc
            logger.exception("azure_review_write_failed")
            raise DataStoreUnavailableError(
                "Azure Blob Storage write failed.",
                safe_context="storage=azure_blob",
            ) from exc

        # Post-commit read is observational. Failure here is not proof the write failed.
        after: LoadedReview | None
        try:
            after = self.load_review(dataset_id, dataset_version, image_id)
        except (DataStoreUnavailableError, InvalidArtifactError):
            logger.exception("azure_review_post_commit_read_failed")
            after = None
        return ReviewMutationResult(
            loaded_before=before,
            loaded_after=after,
            wrote=True,
            committed_record=decision.record,
        )

    def read_raw_image_bytes(
        self, dataset_id: str, dataset_version: str, raw_image_key: str
    ) -> tuple[bytes, str]:
        dataset_id = validate_identifier(dataset_id, field="dataset_id")
        dataset_version = validate_identifier(dataset_version, field="dataset_version")
        safe_key = validate_relative_storage_key(raw_image_key, field="raw_image_key")
        key = f"raw-images/{dataset_id}/{dataset_version}/{safe_key}"
        content = self._download_bytes(key)
        suffix = "." + safe_key.rsplit(".", 1)[-1].lower() if "." in safe_key else ""
        media_type = _MEDIA_TYPES.get(suffix, "application/octet-stream")
        return content, media_type

    def _download_bytes(self, key: str) -> bytes:
        blob = self._blob(key)
        try:
            data = blob.download_blob().readall()
            return bytes(data)
        except AzureResourceNotFoundError as exc:
            raise ResourceNotFoundError(
                "Artifact not found.",
                safe_context="artifact=blob",
            ) from exc
        except (ClientAuthenticationError, AzureError) as exc:
            logger.exception("azure_download_failed")
            raise DataStoreUnavailableError(
                "Azure Blob Storage is unavailable or credentials are invalid.",
                safe_context="storage=azure_blob",
            ) from exc

    def _load_json_model(self, key: str, model_type: type[T], *, artifact: str) -> T:
        try:
            raw = self._download_bytes(key)
            payload = json.loads(raw.decode("utf-8"))
            return model_type.model_validate(payload)
        except ResourceNotFoundError:
            raise
        except (UnicodeError, json.JSONDecodeError, ValidationError) as exc:
            logger.exception("invalid_artifact artifact=%s", artifact)
            raise InvalidArtifactError(
                f"Invalid {artifact} artifact.",
                safe_context=f"artifact={artifact}",
            ) from exc

    def _load_dataset_json(self, key: str) -> DatasetVersion:
        try:
            raw = self._download_bytes(key)
            payload = json.loads(raw.decode("utf-8"))
            payload = _strip_retired_ground_truth_editable(payload)
            return DatasetVersion.model_validate(payload)
        except ResourceNotFoundError as exc:
            raise ResourceNotFoundError(
                "Dataset version not found.",
                safe_context="artifact=dataset",
            ) from exc
        except (UnicodeError, json.JSONDecodeError, ValidationError) as exc:
            logger.exception("invalid_artifact artifact=dataset")
            raise InvalidArtifactError(
                "Invalid dataset artifact.",
                safe_context="artifact=dataset",
            ) from exc

    def _parse_video_payload(self, raw: bytes) -> VideoArtifact:
        try:
            payload = json.loads(raw.decode("utf-8"))
            payload = _strip_retired_ground_truth_editable(payload)
            return VideoArtifact.model_validate(payload)
        except (UnicodeError, json.JSONDecodeError, ValidationError) as exc:
            logger.exception("invalid_artifact artifact=video")
            raise InvalidArtifactError(
                "Invalid video metadata artifact.",
                safe_context="artifact=video",
            ) from exc

    def _parse_review(
        self,
        raw: bytes,
        dataset_id: str,
        dataset_version: str,
        image_id: str,
    ) -> LoadedReview:
        try:
            payload = json.loads(raw.decode("utf-8"))
            review = parse_review_payload(payload, artifact="review")
        except (UnicodeError, json.JSONDecodeError) as exc:
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


def _as_str_object_map(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    untyped = cast(dict[object, object], value)
    typed: dict[str, object] = {}
    for key, item in untyped.items():
        typed[str(key)] = item
    return typed


def _strip_retired_ground_truth_editable(payload: object) -> object:
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
