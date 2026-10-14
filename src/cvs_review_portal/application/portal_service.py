"""Read use cases: catalog listing, effective views, summary, and image bytes."""

from __future__ import annotations

from cvs_review_portal.application.ports import PortalDataStore
from cvs_review_portal.application.views import (
    DatasetDetailView,
    DatasetListItem,
    DatasetListView,
    EffectiveImageView,
    GroundTruthCounts,
    MetricsView,
    PredictionCoverage,
    PredictionView,
    ReviewStateView,
    RunDetailView,
    RunImageView,
    RunListItem,
    RunListView,
    SummaryView,
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
)


class PortalReadService:
    """Compose portal read models without mutating stored manifests."""

    def __init__(self, store: PortalDataStore) -> None:
        self._store = store

    def list_datasets(self) -> DatasetListView:
        catalog = self._load_catalog()
        items: list[DatasetListItem] = []
        for ref in catalog.datasets:
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
                )
            )
        return DatasetListView(datasets=items)

    def get_dataset(self, dataset_id: str, dataset_version: str) -> DatasetDetailView:
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
        dataset = self._load_published_dataset(
            run.dataset_id, run.dataset_version, from_catalog=True
        )
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
        dataset = self._require_client_dataset(dataset_id, dataset_version)
        effective_images = [self._effective_image(dataset, image) for image in dataset.images]
        gt_0 = sum(1 for image in effective_images if image.effective_ground_truth == 0)
        gt_1 = sum(1 for image in effective_images if image.effective_ground_truth == 1)

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
        )

    def get_image_content(
        self, dataset_id: str, dataset_version: str, image_id: str
    ) -> tuple[bytes, str]:
        dataset = self._require_client_dataset(dataset_id, dataset_version)
        image_id = validate_identifier(image_id, field="image_id")
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

    def _load_catalog(self) -> Catalog:
        return self._store.load_catalog()

    def _require_client_dataset(self, dataset_id: str, dataset_version: str) -> DatasetVersion:
        catalog = self._load_catalog()
        dataset_id = validate_identifier(dataset_id, field="dataset_id")
        dataset_version = validate_identifier(dataset_version, field="dataset_version")
        if not catalog.has_dataset(dataset_id, dataset_version):
            raise ResourceNotFoundError(
                "Dataset version not found.",
                safe_context=(f"dataset_id={dataset_id} dataset_version={dataset_version}"),
            )
        return self._load_published_dataset(dataset_id, dataset_version, from_catalog=True)

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
