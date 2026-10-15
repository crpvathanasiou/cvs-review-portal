"""Storage port isolating local filesystem and Azure Blob adapters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from cvs_review_portal.domain.models import (
    Catalog,
    DatasetVersion,
    EvaluationSnapshot,
    MetricsArtifact,
    PredictionsArtifact,
    ReviewRecord,
    RunManifest,
    VideoArtifact,
    VideoCatalog,
)
from cvs_review_portal.domain.review_document import LoadedReview
from cvs_review_portal.settings import DatasetLayout


@dataclass(frozen=True, slots=True)
class ReviewWriteCommit:
    """Mutator decision: persist this current-state review record."""

    record: ReviewRecord


ReviewMutator = Callable[[LoadedReview | None], ReviewWriteCommit]


@dataclass(frozen=True, slots=True)
class ReviewMutationResult:
    """Outcome of an atomic compare-and-write against one image review."""

    loaded_before: LoadedReview | None
    loaded_after: LoadedReview | None
    wrote: bool
    committed_record: ReviewRecord | None = None


class PortalDataStore(Protocol):
    """Minimal interface for published portal artifacts and review writes."""

    @property
    def dataset_layout(self) -> DatasetLayout:
        """Configured dataset layout: ``legacy`` or ``video_catalog``."""
        ...

    def load_catalog(self) -> Catalog: ...

    def load_dataset(self, dataset_id: str, dataset_version: str) -> DatasetVersion: ...

    def load_video_catalog(self, dataset_id: str, dataset_version: str) -> VideoCatalog:
        """Load and validate ``videos.csv`` (always re-read; sole activation list)."""
        ...

    def load_video(self, dataset_id: str, dataset_version: str, video_id: str) -> VideoArtifact:
        """Load one active video's metadata JSON (bounded cache; detects file changes)."""
        ...

    def load_run(self, run_id: str) -> RunManifest: ...

    def load_predictions(self, run: RunManifest) -> PredictionsArtifact: ...

    def load_metrics(self, run: RunManifest) -> MetricsArtifact | None: ...

    def load_evaluation_snapshot(self, run: RunManifest) -> EvaluationSnapshot | None: ...

    def load_review(
        self, dataset_id: str, dataset_version: str, image_id: str
    ) -> LoadedReview | None: ...

    def mutate_review(
        self,
        dataset_id: str,
        dataset_version: str,
        image_id: str,
        mutator: ReviewMutator,
    ) -> ReviewMutationResult:
        """Atomically read, apply mutator, and conditionally write one review document.

        Implementations must serialize the full read/check/write transaction using
        storage-native concurrency control (local file lock + atomic replace, or
        Azure blob ETag conditional create/update). Never fall back to unconditional
        overwrite.
        """
        ...

    def read_raw_image_bytes(
        self, dataset_id: str, dataset_version: str, raw_image_key: str
    ) -> tuple[bytes, str]: ...

    def close(self) -> None:
        """Release any held clients. Default no-op for local stores."""
        ...
