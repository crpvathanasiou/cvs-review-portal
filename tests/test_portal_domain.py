"""Domain contract validation tests."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cvs_review_portal.domain.errors import InvalidIdentifierError
from cvs_review_portal.domain.identifiers import (
    validate_identifier,
    validate_relative_storage_key,
)
from cvs_review_portal.domain.models import (
    Catalog,
    CatalogDatasetRef,
    CatalogRunRef,
    ConfusionMatrix,
    DatasetImage,
    EvaluationImage,
    MetricsArtifact,
    Prediction,
    PredictionsArtifact,
    ReviewRecord,
)
from cvs_review_portal.domain.types import parse_binary_label, parse_optional_unit_interval


def test_identifier_rejects_traversal() -> None:
    with pytest.raises(InvalidIdentifierError):
        validate_identifier("..", field="dataset_id")
    with pytest.raises(InvalidIdentifierError):
        validate_identifier("a/b", field="dataset_id")
    with pytest.raises(InvalidIdentifierError):
        validate_relative_storage_key("../x.png")
    with pytest.raises(InvalidIdentifierError):
        validate_relative_storage_key("/abs/x.png")


def test_strict_binary_label_rejects_bool_float_string() -> None:
    with pytest.raises(ValueError):
        parse_binary_label(True)
    with pytest.raises(ValueError):
        parse_binary_label(False)
    with pytest.raises(ValueError):
        parse_binary_label(0.0)
    with pytest.raises(ValueError):
        parse_binary_label(1.0)
    with pytest.raises(ValueError):
        parse_binary_label("0")
    with pytest.raises(ValueError):
        parse_binary_label(2)
    assert parse_binary_label(0) == 0
    assert parse_binary_label(1) == 1


def test_models_reject_non_integer_binary_labels() -> None:
    with pytest.raises(ValidationError):
        DatasetImage(
            image_id="a",
            raw_image_key="a.png",
            ground_truth=True,  # type: ignore[arg-type]
        )
    with pytest.raises(ValidationError):
        Prediction(image_id="a", predicted_label=0.0)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        EvaluationImage(image_id="a", ground_truth="1")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        ConfusionMatrix(labels=[True, 1], matrix=[[1, 0], [0, 1]])  # type: ignore[list-item]


def test_strict_integer_counts_and_revisions() -> None:
    with pytest.raises(ValidationError):
        ConfusionMatrix(labels=[0, 1], matrix=[[1.0, 0], [0, 1]])  # type: ignore[list-item]
    with pytest.raises(ValidationError):
        ConfusionMatrix(labels=[0, 1], matrix=[[True, 0], [0, 1]])  # type: ignore[list-item]
    with pytest.raises(ValidationError):
        MetricsArtifact(
            schema_version="1",
            evaluated_image_count=1.0,  # type: ignore[arg-type]
        )
    with pytest.raises(ValidationError):
        ReviewRecord(
            schema_version="1",
            dataset_id="ds-a",
            dataset_version="v1",
            image_id="a",
            ground_truth_override=None,
            comments=None,
            revision=1.0,  # type: ignore[arg-type]
            actor="x",
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_prediction_rejects_invalid_probability_and_label() -> None:
    with pytest.raises(ValidationError):
        Prediction(image_id="a", predicted_label=2)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        Prediction(image_id="a", predicted_label=0, positive_class_probability=1.1)
    with pytest.raises(ValidationError):
        Prediction(image_id="a", predicted_label=0, positive_class_probability=True)


def test_metric_scores_reject_bool_nan_inf_and_out_of_range() -> None:
    with pytest.raises(ValueError):
        parse_optional_unit_interval(True)
    with pytest.raises(ValueError):
        parse_optional_unit_interval(math.nan)
    with pytest.raises(ValueError):
        parse_optional_unit_interval(math.inf)
    with pytest.raises(ValueError):
        parse_optional_unit_interval(-0.1)
    with pytest.raises(ValueError):
        parse_optional_unit_interval(1.1)
    with pytest.raises(ValueError):
        parse_optional_unit_interval("0.5")
    assert parse_optional_unit_interval(None) is None
    assert parse_optional_unit_interval(0) == 0.0
    assert parse_optional_unit_interval(1.0) == 1.0

    with pytest.raises(ValidationError):
        MetricsArtifact(
            schema_version="1",
            accuracy=True,  # type: ignore[arg-type]
            evaluated_image_count=1,
        )
    with pytest.raises(ValidationError):
        MetricsArtifact(
            schema_version="1",
            precision=math.nan,
            evaluated_image_count=1,
        )


def test_zero_evaluated_images_metrics_rejected() -> None:
    with pytest.raises(ValidationError):
        MetricsArtifact(
            schema_version="1",
            accuracy=1.0,
            precision=None,
            recall=None,
            f1=None,
            confusion_matrix=None,
            evaluated_image_count=0,
        )


def test_duplicate_predictions_rejected() -> None:
    with pytest.raises(ValidationError):
        PredictionsArtifact(
            schema_version="1",
            predictions=[
                Prediction(image_id="a", predicted_label=0),
                Prediction(image_id="a", predicted_label=1),
            ],
        )


def test_confusion_matrix_sum_must_match_count() -> None:
    with pytest.raises(ValidationError):
        MetricsArtifact(
            schema_version="1",
            accuracy=1.0,
            precision=None,
            recall=None,
            f1=None,
            confusion_matrix=ConfusionMatrix(labels=[0, 1], matrix=[[1, 0], [0, 1]]),
            evaluated_image_count=3,
        )


def test_catalog_rejects_duplicate_entries() -> None:
    with pytest.raises(ValidationError):
        Catalog(
            schema_version="1",
            datasets=[
                CatalogDatasetRef(dataset_id="ds-a", dataset_version="v1"),
                CatalogDatasetRef(dataset_id="ds-a", dataset_version="v1"),
            ],
            runs=[],
        )
    with pytest.raises(ValidationError):
        Catalog(
            schema_version="1",
            datasets=[],
            runs=[
                CatalogRunRef(run_id="run-a"),
                CatalogRunRef(run_id="run-a"),
            ],
        )


def test_legitimate_zero_prediction_round_trips() -> None:
    artifact = PredictionsArtifact(
        schema_version="1",
        predictions=[Prediction(image_id="a", predicted_label=0)],
    )
    assert artifact.predictions[0].predicted_label == 0
    assert artifact.by_image_id()["a"].predicted_label == 0
