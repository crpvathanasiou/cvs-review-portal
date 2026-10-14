"""Behavioral tests for comments-only Save and basic concurrency."""

from __future__ import annotations

import json
import multiprocessing
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from cvs_review_portal.domain.constants import MAX_COMMENT_LENGTH
from cvs_review_portal.main import create_app
from tests.fixture_trees import IsolatedSettings


def _review_url(image_id: str = "b") -> str:
    return f"/api/datasets/ds-a/versions/v1/images/{image_id}/review"


def _put(
    client: TestClient,
    *,
    image_id: str,
    comments: str,
    expected_revision: int,
) -> Any:
    return client.put(
        _review_url(image_id),
        json={"comments": comments, "expected_revision": expected_revision},
        headers={"Origin": "http://testserver"},
    )


def test_first_save_update_empty_and_reload(client: TestClient, data_root: Path) -> None:
    response = _put(client, image_id="b", comments="first", expected_revision=0)
    assert response.status_code == 200
    payload = response.json()
    assert payload["persisted_revision"] == 1
    assert payload["current"]["comments"] == "first"
    assert payload["current"]["ground_truth_override"] is None

    path = data_root / "reviews" / "ds-a" / "v1" / "b.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["schema_version"] == "1"
    assert stored["revision"] == 1
    assert stored["comments"] == "first"

    response = _put(client, image_id="b", comments="", expected_revision=1)
    assert response.status_code == 200
    assert response.json()["current"]["comments"] == ""
    assert response.json()["persisted_revision"] == 2

    got = client.get(_review_url("b"))
    assert got.status_code == 200
    assert got.json()["persisted_revision"] == 2
    assert got.json()["review"]["comments"] == ""

    summary = client.get("/api/datasets/ds-a/versions/v1/summary?run_id=run-full").json()
    assert summary["historical_metrics"]["available"] is True
    assert summary["historical_metrics"]["accuracy"] == 1.0


def test_cross_run_review_consistency(client: TestClient) -> None:
    _put(client, image_id="c", comments="shared-across-runs", expected_revision=0)
    run_full = client.get("/api/runs/run-full").json()
    run_alt = client.get("/api/runs/run-alt").json()
    comments_full = {
        row["image"]["image_id"]: row["image"]["effective_comments"] for row in run_full["images"]
    }
    comments_alt = {
        row["image"]["image_id"]: row["image"]["effective_comments"] for row in run_alt["images"]
    }
    assert comments_full["c"] == "shared-across-runs"
    assert comments_alt["c"] == "shared-across-runs"


def test_ground_truth_mutation_rejected_and_override_zero_preserved(
    client: TestClient, data_root: Path
) -> None:
    seeded = {
        "schema_version": "1",
        "dataset_id": "ds-a",
        "dataset_version": "v1",
        "image_id": "c",
        "ground_truth_override": 0,
        "comments": "seed",
        "revision": 1,
        "actor": "seeder",
        "updated_at": "2026-01-05T00:00:00+00:00",
    }
    path = data_root / "reviews" / "ds-a" / "v1" / "c.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(seeded) + "\n", encoding="utf-8")

    bad = client.put(
        _review_url("c"),
        json={
            "comments": "x",
            "expected_revision": 1,
            "ground_truth_override": 1,
        },
        headers={"Origin": "http://testserver"},
    )
    assert bad.status_code == 422

    ok = _put(client, image_id="c", comments="after", expected_revision=1)
    assert ok.status_code == 200
    assert ok.json()["current"]["ground_truth_override"] == 0
    assert ok.json()["current"]["comments"] == "after"

    detail = client.get("/api/datasets/ds-a/versions/v1").json()
    image_c = next(img for img in detail["images"] if img["image_id"] == "c")
    assert image_c["effective_ground_truth"] == 0
    assert image_c["original_ground_truth"] == 1


def test_legacy_v1_readable_and_save_preserves_override(
    client: TestClient, data_root: Path
) -> None:
    got = client.get(_review_url("a"))
    assert got.status_code == 200
    assert got.json()["persisted_revision"] == 1
    assert got.json()["review"]["comments"] == "reviewed-a"

    response = _put(client, image_id="a", comments="converted", expected_revision=1)
    assert response.status_code == 200
    assert response.json()["current"]["comments"] == "converted"
    assert response.json()["current"]["ground_truth_override"] == 1

    path = data_root / "reviews" / "ds-a" / "v1" / "a.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["schema_version"] == "1"
    assert stored["ground_truth_override"] == 1
    assert stored["comments"] == "converted"
    assert stored["revision"] == 2


def test_stale_revision_conflict(client: TestClient) -> None:
    _put(client, image_id="b", comments="one", expected_revision=0)
    conflict = _put(client, image_id="b", comments="two", expected_revision=0)
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["conflict_kind"] == "revision"


def test_comment_too_long_rejected(client: TestClient) -> None:
    response = _put(
        client,
        image_id="b",
        comments="x" * (MAX_COMMENT_LENGTH + 1),
        expected_revision=0,
    )
    assert response.status_code == 422


def test_metrics_unchanged_by_comment_save(client: TestClient) -> None:
    before = client.get("/api/datasets/ds-a/versions/v1/summary?run_id=run-full").json()
    _put(client, image_id="b", comments="metrics-should-stay", expected_revision=0)
    after = client.get("/api/datasets/ds-a/versions/v1/summary?run_id=run-full").json()
    assert after["historical_metrics"] == before["historical_metrics"]


def test_unauthorized_actor_forbidden(tmp_path: Path, data_root: Path) -> None:
    settings = IsolatedSettings(
        data_root=data_root,
        identity_mode="development",
        development_actor="outsider",
        allowed_actors="test-reviewer",
    )
    with TestClient(create_app(settings)) as client:
        response = client.put(
            _review_url("b"),
            json={"comments": "nope", "expected_revision": 0},
            headers={"Origin": "http://testserver"},
        )
        assert response.status_code == 403


def _worker_save(data_root: str, comments: str, expected: int, queue: Any) -> None:
    settings = IsolatedSettings(
        data_root=Path(data_root),
        identity_mode="development",
        development_actor="test-reviewer",
        allowed_actors="test-reviewer",
    )
    with TestClient(create_app(settings)) as client:
        response = client.put(
            _review_url("b"),
            json={"comments": comments, "expected_revision": expected},
            headers={"Origin": "http://testserver"},
        )
        queue.put((response.status_code, response.json()))


def test_cross_process_stale_writers_conflict(data_root: Path) -> None:
    settings = IsolatedSettings(
        data_root=data_root,
        identity_mode="development",
        development_actor="test-reviewer",
        allowed_actors="test-reviewer",
    )
    with TestClient(create_app(settings)) as client:
        primed = _put(client, image_id="b", comments="base", expected_revision=0)
        assert primed.status_code == 200

    ctx = multiprocessing.get_context("spawn")
    queue: Any = ctx.Queue()
    p1 = ctx.Process(target=_worker_save, args=(str(data_root), "writer-a", 1, queue))
    p2 = ctx.Process(target=_worker_save, args=(str(data_root), "writer-b", 1, queue))
    p1.start()
    p2.start()
    p1.join(timeout=30)
    p2.join(timeout=30)
    results = [queue.get(timeout=5), queue.get(timeout=5)]
    statuses = sorted(code for code, _ in results)
    assert statuses == [200, 409]
    winner = next(body for code, body in results if code == 200)
    assert winner["current"]["comments"] in {"writer-a", "writer-b"}
    path = data_root / "reviews" / "ds-a" / "v1" / "b.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["revision"] == 2
    assert stored["comments"] == winner["current"]["comments"]
