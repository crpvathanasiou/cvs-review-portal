"""Read use cases: catalog listing, effective views, summary, and image bytes."""

from __future__ import annotations

from typing import Literal

from cvs_review_portal.application.interval_index import (
    IntervalRecord,
    build_interval_index,
    dataset_has_provenance,
    find_interval,
    format_summary_clock,
    interval_title,
    search_intervals,
    video_label_from_filename,
)
from cvs_review_portal.application.ports import PortalDataStore
from cvs_review_portal.application.video_resolve import (
    intervals_for_active_video,
    iter_active_images,
    require_published_video_catalog,
    resolve_image,
    resolve_interval,
    search_active_videos,
)
from cvs_review_portal.application.views import (
    DatasetBrowseView,
    DatasetDetailView,
    DatasetListItem,
    DatasetListView,
    EffectiveImageView,
    GroundTruthCounts,
    ImageFrameView,
    IntervalFrameMetaView,
    IntervalFramesView,
    IntervalListView,
    IntervalMetaView,
    IntervalSearchHitView,
    IntervalSearchView,
    MetricsView,
    PredictionCoverage,
    PredictionView,
    ReviewStateView,
    RunDetailView,
    RunImageView,
    RunListItem,
    RunListView,
    RunOverviewView,
    SummaryIntervalRow,
    SummaryView,
    VideoListItem,
    VideoListView,
    VideoPreviewView,
)
from cvs_review_portal.domain.errors import InvalidArtifactError, ResourceNotFoundError
from cvs_review_portal.domain.identifiers import validate_identifier
from cvs_review_portal.domain.models import (
    Catalog,
    DatasetImage,
    DatasetVersion,
    EvaluationSnapshot,
    MetricsArtifact,
    Prediction,
    PredictionsArtifact,
    RunManifest,
    VideoArtifact,
)

_DEFAULT_PICKER_PAGE = 24
_MAX_PICKER_PAGE = 100


