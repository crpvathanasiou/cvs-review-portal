"""Read-model view types composed by portal use cases."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

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
    # None when DATASET_LAYOUT=video_catalog (full image scan is not done at list time).
    image_count: int | None = None
    video_count: int | None = None
    dataset_layout: Literal["legacy", "video_catalog"] = "legacy"


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


class SummaryIntervalRow(ViewModel):
    """One active interval for the Summary tab table (not a per-image row)."""

    segment_id: str
    video_id: str
    video_label: str
    time_interval: str
    # Effective GT for the interval: 0, 1, or Mixed when frames disagree.
    ground_truth: Literal[0, 1, "Mixed"]
    image_count: int = Field(ge=0)


class SummaryView(ViewModel):
    dataset_id: str
    dataset_version: str
    total_images: int
    effective_ground_truth: GroundTruthCounts
    run_id: str | None
    prediction_coverage: PredictionCoverage | None
    historical_metrics: MetricsView
    # Empty when the dataset has no provenance-backed intervals.
    intervals: list[SummaryIntervalRow] = Field(default_factory=list[SummaryIntervalRow])


# ---------------------------------------------------------------------------
# Interval browse read models (Step 2B) — metadata only unless noted
# ---------------------------------------------------------------------------


class DatasetBrowseView(ViewModel):
    """Lightweight dataset header for UI bootstrap (no per-image reviews)."""

    dataset_id: str
    dataset_version: str
    display_name: str
    description: str | None
    # None when video_catalog bootstrap skips full image/interval scans.
    image_count: int | None = None
    browse_mode: Literal["interval", "image"]
    interval_count: int | None = 0
    video_count: int | None = None
    dataset_layout: Literal["legacy", "video_catalog"] = "legacy"


class VideoListItem(ViewModel):
    video_id: str
    video_name: str


class VideoListView(ViewModel):
    dataset_id: str
    dataset_version: str
    videos: list[VideoListItem]
    total: int


class VideoPreviewView(ViewModel):
    """Lazy per-video picker preview (loads one video JSON)."""

    dataset_id: str
    dataset_version: str
    video_id: str
    video_name: str
    video_label: str
    first_image_id: str


class IntervalMetaView(ViewModel):
    segment_id: str
    video_id: str
    video_filename: str
    start_seconds: int
    end_seconds: int
    image_count: int
    first_image_id: str
    title: str


class IntervalListView(ViewModel):
    dataset_id: str
    dataset_version: str
    intervals: list[IntervalMetaView]
    total: int
    offset: int
    limit: int


class IntervalSearchHitView(ViewModel):
    interval: IntervalMetaView
    target_image_id: str | None = None
    target_frame_index: int | None = None


class IntervalSearchView(ViewModel):
    dataset_id: str
    dataset_version: str
    query: str
    match_kind: Literal["empty", "video", "image", "none"]
    hits: list[IntervalSearchHitView]
    total: int
    offset: int
    limit: int


class IntervalFrameMetaView(ViewModel):
    image_id: str
    frame_index: int
    display_id: str
    position: int  # 1-based within the interval


class IntervalFramesView(ViewModel):
    dataset_id: str
    dataset_version: str
    segment_id: str
    video_id: str
    video_filename: str
    start_seconds: int
    end_seconds: int
    title: str
    image_count: int
    frames: list[IntervalFrameMetaView]


class ImageFrameView(ViewModel):
    """Effective review state for one selected frame (optional prediction)."""

    image: EffectiveImageView
    display_id: str | None = None
    segment_id: str | None = None
    video_id: str | None = None
    position: int | None = None
    image_count: int | None = None
    prediction: PredictionView | None = None


class RunOverviewView(ViewModel):
    """Run metadata + metrics without per-image review composition."""

    run_id: str
    dataset_id: str
    dataset_version: str
    model: ModelInfo
    model_parameters: dict[str, object]
    preprocessing: dict[str, object]
    execution_description: str | None
    executed_at: datetime | None
    metrics: MetricsView
