"""Pydantic v2 data contracts for published portal artifacts (schema_version \"1\")."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from cvs_review_portal.domain.identifiers import validate_identifier, validate_relative_storage_key
from cvs_review_portal.domain.types import (
    BinaryLabel,
    NonNegativeInt,
    OptionalBinaryLabel,
    OptionalUnitInterval,
    PositiveInt,
)

# Re-export for application/API layers that import labels from models.
__all__ = (
    "BinaryLabel",
    "Catalog",
    "CatalogDatasetRef",
    "CatalogRunRef",
    "ConfusionMatrix",
    "DatasetImage",
    "DatasetVersion",
    "EvaluationImage",
    "EvaluationSnapshot",
    "ImageProvenance",
    "MetricsArtifact",
    "ModelInfo",
    "Prediction",
    "PredictionsArtifact",
    "ReviewRecord",
    "RunManifest",
    "SchemaVersion",
)

SchemaVersion = Literal["1"]


class PortalModel(BaseModel):
    """Strict portal contract base."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class CatalogDatasetRef(PortalModel):
    dataset_id: str
    dataset_version: str

    @field_validator("dataset_id", "dataset_version")
    @classmethod
    def _ids(cls, value: str, info: ValidationInfo) -> str:
        return validate_identifier(value, field=str(info.field_name))


class CatalogRunRef(PortalModel):
    run_id: str

    @field_validator("run_id")
    @classmethod
    def _run_id(cls, value: str) -> str:
        return validate_identifier(value, field="run_id")


class Catalog(PortalModel):
    schema_version: SchemaVersion
    datasets: list[CatalogDatasetRef]
    runs: list[CatalogRunRef]

    @model_validator(mode="after")
    def _unique_entries(self) -> Catalog:
        seen_datasets: set[tuple[str, str]] = set()
        for ref in self.datasets:
            key = (ref.dataset_id, ref.dataset_version)
            if key in seen_datasets:
                raise ValueError(
                    f"Duplicate catalog dataset entry: {ref.dataset_id}/{ref.dataset_version}"
                )
            seen_datasets.add(key)
        seen_runs: set[str] = set()
        for ref in self.runs:
            if ref.run_id in seen_runs:
                raise ValueError(f"Duplicate catalog run_id: {ref.run_id}")
            seen_runs.add(ref.run_id)
        return self

    def has_dataset(self, dataset_id: str, dataset_version: str) -> bool:
        return any(
            ref.dataset_id == dataset_id and ref.dataset_version == dataset_version
            for ref in self.datasets
        )

    def has_run(self, run_id: str) -> bool:
        return any(ref.run_id == run_id for ref in self.runs)