class PortalReadService:
    """Compose portal read models without mutating stored manifests."""

    def __init__(self, store: PortalDataStore) -> None:
        self._store = store

    def list_datasets(self) -> DatasetListView:
        catalog = self._load_catalog()
        items: list[DatasetListItem] = []
        for ref in catalog.datasets:
            if self._store.dataset_layout == "video_catalog":
                video_catalog = self._load_published_video_catalog(
                    ref.dataset_id, ref.dataset_version, from_catalog=True
                )
                items.append(
                    DatasetListItem(
                        dataset_id=ref.dataset_id,
                        dataset_version=ref.dataset_version,
                        display_name=f"{ref.dataset_id} {ref.dataset_version}",
                        description=None,
                        image_count=None,
                        video_count=len(video_catalog.entries),
                        dataset_layout="video_catalog",
                    )
                )
                continue
            dataset = self._load_published_dataset(
                ref.dataset_id, ref.dataset_version, from_catalog=True
            )
            items.append(
                DatasetListItem(
                    dataset_id=dataset.dataset_id,
                    dataset_version=dataset.dataset_version,
                    display_name=dataset.display_name,
                    description=dataset.description,
                    image_count=len(dataset.images),
                    video_count=None,
                    dataset_layout="legacy",
                )
            )
        return DatasetListView(datasets=items)

    def get_dataset(self, dataset_id: str, dataset_version: str) -> DatasetDetailView:
        if self._store.dataset_layout == "video_catalog":
            return self._get_dataset_from_videos(dataset_id, dataset_version)
        dataset = self._require_client_dataset(dataset_id, dataset_version)
        images = [self._effective_image(dataset, image) for image in dataset.images]
        return DatasetDetailView(
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
            display_name=dataset.display_name,
            description=dataset.description,
            images=images,
        )

    def list_runs(
        self,
        *,
        dataset_id: str | None = None,
        dataset_version: str | None = None,
    ) -> RunListView:
        if dataset_id is not None:
            validate_identifier(dataset_id, field="dataset_id")
        if dataset_version is not None:
            validate_identifier(dataset_version, field="dataset_version")

        catalog = self._load_catalog()
        if dataset_id is not None and dataset_version is not None:
            if not catalog.has_dataset(dataset_id, dataset_version):
                raise ResourceNotFoundError(
                    "Dataset version not found.",
                    safe_context=(f"dataset_id={dataset_id} dataset_version={dataset_version}"),
                )

        items: list[RunListItem] = []
        for ref in catalog.runs:
            run = self._load_published_run(ref.run_id, from_catalog=True)
            self._ensure_run_dataset_published(catalog, run)
            if dataset_id is not None and (
                run.dataset_id != dataset_id or run.dataset_version != dataset_version
            ):
                continue
            items.append(
                RunListItem(
                    run_id=run.run_id,
                    dataset_id=run.dataset_id,
                    dataset_version=run.dataset_version,
                    model_id=run.model.model_id,
                    model_name=run.model.model_name,
                    model_version=run.model.model_version,
                    executed_at=run.executed_at,
                    has_metrics=run.metrics_artifact is not None,
                )
            )
        return RunListView(runs=items)

    def get_run(self, run_id: str) -> RunDetailView:
        catalog = self._load_catalog()
        run = self._require_client_run(catalog, run_id)
        self._ensure_run_dataset_published(catalog, run)
        dataset = self._require_dataset_for_joins(run.dataset_id, run.dataset_version)
        predictions = self._store.load_predictions(run)
        self._validate_predictions(dataset, predictions)
        metrics_view = self._load_metrics_view(run, dataset, predictions)
        images: list[RunImageView] = []
        prediction_map = predictions.by_image_id()
        for image in dataset.images:
            effective = self._effective_image(dataset, image)
            prediction = prediction_map.get(image.image_id)
            images.append(
                RunImageView(
                    image=effective,
                    prediction=_prediction_view(prediction),
                )
            )
        return RunDetailView(
            run_id=run.run_id,
            dataset_id=run.dataset_id,
            dataset_version=run.dataset_version,
            model=run.model,
            model_parameters=dict(run.model_parameters),
            preprocessing=dict(run.preprocessing),
            execution_description=run.execution_description,
            executed_at=run.executed_at,
            images=images,
            metrics=metrics_view,
        )

    def get_summary(
        self,
        dataset_id: str,
        dataset_version: str,
        *,
        run_id: str | None = None,
    ) -> SummaryView:
        catalog = self._load_catalog()
        dataset = self._require_dataset_for_joins(dataset_id, dataset_version)
        effective_images = [self._effective_image(dataset, image) for image in dataset.images]
        gt_0 = sum(1 for image in effective_images if image.effective_ground_truth == 0)
        gt_1 = sum(1 for image in effective_images if image.effective_ground_truth == 1)
        # Interval rows reuse this same effective-image pass (no second scan).
        intervals = _summary_interval_rows(dataset, effective_images)

        prediction_coverage: PredictionCoverage | None = None
        historical_metrics = MetricsView(available=False)
        resolved_run_id: str | None = None

        if run_id is not None:
            run = self._require_client_run(catalog, run_id)
            if (
                run.dataset_id != dataset.dataset_id
                or run.dataset_version != dataset.dataset_version
            ):
                raise ResourceNotFoundError(
                    "Run does not belong to the requested dataset version.",
                    safe_context=f"run_id={run_id}",
                )
            self._ensure_run_dataset_published(catalog, run)
            resolved_run_id = run.run_id
            predictions = self._store.load_predictions(run)
            self._validate_predictions(dataset, predictions)
            prediction_coverage = _prediction_coverage(dataset, predictions)
            historical_metrics = self._load_metrics_view(run, dataset, predictions)

        return SummaryView(
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
            total_images=len(dataset.images),
            effective_ground_truth=GroundTruthCounts(label_0=gt_0, label_1=gt_1),
            run_id=resolved_run_id,
            prediction_coverage=prediction_coverage,
            historical_metrics=historical_metrics,
            intervals=intervals,
        )

    def get_image_content(
        self,
        dataset_id: str,
        dataset_version: str,
        image_id: str,
        *,
        video_id: str | None = None,
    ) -> tuple[bytes, str]:
        image_id = validate_identifier(image_id, field="image_id")
        dataset_id, dataset_version = self._require_published_ids(dataset_id, dataset_version)
        if video_id is not None:
            video_id = validate_identifier(video_id, field="video_id")
        if self._store.dataset_layout == "video_catalog":
            resolved = resolve_image(
                self._store,
                dataset_id,
                dataset_version,
                image_id,
                video_id=video_id,
            )
            return self._store.read_raw_image_bytes(
                dataset_id, dataset_version, resolved.image.raw_image_key
            )
        dataset = self._require_client_dataset(dataset_id, dataset_version)
        image = dataset.get_image(image_id)
        if image is None:
            raise ResourceNotFoundError(
                "Image not found in dataset version.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"image_id={image_id}"
                ),
            )
        return self._store.read_raw_image_bytes(
            dataset.dataset_id, dataset.dataset_version, image.raw_image_key
        )

    def get_browse(self, dataset_id: str, dataset_version: str) -> DatasetBrowseView:
        """Dataset header + browse mode without loading per-image reviews."""
        dataset_id, dataset_version = self._require_published_ids(dataset_id, dataset_version)
        if self._store.dataset_layout == "video_catalog":
            video_catalog = self._load_published_video_catalog(
                dataset_id, dataset_version, from_catalog=True
            )
            # Bootstrap reads CSV only — no video JSON, no image/interval counts.
            return DatasetBrowseView(
                dataset_id=dataset_id,
                dataset_version=dataset_version,
                display_name=f"{dataset_id} {dataset_version}",
                description=None,
                image_count=None,
                browse_mode="interval",
                interval_count=None,
                video_count=len(video_catalog.entries),
                dataset_layout="video_catalog",
            )
        dataset = self._require_client_dataset(dataset_id, dataset_version)
        has_intervals = dataset_has_provenance(dataset)
        interval_count = len(build_interval_index(dataset)) if has_intervals else 0
        return DatasetBrowseView(
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
            display_name=dataset.display_name,
            description=dataset.description,
            image_count=len(dataset.images),
            browse_mode="interval" if has_intervals else "image",
            interval_count=interval_count,
            video_count=None,
            dataset_layout="legacy",
        )

    def list_videos(self, dataset_id: str, dataset_version: str) -> VideoListView:
        """List active videos from CSV only (no video JSON)."""
        dataset_id, dataset_version = self._require_published_ids(dataset_id, dataset_version)
        if self._store.dataset_layout != "video_catalog":
            raise ResourceNotFoundError(
                "Video listing requires DATASET_LAYOUT=video_catalog.",
                safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
            )
        video_catalog = self._load_published_video_catalog(
            dataset_id, dataset_version, from_catalog=True
        )
        return VideoListView(
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            videos=[
                VideoListItem(video_id=entry.video_id, video_name=entry.video_name)
                for entry in video_catalog.entries
            ],
            total=len(video_catalog.entries),
        )

    def get_video_preview(
        self, dataset_id: str, dataset_version: str, video_id: str
    ) -> VideoPreviewView:
        """Lazy preview for one active video: readable label + first ordered image id.

        Loads only that video's JSON (CSV membership rechecked). Used for picker
        thumbnails; not part of CSV-only listing bootstrap.
        """
        dataset_id, dataset_version = self._require_published_ids(dataset_id, dataset_version)
        if self._store.dataset_layout != "video_catalog":
            raise ResourceNotFoundError(
                "Video preview requires DATASET_LAYOUT=video_catalog.",
                safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
            )
        video_id = validate_identifier(video_id, field="video_id")
        video, records = intervals_for_active_video(
            self._store, dataset_id, dataset_version, video_id
        )
        if not records:
            raise ResourceNotFoundError(
                "Active video has no intervals.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"video_id={video_id}"
                ),
            )
        first = records[0]
        return VideoPreviewView(
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            video_id=video.video_id,
            video_name=video.video_name,
            video_label=video_label_from_filename(video.video_name),
            first_image_id=first.first_image_id,
        )

    def list_intervals(
        self,
        dataset_id: str,
        dataset_version: str,
        *,
        offset: int = 0,
        limit: int = _DEFAULT_PICKER_PAGE,
        video_id: str | None = None,
    ) -> IntervalListView:
        dataset_id, dataset_version = self._require_published_ids(dataset_id, dataset_version)
        offset, limit = _clamp_page(offset, limit)
        if self._store.dataset_layout == "video_catalog":
            if video_id is None:
                raise ResourceNotFoundError(
                    "video_id is required to list intervals when DATASET_LAYOUT=video_catalog.",
                    safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
                )
            video_id = validate_identifier(video_id, field="video_id")
            video, records = intervals_for_active_video(
                self._store, dataset_id, dataset_version, video_id
            )
            page = records[offset : offset + limit]
            return IntervalListView(
                dataset_id=dataset_id,
                dataset_version=dataset_version,
                intervals=[self._interval_meta_video(video, record) for record in page],
                total=len(records),
                offset=offset,
                limit=limit,
            )
        dataset = self._require_client_dataset(dataset_id, dataset_version)
        records = build_interval_index(dataset)
        if video_id is not None:
            video_id = validate_identifier(video_id, field="video_id")
            records = [record for record in records if record.video_id == video_id]
        page = records[offset : offset + limit]
        return IntervalListView(
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
            intervals=[self._interval_meta(dataset, record) for record in page],
            total=len(records),
            offset=offset,
            limit=limit,
        )

    def search_intervals(
        self,
        dataset_id: str,
        dataset_version: str,
        *,
        query: str,
        offset: int = 0,
        limit: int = _DEFAULT_PICKER_PAGE,
    ) -> IntervalSearchView:
        dataset_id, dataset_version = self._require_published_ids(dataset_id, dataset_version)
        offset, limit = _clamp_page(offset, limit)
        if self._store.dataset_layout == "video_catalog":
            match_kind, matched, image_hit = search_active_videos(
                self._store, dataset_id, dataset_version, query
            )
            total = len(matched)
            page = matched[offset : offset + limit]
            hits: list[IntervalSearchHitView] = []
            for video, record in page:
                target_image_id: str | None = None
                target_frame_index: int | None = None
                if (
                    match_kind == "image"
                    and image_hit is not None
                    and image_hit[1].segment_id == record.segment_id
                ):
                    target_image_id = image_hit[1].frames[image_hit[2]].image_id
                    target_frame_index = image_hit[2] + 1
                hits.append(
                    IntervalSearchHitView(
                        interval=self._interval_meta_video(video, record),
                        target_image_id=target_image_id,
                        target_frame_index=target_frame_index,
                    )
                )
            return IntervalSearchView(
                dataset_id=dataset_id,
                dataset_version=dataset_version,
                query=query,
                match_kind=match_kind,  # type: ignore[arg-type]
                hits=hits,
                total=total,
                offset=offset,
                limit=limit,
            )
        dataset = self._require_client_dataset(dataset_id, dataset_version)
        records = build_interval_index(dataset)
        match_kind, matched, image_hit = search_intervals(records, query)
        total = len(matched)
        page = matched[offset : offset + limit]
        hits = []
        for record in page:
            target_image_id = None
            target_frame_index = None
            if (
                match_kind == "image"
                and image_hit is not None
                and image_hit[0].segment_id == record.segment_id
            ):
                target_image_id = image_hit[0].frames[image_hit[1]].image_id
                # API exposes 1-based frame position within the interval.
                target_frame_index = image_hit[1] + 1
            hits.append(
                IntervalSearchHitView(
                    interval=self._interval_meta(dataset, record),
                    target_image_id=target_image_id,
                    target_frame_index=target_frame_index,
                )
            )
        return IntervalSearchView(
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
            query=query,
            match_kind=match_kind,
            hits=hits,
            total=total,
            offset=offset,
            limit=limit,
        )

    def get_interval_frames(
        self,
        dataset_id: str,
        dataset_version: str,
        segment_id: str,
        *,
        video_id: str | None = None,
    ) -> IntervalFramesView:
        dataset_id, dataset_version = self._require_published_ids(dataset_id, dataset_version)
        segment_id = validate_identifier(segment_id, field="segment_id")
        if video_id is not None:
            video_id = validate_identifier(video_id, field="video_id")
        if self._store.dataset_layout == "video_catalog":
            video, record = resolve_interval(
                self._store,
                dataset_id,
                dataset_version,
                segment_id,
                video_id=video_id,
            )
            display_name = video.display_name
        else:
            dataset = self._require_client_dataset(dataset_id, dataset_version)
            record = find_interval(build_interval_index(dataset), segment_id)
            if record is None:
                raise ResourceNotFoundError(
                    "Interval not found in dataset version.",
                    safe_context=(
                        f"dataset_id={dataset_id} dataset_version={dataset_version} "
                        f"segment_id={segment_id}"
                    ),
                )
            display_name = dataset.display_name
        frames = [
            IntervalFrameMetaView(
                image_id=frame.image_id,
                frame_index=frame.frame_index,
                display_id=frame.display_id,
                position=index + 1,
            )
            for index, frame in enumerate(record.frames)
        ]
        return IntervalFramesView(
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            segment_id=record.segment_id,
            video_id=record.video_id,
            video_filename=record.video_filename,
            start_seconds=record.start_seconds,
            end_seconds=record.end_seconds,
            title=interval_title(display_name, record),
            image_count=record.image_count,
            frames=frames,
        )

    def get_image_frame_view(
        self,
        dataset_id: str,
        dataset_version: str,
        image_id: str,
        *,
        run_id: str | None = None,
        video_id: str | None = None,
    ) -> ImageFrameView:
        """Effective state for one image only (optional prediction for a run)."""
        catalog = self._load_catalog()
        dataset_id, dataset_version = self._require_published_ids(dataset_id, dataset_version)
        image_id = validate_identifier(image_id, field="image_id")
        if video_id is not None:
            video_id = validate_identifier(video_id, field="video_id")

        if self._store.dataset_layout == "video_catalog":
            resolved = resolve_image(
                self._store,
                dataset_id,
                dataset_version,
                image_id,
                video_id=video_id,
            )
            video = resolved.video
            image = resolved.image
            dataset_proj = video.as_dataset_version()
            effective = self._effective_image(dataset_proj, image)
            display_id = image.provenance.display_id if image.provenance else None
            segment_id = image.provenance.segment_id if image.provenance else None
            video_id = image.provenance.video_id if image.provenance else None
            position: int | None = None
            image_count: int | None = None
            if segment_id is not None:
                record = find_interval(build_interval_index(dataset_proj), segment_id)
                if record is not None:
                    image_count = record.image_count
                    for index, frame in enumerate(record.frames):
                        if frame.image_id == image_id:
                            position = index + 1
                            break
            prediction: PredictionView | None = None
            if run_id is not None:
                run = self._require_client_run(catalog, run_id)
                if run.dataset_id != dataset_id or run.dataset_version != dataset_version:
                    raise ResourceNotFoundError(
                        "Run does not belong to the requested dataset version.",
                        safe_context=f"run_id={run_id}",
                    )
                self._ensure_run_dataset_published(catalog, run)
                predictions = self._store.load_predictions(run)
                prediction = _prediction_view(predictions.by_image_id().get(image_id))
            return ImageFrameView(
                image=effective,
                display_id=display_id,
                segment_id=segment_id,
                video_id=video_id,
                position=position,
                image_count=image_count,
                prediction=prediction,
            )

        dataset = self._require_client_dataset(dataset_id, dataset_version)
        image = dataset.get_image(image_id)
        if image is None:
            raise ResourceNotFoundError(
                "Image not found in dataset version.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"image_id={image_id}"
                ),
            )
        effective = self._effective_image(dataset, image)
        display_id = image.provenance.display_id if image.provenance else None
        segment_id = image.provenance.segment_id if image.provenance else None
        video_id = image.provenance.video_id if image.provenance else None
        position = None
        image_count = None
        if segment_id is not None:
            record = find_interval(build_interval_index(dataset), segment_id)
            if record is not None:
                image_count = record.image_count
                for index, frame in enumerate(record.frames):
                    if frame.image_id == image_id:
                        position = index + 1
                        break

        prediction = None
        if run_id is not None:
            run = self._require_client_run(catalog, run_id)
            if (
                run.dataset_id != dataset.dataset_id
                or run.dataset_version != dataset.dataset_version
            ):
                raise ResourceNotFoundError(
                    "Run does not belong to the requested dataset version.",
                    safe_context=f"run_id={run_id}",
                )
            self._ensure_run_dataset_published(catalog, run)
            predictions = self._store.load_predictions(run)
            self._validate_predictions(dataset, predictions)
            prediction = _prediction_view(predictions.by_image_id().get(image_id))

        return ImageFrameView(
            image=effective,
            display_id=display_id,
            segment_id=segment_id,
            video_id=video_id,
            position=position,
            image_count=image_count,
            prediction=prediction,
        )

    def get_run_overview(self, run_id: str) -> RunOverviewView:
        """Run metadata and metrics without composing per-image effective reviews."""
        catalog = self._load_catalog()
        run = self._require_client_run(catalog, run_id)
        self._ensure_run_dataset_published(catalog, run)
        dataset = self._require_dataset_for_joins(run.dataset_id, run.dataset_version)
        predictions = self._store.load_predictions(run)
        self._validate_predictions(dataset, predictions)
        metrics_view = self._load_metrics_view(run, dataset, predictions)
        return RunOverviewView(
            run_id=run.run_id,
            dataset_id=run.dataset_id,
            dataset_version=run.dataset_version,
            model=run.model,
            model_parameters=dict(run.model_parameters),
            preprocessing=dict(run.preprocessing),
            execution_description=run.execution_description,
            executed_at=run.executed_at,
            metrics=metrics_view,
        )

    def _interval_meta(self, dataset: DatasetVersion, record: IntervalRecord) -> IntervalMetaView:
        return IntervalMetaView(
            segment_id=record.segment_id,
            video_id=record.video_id,
            video_filename=record.video_filename,
            start_seconds=record.start_seconds,
            end_seconds=record.end_seconds,
            image_count=record.image_count,
            first_image_id=record.first_image_id,
            title=interval_title(dataset.display_name, record),
        )

    def _interval_meta_video(
        self, video: VideoArtifact, record: IntervalRecord
    ) -> IntervalMetaView:
        return IntervalMetaView(
            segment_id=record.segment_id,
            video_id=record.video_id,
            video_filename=record.video_filename,
            start_seconds=record.start_seconds,
            end_seconds=record.end_seconds,
            image_count=record.image_count,
            first_image_id=record.first_image_id,
            title=interval_title(video.display_name, record),
        )

    def _load_catalog(self) -> Catalog:
        return self._store.load_catalog()

    def _require_published_ids(self, dataset_id: str, dataset_version: str) -> tuple[str, str]:
        catalog = self._load_catalog()
        dataset_id = validate_identifier(dataset_id, field="dataset_id")
        dataset_version = validate_identifier(dataset_version, field="dataset_version")
        if not catalog.has_dataset(dataset_id, dataset_version):
            raise ResourceNotFoundError(
                "Dataset version not found.",
                safe_context=(f"dataset_id={dataset_id} dataset_version={dataset_version}"),
            )
        return dataset_id, dataset_version

    def _require_client_dataset(self, dataset_id: str, dataset_version: str) -> DatasetVersion:
        dataset_id, dataset_version = self._require_published_ids(dataset_id, dataset_version)
        return self._load_published_dataset(dataset_id, dataset_version, from_catalog=True)

    def _require_dataset_for_joins(self, dataset_id: str, dataset_version: str) -> DatasetVersion:
        """Dataset projection for summary/run joins (active videos only in video_catalog)."""
        dataset_id, dataset_version = self._require_published_ids(dataset_id, dataset_version)
        if self._store.dataset_layout == "video_catalog":
            return self._compose_active_dataset(dataset_id, dataset_version)
        return self._load_published_dataset(dataset_id, dataset_version, from_catalog=True)

    def _compose_active_dataset(self, dataset_id: str, dataset_version: str) -> DatasetVersion:
        pairs = iter_active_images(self._store, dataset_id, dataset_version)
        if not pairs:
            return DatasetVersion(
                schema_version="1",  # type: ignore[arg-type]
                dataset_id=dataset_id,
                dataset_version=dataset_version,
                display_name=f"{dataset_id} {dataset_version}",
                description=None,
                images=[],
            )
        first_video = pairs[0][0]
        images = [image for _, image in pairs]
        return DatasetVersion(
            schema_version=first_video.schema_version,
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            display_name=first_video.display_name,
            description=first_video.description,
            images=images,
        )

    def _get_dataset_from_videos(self, dataset_id: str, dataset_version: str) -> DatasetDetailView:
        dataset = self._require_dataset_for_joins(dataset_id, dataset_version)
        images = [self._effective_image(dataset, image) for image in dataset.images]
        return DatasetDetailView(
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
            display_name=dataset.display_name,
            description=dataset.description,
            images=images,
        )

    def _load_published_video_catalog(
        self, dataset_id: str, dataset_version: str, *, from_catalog: bool
    ):
        try:
            return require_published_video_catalog(self._store, dataset_id, dataset_version)
        except ResourceNotFoundError as exc:
            if from_catalog:
                raise InvalidArtifactError(
                    "Catalog references a missing video catalog.",
                    safe_context=(f"dataset_id={dataset_id} dataset_version={dataset_version}"),
                ) from exc
            raise

    def _require_client_run(self, catalog: Catalog, run_id: str) -> RunManifest:
        run_id = validate_identifier(run_id, field="run_id")
        if not catalog.has_run(run_id):
            raise ResourceNotFoundError(
                "Run not found.",
                safe_context=f"run_id={run_id}",
            )
        return self._load_published_run(run_id, from_catalog=True)

    def _load_published_dataset(
        self, dataset_id: str, dataset_version: str, *, from_catalog: bool
    ) -> DatasetVersion:
        try:
            return self._store.load_dataset(dataset_id, dataset_version)
        except ResourceNotFoundError as exc:
            if from_catalog:
                raise InvalidArtifactError(
                    "Catalog references a missing dataset version.",
                    safe_context=(f"dataset_id={dataset_id} dataset_version={dataset_version}"),
                ) from exc
            raise

    def _load_published_run(self, run_id: str, *, from_catalog: bool) -> RunManifest:
        try:
            return self._store.load_run(run_id)
        except ResourceNotFoundError as exc:
            if from_catalog:
                raise InvalidArtifactError(
                    "Catalog references a missing run.",
                    safe_context=f"run_id={run_id}",
                ) from exc
            raise

    def _ensure_run_dataset_published(self, catalog: Catalog, run: RunManifest) -> None:
        if not catalog.has_dataset(run.dataset_id, run.dataset_version):
            raise InvalidArtifactError(
                "Published run references an unpublished dataset version.",
                safe_context=f"run_id={run.run_id}",
            )

    def _effective_image(self, dataset: DatasetVersion, image: DatasetImage) -> EffectiveImageView:
        review = self._store.load_review(
            dataset.dataset_id, dataset.dataset_version, image.image_id
        )

        effective_gt = image.ground_truth
        effective_comments = image.comments
        review_view: ReviewStateView | None = None

        persisted_revision = 0
        if review is not None:
            persisted_revision = review.revision
            review_view = ReviewStateView(
                ground_truth_override=review.ground_truth_override,
                comments=review.comments,
                revision=review.revision,
                actor=review.actor,
                updated_at=review.updated_at,
            )
            if review.ground_truth_override is not None:
                effective_gt = review.ground_truth_override
            # Comments: use review value when present, including intentional empty string.
            if review.comments is not None:
                effective_comments = review.comments

        return EffectiveImageView(
            image_id=image.image_id,
            raw_image_key=image.raw_image_key,
            original_ground_truth=image.ground_truth,
            original_comments=image.comments,
            effective_ground_truth=effective_gt,
            effective_comments=effective_comments,
            review=review_view,
            persisted_revision=persisted_revision,
        )

    def _validate_predictions(
        self, dataset: DatasetVersion, predictions: PredictionsArtifact
    ) -> None:
        known = dataset.image_ids()
        for prediction in predictions.predictions:
            if prediction.image_id not in known:
                raise InvalidArtifactError(
                    "Prediction references unknown image_id.",
                    safe_context=f"image_id={prediction.image_id}",
                )

    def _load_metrics_view(
        self,
        run: RunManifest,
        dataset: DatasetVersion,
        predictions: PredictionsArtifact,
    ) -> MetricsView:
        metrics = self._store.load_metrics(run)
        snapshot = self._store.load_evaluation_snapshot(run)
        if metrics is None and snapshot is None:
            return MetricsView(available=False)
        if metrics is None or snapshot is None:
            raise InvalidArtifactError(
                "Metrics and evaluation snapshot must be published together.",
                safe_context=f"run_id={run.run_id}",
            )
        if len(predictions.predictions) == 0:
            raise InvalidArtifactError(
                "Metrics cannot be available when there are no predictions.",
                safe_context=f"run_id={run.run_id}",
            )
        if metrics.evaluated_image_count == 0:
            raise InvalidArtifactError(
                "Published metrics must evaluate at least one image.",
                safe_context=f"run_id={run.run_id}",
            )
        self._validate_evaluation_consistency(dataset, predictions, metrics, snapshot)
        return MetricsView(
            available=True,
            accuracy=metrics.accuracy,
            precision=metrics.precision,
            recall=metrics.recall,
            f1=metrics.f1,
            confusion_matrix=metrics.confusion_matrix,
            evaluated_image_count=metrics.evaluated_image_count,
            evaluation_snapshot=snapshot,
        )

    def _validate_evaluation_consistency(
        self,
        dataset: DatasetVersion,
        predictions: PredictionsArtifact,
        metrics: MetricsArtifact,
        snapshot: EvaluationSnapshot,
    ) -> None:
        if len(snapshot.evaluated_images) != metrics.evaluated_image_count:
            raise InvalidArtifactError(
                "Evaluation snapshot size does not match evaluated_image_count.",
                safe_context="artifact=evaluation_snapshot",
            )
        known = dataset.image_ids()
        prediction_ids = predictions.by_image_id()
        for item in snapshot.evaluated_images:
            if item.image_id not in known:
                raise InvalidArtifactError(
                    "Evaluation snapshot references unknown image_id.",
                    safe_context=f"image_id={item.image_id}",
                )
            if item.image_id not in prediction_ids:
                raise InvalidArtifactError(
                    "Evaluation snapshot image lacks a prediction.",
                    safe_context=f"image_id={item.image_id}",
                )


