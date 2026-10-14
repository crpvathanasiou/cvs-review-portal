"""Read-model view types composed by portal use cases."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from cvs_review_portal.domain.models import (
    BinaryLabel,
    ConfusionMatrix,
    EvaluationSnapshot,
    ModelInfo,
)


class ViewModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DatasetListItem(ViewModel):
    dataset_id: str
    dataset_version: str
    display_name: str
    description: str | None
    image_count: int


class DatasetListView(ViewModel):
    datasets: list[DatasetListItem]


class ReviewStateView(ViewModel):
    ground_truth_override: BinaryLabel | None
    comments: str | None
    revision: int
    actor: str
    updated_at: datetime


class EffectiveImageView(ViewModel):
    image_id: str
    raw_image_key: str
    original_ground_truth: BinaryLabel
    original_comments: str | None
    effective_ground_truth: BinaryLabel
    effective_comments: str | None
    review: ReviewStateView | None
    # Additive: 0 when no persisted review exists (Save expected_revision base).
    persisted_revision: int = 0


class DatasetDetailView(ViewModel):
    dataset_id: str
    dataset_version: str
    display_name: str
    description: str | None
    images: list[EffectiveImageView]


class RunListItem(ViewModel):
    run_id: str
    dataset_id: str
    dataset_version: str
    model_id: str
    model_name: str
    model_version: str | None
    executed_at: datetime | None
    has_metrics: bool


class RunListView(ViewModel):
    runs: list[RunListItem]


class PredictionView(ViewModel):
    available: bool
    predicted_label: BinaryLabel | None = None
    positive_class_probability: float | None = None
    description: str | None = None


class RunImageView(ViewModel):
    image: EffectiveImageView
    prediction: PredictionView


class MetricsView(ViewModel):
    available: bool
    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    confusion_matrix: ConfusionMatrix | None = None
    evaluated_image_count: int | None = None
    evaluation_snapshot: EvaluationSnapshot | None = None


class RunDetailView(ViewModel):
    run_id: str
    dataset_id: str
    dataset_version: str
    model: ModelInfo
    model_parameters: dict[str, object]
    preprocessing: dict[str, object]
    execution_description: str | None
    executed_at: datetime | None
    images: list[RunImageView]
    metrics: MetricsView


class GroundTruthCounts(ViewModel):
    label_0: int = Field(ge=0)
    label_1: int = Field(ge=0)


class PredictionCoverage(ViewModel):
    total_images: int = Field(ge=0)
    with_prediction: int = Field(ge=0)
    without_prediction: int = Field(ge=0)
    predicted_label_0: int = Field(ge=0)
    predicted_label_1: int = Field(ge=0)


class SummaryView(ViewModel):
    dataset_id: str
    dataset_version: str
    total_images: int
    effective_ground_truth: GroundTruthCounts
    run_id: str | None
    prediction_coverage: PredictionCoverage | None
    historical_metrics: MetricsView