class ImageProvenance(PortalModel):
    """Optional per-image source provenance (interval/video frame identity).

    Absent (``None``) for datasets that do not carry export provenance, including
    existing demo fixtures. Technical ``image_id`` values remain unchanged.
    """

    video_id: str
    video_filename: str
    segment_id: str
    start_seconds: NonNegativeInt
    end_seconds: NonNegativeInt
    frame_index: NonNegativeInt
    timestamp: float
    display_id: str

    @field_validator("video_id", "segment_id", "display_id")
    @classmethod
    def _ids(cls, value: str, info: ValidationInfo) -> str:
        return validate_identifier(value, field=str(info.field_name))

    @field_validator("video_filename")
    @classmethod
    def _video_filename(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or cleaned != value:
            raise ValueError("video_filename must be a non-empty exact filename")
        return cleaned

    @model_validator(mode="after")
    def _bounds(self) -> ImageProvenance:
        if self.end_seconds < self.start_seconds:
            raise ValueError("end_seconds must be >= start_seconds")
        if not math.isfinite(self.timestamp):
            raise ValueError("timestamp must be a finite number")
        return self


class DatasetImage(PortalModel):
    image_id: str
    raw_image_key: str
    ground_truth: BinaryLabel
    comments: str | None = None
    provenance: ImageProvenance | None = None

    @field_validator("image_id")
    @classmethod
    def _image_id(cls, value: str) -> str:
        return validate_identifier(value, field="image_id")

    @field_validator("raw_image_key")
    @classmethod
    def _raw_key(cls, value: str) -> str:
        return validate_relative_storage_key(value, field="raw_image_key")


class DatasetVersion(PortalModel):
    schema_version: SchemaVersion
    dataset_id: str
    dataset_version: str
    display_name: str
    description: str | None = None
    images: list[DatasetImage]

    @field_validator("dataset_id", "dataset_version")
    @classmethod
    def _ids(cls, value: str, info: ValidationInfo) -> str:
        return validate_identifier(value, field=str(info.field_name))

    @model_validator(mode="after")
    def _unique_image_ids(self) -> DatasetVersion:
        seen: set[str] = set()
        seen_display: set[str] = set()
        for image in self.images:
            if image.image_id in seen:
                raise ValueError(f"Duplicate image_id in dataset: {image.image_id}")
            seen.add(image.image_id)
            if image.provenance is not None:
                display_id = image.provenance.display_id
                if display_id in seen_display:
                    raise ValueError(f"Duplicate provenance.display_id in dataset: {display_id}")
                seen_display.add(display_id)
        return self

    def image_ids(self) -> set[str]:
        return {image.image_id for image in self.images}

    def get_image(self, image_id: str) -> DatasetImage | None:
        for image in self.images:
            if image.image_id == image_id:
                return image
        return None


class ModelInfo(PortalModel):
    model_id: str
    model_name: str
    model_version: str | None = None
    description: str | None = None

    @field_validator("model_id")
    @classmethod
    def _model_id(cls, value: str) -> str:
        return validate_identifier(value, field="model_id")


class RunManifest(PortalModel):
    schema_version: SchemaVersion
    run_id: str
    dataset_id: str
    dataset_version: str
    model: ModelInfo
    model_parameters: dict[str, Any] = Field(default_factory=dict)
    preprocessing: dict[str, Any] = Field(default_factory=dict)
    execution_description: str | None = None
    executed_at: datetime | None = None
    predictions_artifact: str = "predictions.json"
    metrics_artifact: str | None = None
    evaluation_snapshot_artifact: str | None = None

    @field_validator("run_id", "dataset_id", "dataset_version")
    @classmethod
    def _ids(cls, value: str, info: ValidationInfo) -> str:
        return validate_identifier(value, field=str(info.field_name))

    @field_validator("predictions_artifact")
    @classmethod
    def _predictions_artifact(cls, value: str) -> str:
        return validate_relative_storage_key(value, field="predictions_artifact")

    @field_validator("metrics_artifact", "evaluation_snapshot_artifact")
    @classmethod
    def _optional_artifacts(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is None:
            return None
        return validate_relative_storage_key(value, field=str(info.field_name))

    @field_validator("executed_at")
    @classmethod
    def _tz_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("executed_at must be timezone-aware when present")
        return value

    @model_validator(mode="after")
    def _metrics_pair(self) -> RunManifest:
        has_metrics = self.metrics_artifact is not None
        has_snapshot = self.evaluation_snapshot_artifact is not None
        if has_metrics != has_snapshot:
            raise ValueError(
                "metrics_artifact and evaluation_snapshot_artifact must both be set or both null"
            )
        return self


class Prediction(PortalModel):
    image_id: str
    predicted_label: BinaryLabel
    positive_class_probability: OptionalUnitInterval = None
    description: str | None = None

    @field_validator("image_id")
    @classmethod
    def _image_id(cls, value: str) -> str:
        return validate_identifier(value, field="image_id")


class PredictionsArtifact(PortalModel):
    schema_version: SchemaVersion
    predictions: list[Prediction]

    @model_validator(mode="after")
    def _unique_predictions(self) -> PredictionsArtifact:
        seen: set[str] = set()
        for prediction in self.predictions:
            if prediction.image_id in seen:
                raise ValueError(f"Duplicate prediction for image_id: {prediction.image_id}")
            seen.add(prediction.image_id)
        return self

    def by_image_id(self) -> dict[str, Prediction]:
        return {prediction.image_id: prediction for prediction in self.predictions}


class ConfusionMatrix(PortalModel):
    """Confusion matrix with explicit orientation.

    Rows are ground-truth labels and columns are predicted labels, both ordered
    according to `labels`.
    """

    labels: list[BinaryLabel]
    matrix: list[list[NonNegativeInt]]

    @model_validator(mode="after")
    def _shape_and_nonnegative(self) -> ConfusionMatrix:
        size = len(self.labels)
        if size == 0:
            raise ValueError("confusion_matrix.labels must not be empty")
        if len(set(self.labels)) != size:
            raise ValueError("confusion_matrix.labels must be unique")
        if len(self.matrix) != size:
            raise ValueError("confusion_matrix.matrix row count must match labels")
        for row in self.matrix:
            if len(row) != size:
                raise ValueError("confusion_matrix.matrix must be square")
        return self

    def total(self) -> int:
        return sum(cell for row in self.matrix for cell in row)


class MetricsArtifact(PortalModel):
    schema_version: SchemaVersion
    accuracy: OptionalUnitInterval = None
    precision: OptionalUnitInterval = None
    recall: OptionalUnitInterval = None
    f1: OptionalUnitInterval = None
    confusion_matrix: ConfusionMatrix | None = None
    evaluated_image_count: NonNegativeInt

    @model_validator(mode="after")
    def _matrix_sum_and_nonzero(self) -> MetricsArtifact:
        if self.evaluated_image_count == 0:
            raise ValueError(
                "published metrics must evaluate at least one image "
                "(evaluated_image_count must be > 0)"
            )
        if self.confusion_matrix is not None:
            if self.confusion_matrix.total() != self.evaluated_image_count:
                raise ValueError("confusion_matrix counts must sum to evaluated_image_count")
        return self


class EvaluationImage(PortalModel):
    image_id: str
    ground_truth: BinaryLabel

    @field_validator("image_id")
    @classmethod
    def _image_id(cls, value: str) -> str:
        return validate_identifier(value, field="image_id")


class EvaluationSnapshot(PortalModel):
    schema_version: SchemaVersion
    evaluated_images: list[EvaluationImage]

    @model_validator(mode="after")
    def _unique_ids(self) -> EvaluationSnapshot:
        seen: set[str] = set()
        for item in self.evaluated_images:
            if item.image_id in seen:
                raise ValueError(f"Duplicate evaluated image_id: {item.image_id}")
            seen.add(item.image_id)
        return self


class ReviewRecord(PortalModel):
    schema_version: SchemaVersion
    dataset_id: str
    dataset_version: str
    image_id: str
    ground_truth_override: OptionalBinaryLabel = None
    comments: str | None = None
    revision: PositiveInt
    actor: str
    updated_at: datetime

    @field_validator("dataset_id", "dataset_version", "image_id")
    @classmethod
    def _ids(cls, value: str, info: ValidationInfo) -> str:
        return validate_identifier(value, field=str(info.field_name))

    @field_validator("updated_at")
    @classmethod
    def _tz_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("updated_at must be timezone-aware")
        return value