def _summary_interval_rows(
    dataset: DatasetVersion,
    effective_images: list[EffectiveImageView],
) -> list[SummaryIntervalRow]:
    """Build one Summary row per interval from the already-loaded effective images."""
    if not dataset_has_provenance(dataset):
        return []
    effective_by_id = {image.image_id: image.effective_ground_truth for image in effective_images}
    records = build_interval_index(dataset)
    records_sorted = sorted(
        records,
        key=lambda record: (
            record.video_filename.lower(),
            record.start_seconds,
            record.end_seconds,
            record.segment_id,
        ),
    )
    rows: list[SummaryIntervalRow] = []
    for record in records_sorted:
        labels: set[int] = set()
        for frame in record.frames:
            label = effective_by_id.get(frame.image_id)
            if label is not None:
                labels.add(int(label))
        ground_truth: Literal[0, 1, "Mixed"]
        if labels == {0}:
            ground_truth = 0
        elif labels == {1}:
            ground_truth = 1
        elif labels == {0, 1}:
            ground_truth = "Mixed"
        else:
            # No effective labels resolved for this interval's frames.
            ground_truth = "Mixed"
        start = format_summary_clock(record.start_seconds)
        end = format_summary_clock(record.end_seconds)
        rows.append(
            SummaryIntervalRow(
                segment_id=record.segment_id,
                video_id=record.video_id,
                video_label=video_label_from_filename(record.video_filename),
                time_interval=f"{start}–{end}",
                ground_truth=ground_truth,
                image_count=record.image_count,
            )
        )
    return rows


