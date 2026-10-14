"""API and composition tests for Step 1 portal read paths."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic_settings import SettingsConfigDict

from cvs_review_portal.main import create_app
from cvs_review_portal.settings import Settings
from tests.fixture_trees import build_demo_tree, make_settings


def test_system_endpoints_remain_valid_with_data_routes(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    ready = client.get("/ready").json()
    assert ready["status"] == "ready"
    assert client.get("/version").json()["version"]


def test_dataset_without_runs_and_shared_dataset_reuse(client: TestClient) -> None:
    datasets = client.get("/api/datasets").json()["datasets"]
    ids = {(item["dataset_id"], item["dataset_version"]) for item in datasets}
    assert ("ds-b", "v1") in ids
    assert ("ds-a", "v1") in ids

    bare = client.get("/api/datasets/ds-b/versions/v1")
    assert bare.status_code == 200
    assert bare.json()["images"][0]["image_id"] == "only"

    runs = client.get("/api/runs", params={"dataset_id": "ds-a", "dataset_version": "v1"})
    assert runs.status_code == 200
    run_ids = {item["run_id"] for item in runs.json()["runs"]}
    assert run_ids == {"run-full", "run-alt", "run-empty", "run-partial"}

    bare_runs = client.get("/api/runs", params={"dataset_id": "ds-b", "dataset_version": "v1"})
    assert bare_runs.json()["runs"] == []


def test_empty_and_partial_predictions_preserve_zero_labels(client: TestClient) -> None:
    empty = client.get("/api/runs/run-empty").json()
    assert all(item["prediction"]["available"] is False for item in empty["images"])
    assert empty["metrics"]["available"] is False

    partial = client.get("/api/runs/run-partial").json()
    by_id = {item["image"]["image_id"]: item for item in partial["images"]}
    assert by_id["a"]["prediction"]["available"] is False
    assert by_id["b"]["prediction"]["available"] is True
    assert by_id["b"]["prediction"]["predicted_label"] == 0
    assert by_id["c"]["prediction"]["available"] is False


def test_shared_review_composition_across_runs(client: TestClient) -> None:
    dataset = client.get("/api/datasets/ds-a/versions/v1").json()
    image_a = next(item for item in dataset["images"] if item["image_id"] == "a")
    assert image_a["original_ground_truth"] == 0
    assert image_a["effective_ground_truth"] == 1
    assert image_a["effective_comments"] == "reviewed-a"
    assert image_a["review"]["revision"] == 1
    assert "ground_truth_editable" not in image_a

    for run_id in ("run-full", "run-alt"):
        run = client.get(f"/api/runs/{run_id}").json()
        image = next(item for item in run["images"] if item["image"]["image_id"] == "a")
        assert image["image"]["effective_ground_truth"] == 1
        assert image["image"]["original_ground_truth"] == 0
        assert "ground_truth_editable" not in image["image"]


def test_api_does_not_expose_ground_truth_editable(client: TestClient) -> None:
    dataset = client.get("/api/datasets/ds-a/versions/v1").json()
    for image in dataset["images"]:
        assert "ground_truth_editable" not in image
        assert image["effective_ground_truth"] in (0, 1)
        assert image["original_ground_truth"] in (0, 1)

    run = client.get("/api/runs/run-full").json()
    for row in run["images"]:
        assert "ground_truth_editable" not in row["image"]


def test_legacy_ground_truth_editable_field_is_ignored(tmp_path: Path) -> None:
    """Datasets that still store the retired field remain readable."""
    root = tmp_path / "legacy-editable"
    build_demo_tree(root)
    dataset_path = root / "runs-output" / "datasets" / "ds-a" / "v1" / "dataset.json"
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    for index, image in enumerate(payload["images"]):
        image["ground_truth_editable"] = index % 2 == 0
    dataset_path.write_text(json.dumps(payload), encoding="utf-8")

    with TestClient(create_app(make_settings(data_root=root))) as client:
        response = client.get("/api/datasets/ds-a/versions/v1")
        assert response.status_code == 200
        body = response.json()
        by_id = {item["image_id"]: item for item in body["images"]}
        assert by_id["a"]["original_ground_truth"] == 0
        assert by_id["a"]["effective_ground_truth"] == 1  # seeded review override
        assert by_id["b"]["original_ground_truth"] == 1
        assert by_id["b"]["effective_ground_truth"] == 1
        assert all("ground_truth_editable" not in item for item in body["images"])

        metrics = client.get("/api/runs/run-full").json()["metrics"]
        assert metrics["available"] is True
        assert metrics["evaluated_image_count"] == 3
        snapshot = metrics["evaluation_snapshot"]["evaluated_images"]
        assert {"image_id": "a", "ground_truth": 0} in snapshot


def test_evaluation_snapshot_unchanged_by_review(client: TestClient) -> None:
    run = client.get("/api/runs/run-full").json()
    assert run["metrics"]["available"] is True
    snapshot = run["metrics"]["evaluation_snapshot"]["evaluated_images"]
    assert {"image_id": "a", "ground_truth": 0} in snapshot
    # Effective review changed image a to 1, but historical snapshot stays 0.
    image_a = next(item for item in run["images"] if item["image"]["image_id"] == "a")
    assert image_a["image"]["effective_ground_truth"] == 1


def test_summary_counts_and_metrics_availability(client: TestClient) -> None:
    summary = client.get("/api/datasets/ds-a/versions/v1/summary").json()
    assert summary["total_images"] == 3
    assert summary["effective_ground_truth"] == {"label_0": 0, "label_1": 3}
    assert summary["prediction_coverage"] is None
    assert summary["historical_metrics"]["available"] is False

    with_run = client.get(
        "/api/datasets/ds-a/versions/v1/summary", params={"run_id": "run-partial"}
    ).json()
    coverage = with_run["prediction_coverage"]
    assert coverage["with_prediction"] == 1
    assert coverage["without_prediction"] == 2
    assert coverage["predicted_label_0"] == 1
    assert coverage["predicted_label_1"] == 0
    assert with_run["historical_metrics"]["available"] is False

    with_metrics = client.get(
        "/api/datasets/ds-a/versions/v1/summary", params={"run_id": "run-full"}
    ).json()
    assert with_metrics["historical_metrics"]["available"] is True
    assert with_metrics["historical_metrics"]["evaluated_image_count"] == 3


def test_image_retrieval_and_missing_resources(client: TestClient) -> None:
    response = client.get("/api/datasets/ds-a/versions/v1/images/a/content")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"

    assert client.get("/api/runs/missing-run").status_code == 404
    assert client.get("/api/datasets/ds-a/versions/v9").status_code == 404
    assert client.get("/api/datasets/ds-a/versions/v1/images/missing/content").status_code == 404


def test_invalid_stored_data_returns_controlled_error(
    tmp_path: Path,
) -> None:
    root = tmp_path / "bad"
    build_demo_tree(root)
    predictions = root / "runs-output" / "runs" / "run-partial" / "predictions.json"
    payload = json.loads(predictions.read_text(encoding="utf-8"))
    payload["predictions"].append(
        {
            "image_id": "unknown",
            "predicted_label": 1,
            "positive_class_probability": 0.5,
            "description": None,
        }
    )
    predictions.write_text(json.dumps(payload), encoding="utf-8")

    settings = make_settings(data_root=root)
    with TestClient(create_app(settings)) as bad_client:
        response = bad_client.get("/api/runs/run-partial")
        assert response.status_code == 500
        body = response.json()
        detail = body["detail"]
        assert detail["message"]
        # Safe context may name the image_id; raw file contents and absolute paths must not appear.
        dumped = json.dumps(body)
        assert "predictions.json" not in dumped
        assert ":\\" not in dumped
        assert "/Users/" not in dumped


def test_duplicate_prediction_and_invalid_probability_rejected(tmp_path: Path) -> None:
    root = tmp_path / "dup"
    build_demo_tree(root)
    path = root / "runs-output" / "runs" / "run-empty" / "predictions.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "predictions": [
                    {
                        "image_id": "a",
                        "predicted_label": 0,
                        "positive_class_probability": 0.2,
                        "description": None,
                    },
                    {
                        "image_id": "a",
                        "predicted_label": 1,
                        "positive_class_probability": 0.3,
                        "description": None,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    with TestClient(create_app(make_settings(data_root=root))) as client:
        assert client.get("/api/runs/run-empty").status_code == 500

    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "predictions": [
                    {
                        "image_id": "a",
                        "predicted_label": 0,
                        "positive_class_probability": 1.5,
                        "description": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with TestClient(create_app(make_settings(data_root=root))) as client:
        assert client.get("/api/runs/run-empty").status_code == 500


def test_persisted_ground_truth_override_remains_effective(tmp_path: Path) -> None:
    """Read-only portal still applies existing review overrides to effective GT."""
    root = tmp_path / "override"
    build_demo_tree(root)
    review = root / "reviews" / "ds-a" / "v1" / "b.json"
    review.parent.mkdir(parents=True, exist_ok=True)
    review.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "dataset_id": "ds-a",
                "dataset_version": "v1",
                "image_id": "b",
                "ground_truth_override": 0,
                "comments": "override-b",
                "revision": 1,
                "actor": "tester",
                "updated_at": "2026-01-04T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    with TestClient(create_app(make_settings(data_root=root))) as client:
        dataset = client.get("/api/datasets/ds-a/versions/v1").json()
        image_b = next(item for item in dataset["images"] if item["image_id"] == "b")
        assert image_b["original_ground_truth"] == 1
        assert image_b["effective_ground_truth"] == 0
        assert image_b["effective_comments"] == "override-b"
        assert "ground_truth_editable" not in image_b


def test_path_escape_raw_image_key_rejected(tmp_path: Path) -> None:
    root = tmp_path / "escape"
    build_demo_tree(root)
    dataset_path = root / "runs-output" / "datasets" / "ds-a" / "v1" / "dataset.json"
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    payload["images"][0]["raw_image_key"] = "../secret.png"
    dataset_path.write_text(json.dumps(payload), encoding="utf-8")
    with TestClient(create_app(make_settings(data_root=root))) as client:
        assert client.get("/api/datasets/ds-a/versions/v1").status_code == 500


def test_missing_data_root_does_not_break_health(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    settings = make_settings(data_root=missing)
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/api/datasets").status_code == 503


def test_factory_isolation_with_data_root(tmp_path: Path) -> None:
    root_one = tmp_path / "one"
    root_two = tmp_path / "two"
    build_demo_tree(root_one)
    build_demo_tree(root_two)
    app_one = create_app(make_settings(data_root=root_one, app_version="1.0.0"))
    app_two = create_app(make_settings(data_root=root_two, app_version="2.0.0"))
    assert TestClient(app_one).get("/version").json() == {"version": "1.0.0"}
    assert TestClient(app_two).get("/version").json() == {"version": "2.0.0"}
    assert TestClient(app_one).get("/api/datasets").status_code == 200


def test_incomplete_run_filter_is_rejected(client: TestClient) -> None:
    response = client.get("/api/runs", params={"dataset_id": "ds-a"})
    assert response.status_code == 422


def test_settings_accept_data_root(tmp_path: Path) -> None:
    class Local(Settings):
        model_config = SettingsConfigDict(env_file=None)

    settings = Local(data_root=tmp_path)
    assert settings.data_root == tmp_path


def test_unpublished_dataset_and_run_return_404_even_if_files_exist(
    tmp_path: Path,
) -> None:
    root = tmp_path / "unpub"
    build_demo_tree(root)
    # Extra on-disk dataset/run not listed in the catalog.
    orphan_ds = root / "runs-output" / "datasets" / "orphan" / "v1"
    orphan_ds.mkdir(parents=True)
    (orphan_ds / "dataset.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "dataset_id": "orphan",
                "dataset_version": "v1",
                "display_name": "Orphan",
                "description": None,
                "images": [
                    {
                        "image_id": "x",
                        "raw_image_key": "x.png",
                        "ground_truth": 0,
                        "comments": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (root / "raw-images" / "orphan" / "v1").mkdir(parents=True)
    (root / "raw-images" / "orphan" / "v1" / "x.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    orphan_run = root / "runs-output" / "runs" / "run-orphan"
    orphan_run.mkdir(parents=True)
    (orphan_run / "run.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "run_id": "run-orphan",
                "dataset_id": "ds-a",
                "dataset_version": "v1",
                "model": {
                    "model_id": "m",
                    "model_name": "M",
                    "model_version": None,
                    "description": None,
                },
                "model_parameters": {},
                "preprocessing": {},
                "execution_description": None,
                "executed_at": None,
                "predictions_artifact": "predictions.json",
                "metrics_artifact": None,
                "evaluation_snapshot_artifact": None,
            }
        ),
        encoding="utf-8",
    )
    (orphan_run / "predictions.json").write_text(
        json.dumps({"schema_version": "1", "predictions": []}),
        encoding="utf-8",
    )

    with TestClient(create_app(make_settings(data_root=root))) as client:
        assert client.get("/api/datasets/orphan/versions/v1").status_code == 404
        assert client.get("/api/datasets/orphan/versions/v1/summary").status_code == 404
        assert client.get("/api/datasets/orphan/versions/v1/images/x/content").status_code == 404
        assert client.get("/api/runs/run-orphan").status_code == 404


def test_broken_catalog_dataset_reference_is_server_error(tmp_path: Path) -> None:
    root = tmp_path / "broken-ds"
    build_demo_tree(root)
    catalog_path = root / "runs-output" / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["datasets"].append({"dataset_id": "missing-ds", "dataset_version": "v1"})
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    with TestClient(create_app(make_settings(data_root=root))) as client:
        assert client.get("/api/datasets").status_code == 500


def test_broken_catalog_run_reference_is_server_error(tmp_path: Path) -> None:
    root = tmp_path / "broken-run"
    build_demo_tree(root)
    catalog_path = root / "runs-output" / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["runs"].append({"run_id": "missing-run"})
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    with TestClient(create_app(make_settings(data_root=root))) as client:
        assert client.get("/api/runs").status_code == 500


def test_duplicate_catalog_entries_are_server_error(tmp_path: Path) -> None:
    root = tmp_path / "dup-catalog"
    build_demo_tree(root)
    catalog_path = root / "runs-output" / "catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "datasets": [
                    {"dataset_id": "ds-a", "dataset_version": "v1"},
                    {"dataset_id": "ds-a", "dataset_version": "v1"},
                ],
                "runs": [],
            }
        ),
        encoding="utf-8",
    )
    with TestClient(create_app(make_settings(data_root=root))) as client:
        assert client.get("/api/datasets").status_code == 500


def test_published_run_with_unpublished_dataset_is_server_error(tmp_path: Path) -> None:
    root = tmp_path / "run-unpub-ds"
    build_demo_tree(root)
    run_path = root / "runs-output" / "runs" / "run-full" / "run.json"
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    payload["dataset_id"] = "not-published"
    payload["dataset_version"] = "v1"
    run_path.write_text(json.dumps(payload), encoding="utf-8")
    with TestClient(create_app(make_settings(data_root=root))) as client:
        assert client.get("/api/runs/run-full").status_code == 500


def test_zero_evaluated_metrics_are_invalid_artifact(tmp_path: Path) -> None:
    root = tmp_path / "zero-eval"
    build_demo_tree(root)
    metrics_path = root / "runs-output" / "runs" / "run-full" / "metrics.json"
    snapshot_path = root / "runs-output" / "runs" / "run-full" / "evaluation_snapshot.json"
    metrics_path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "accuracy": 1.0,
                "precision": 1.0,
                "recall": 1.0,
                "f1": 1.0,
                "confusion_matrix": None,
                "evaluated_image_count": 0,
            }
        ),
        encoding="utf-8",
    )
    snapshot_path.write_text(
        json.dumps({"schema_version": "1", "evaluated_images": []}),
        encoding="utf-8",
    )
    with TestClient(create_app(make_settings(data_root=root))) as client:
        response = client.get("/api/runs/run-full")
        assert response.status_code == 500
        # Runs without metrics remain valid.
        assert client.get("/api/runs/run-alt").status_code == 200
        assert client.get("/api/runs/run-alt").json()["metrics"]["available"] is False


def test_invalid_metric_score_is_server_error(tmp_path: Path) -> None:
    root = tmp_path / "bad-metric"
    build_demo_tree(root)
    metrics_path = root / "runs-output" / "runs" / "run-full" / "metrics.json"
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    payload["accuracy"] = True
    metrics_path.write_text(json.dumps(payload), encoding="utf-8")
    with TestClient(create_app(make_settings(data_root=root))) as client:
        assert client.get("/api/runs/run-full").status_code == 500