def _prediction_view(prediction: Prediction | None) -> PredictionView:
    if prediction is None:
        return PredictionView(available=False)
    return PredictionView(
        available=True,
        predicted_label=prediction.predicted_label,
        positive_class_probability=prediction.positive_class_probability,
        description=prediction.description,
    )


def _prediction_coverage(
    dataset: DatasetVersion, predictions: PredictionsArtifact
) -> PredictionCoverage:
    prediction_map = predictions.by_image_id()
    with_prediction = 0
    label_0 = 0
    label_1 = 0
    for image in dataset.images:
        prediction = prediction_map.get(image.image_id)
        if prediction is None:
            continue
        with_prediction += 1
        # Preserve legitimate zero labels explicitly.
        if prediction.predicted_label == 0:
            label_0 += 1
        elif prediction.predicted_label == 1:
            label_1 += 1
    total = len(dataset.images)
    return PredictionCoverage(
        total_images=total,
        with_prediction=with_prediction,
        without_prediction=total - with_prediction,
        predicted_label_0=label_0,
        predicted_label_1=label_1,
    )


def _clamp_page(offset: int, limit: int) -> tuple[int, int]:
    if offset < 0:
        offset = 0
    if limit < 1:
        limit = _DEFAULT_PICKER_PAGE
    if limit > _MAX_PICKER_PAGE:
        limit = _MAX_PICKER_PAGE
    return offset, limit
