"""Step 2B: interval grouping, search, frame reads, and browse bootstrap."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from fastapi.testclient import TestClient

from cvs_review_portal.application.interval_index import (
    build_interval_index,
    format_clock,
    interval_title,
    search_intervals,
    video_label_from_filename,
)
from cvs_review_portal.application.ports import PortalDataStore
from cvs_review_portal.domain.models import DatasetImage, DatasetVersion, ImageProvenance
from cvs_review_portal.domain.review_document import LoadedReview
from cvs_review_portal.main import create_app
from tests.fixture_trees import make_settings, png_bytes


def _prov(
    *,
    video_id: str,
    video_filename: str,
    segment_id: str,
    start: int,
    end: int,
    frame_index: int,
    display_id: str,
    timestamp: float | None = None,
) -> dict[str, Any]:
    return {
        "video_id": video_id,
        "video_filename": video_filename,
        "segment_id": segment_id,
        "start_seconds": start,
        "end_seconds": end,
        "frame_index": frame_index,
        "timestamp": float(start if timestamp is None else timestamp),
        "display_id": display_id,
    }


def build_provenance_tree(root: Path) -> None:
    """Two videos, three intervals (including an overlapping pair), no runs."""
    raw = root / "raw-images" / "cholec-mini" / "v1"
    raw.mkdir(parents=True)
    for name in ("f1.png", "f2.png", "f3.png", "f4.png", "f5.png", "f6.png"):
        (raw / name).write_bytes(png_bytes((10, 20, 30)))

    video_a = "v-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    video_b = "v-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    seg_a1 = f"{video_a}-s1226-e1256"
    seg_a2 = f"{video_a}-s1300-e1320"
    seg_b1 = f"{video_b}-s100-e130"
    # Overlapping interval on video A reuses a source-like frame index with a new image_id.
    seg_a_overlap = f"{video_a}-s1230-e1240"

    images = [
        {
            "image_id": "img-a1-f10",
            "raw_image_key": "f1.png",
            "ground_truth": 0,
            "comments": None,
            "provenance": _prov(
                video_id=video_a,
                video_filename="video02.mp4",
                segment_id=seg_a1,
                start=1226,
                end=1256,
                frame_index=10,
                display_id="cholec-mini-v1-video02-s1226-e1256-f10",
            ),
        },
        {
            "image_id": "img-a1-f2",
            "raw_image_key": "f2.png",
            "ground_truth": 0,
            "comments": "mid",
            "provenance": _prov(
                video_id=video_a,
                video_filename="video02.mp4",
                segment_id=seg_a1,
                start=1226,
                end=1256,
                frame_index=2,
                display_id="cholec-mini-v1-video02-s1226-e1256-f2",
            ),
        },
        {
            "image_id": "img-a1-f20",
            "raw_image_key": "f3.png",
            "ground_truth": 1,
            "comments": None,
            "provenance": _prov(
                video_id=video_a,
                video_filename="video02.mp4",
                segment_id=seg_a1,
                start=1226,
                end=1256,
                frame_index=20,
                display_id="cholec-mini-v1-video02-s1226-e1256-f20",
            ),
        },
        {
            "image_id": "img-a2-f1",
            "raw_image_key": "f4.png",
            "ground_truth": 0,
            "comments": None,
            "provenance": _prov(
                video_id=video_a,
                video_filename="video02.mp4",
                segment_id=seg_a2,
                start=1300,
                end=1320,
                frame_index=1,
                display_id="cholec-mini-v1-video02-s1300-e1320-f1",
            ),
        },
        {
            "image_id": "img-overlap-f15",
            "raw_image_key": "f5.png",
            "ground_truth": 1,
            "comments": "overlap-label",
            "provenance": _prov(
                video_id=video_a,
                video_filename="video02.mp4",
                segment_id=seg_a_overlap,
                start=1230,
                end=1240,
                frame_index=15,
                display_id="cholec-mini-v1-video02-s1230-e1240-f15",
            ),
        },
        {
            "image_id": "img-b1-f1",
            "raw_image_key": "f6.png",
            "ground_truth": 0,
            "comments": None,
            "provenance": _prov(
                video_id=video_b,
                video_filename="video70.mp4",
                segment_id=seg_b1,
                start=100,
                end=130,
                frame_index=1,
                display_id="cholec-mini-v1-video70-s100-e130-f1",
            ),
        },
    ]

    (root / "runs-output").mkdir(parents=True)
    catalog = {
        "schema_version": "1",
        "datasets": [{"dataset_id": "cholec-mini", "dataset_version": "v1"}],
        "runs": [],
    }
    (root / "runs-output" / "catalog.json").write_text(
        json.dumps(catalog, indent=2) + "\n", encoding="utf-8"
    )
    dataset_path = root / "runs-output" / "datasets" / "cholec-mini" / "v1" / "dataset.json"
    dataset_path.parent.mkdir(parents=True)
    dataset_path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "dataset_id": "cholec-mini",
                "dataset_version": "v1",
                "display_name": "Cholec80",
                "description": "Synthetic provenance fixture.",
                "images": images,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _dataset_from_tree(root: Path) -> DatasetVersion:
    payload = json.loads(
        (root / "runs-output" / "datasets" / "cholec-mini" / "v1" / "dataset.json").read_text(
            encoding="utf-8"
        )
    )
    return DatasetVersion.model_validate(payload)


def test_format_clock_and_titles() -> None:
    assert format_clock(1226) == "20:26"
    assert format_clock(1256) == "20:56"
    assert video_label_from_filename("video02.mp4") == "Video 02"
    record_images = [
        DatasetImage(
            image_id="x",
            raw_image_key="a.png",
            ground_truth=0,
            provenance=ImageProvenance(
                video_id="v-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                video_filename="video02.mp4",
                segment_id=(
                    "v-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                    "-s1226-e1256"
                ),
                start_seconds=1226,
                end_seconds=1256,
                frame_index=1,
                timestamp=1226.0,
                display_id="disp-x",
            ),
        )
    ]
    dataset = DatasetVersion(
        schema_version="1",
        dataset_id="cholec-mini",
        dataset_version="v1",
        display_name="Cholec80",
        description=None,
        images=record_images,
    )
    records = build_interval_index(dataset)
    assert interval_title("Cholec80", records[0]) == "Cholec80 · Video 02 · 20:26–20:56"


def test_interval_grouping_and_numeric_ordering(tmp_path: Path) -> None:
    root = tmp_path / "prov"
    build_provenance_tree(root)
    dataset = _dataset_from_tree(root)
    records = build_interval_index(dataset)
    assert [r.segment_id for r in records] == sorted(
        [r.segment_id for r in records],
        key=lambda sid: next(x for x in records if x.segment_id == sid).start_seconds,
    )
    # Chronological by start/end then segment_id
    starts = [(r.start_seconds, r.end_seconds, r.segment_id) for r in records]
    assert starts == sorted(starts)

    first = next(r for r in records if r.start_seconds == 1226)
    assert [f.image_id for f in first.frames] == ["img-a1-f2", "img-a1-f10", "img-a1-f20"]
    assert [f.frame_index for f in first.frames] == [2, 10, 20]

    # Overlapping interval remains a separate card/record
    assert len(records) == 4


def test_video_search_returns_all_intervals(tmp_path: Path) -> None:
    root = tmp_path / "prov"
    build_provenance_tree(root)
    records = build_interval_index(_dataset_from_tree(root))
    kind, matched, hit = search_intervals(records, "video02")
    assert kind == "video"
    assert hit is None
    assert len(matched) == 3
    assert all(r.video_filename == "video02.mp4" for r in matched)
    kind2, matched2, _ = search_intervals(records, "VIDEO02.MP4")
    assert kind2 == "video"
    assert [r.segment_id for r in matched2] == [r.segment_id for r in matched]


def test_image_id_and_display_id_locate_exact_frame(tmp_path: Path) -> None:
    root = tmp_path / "prov"
    build_provenance_tree(root)
    records = build_interval_index(_dataset_from_tree(root))
    kind, matched, hit = search_intervals(records, "img-a1-f10")
    assert kind == "image"
    assert hit is not None
    assert matched[0].segment_id == hit[0].segment_id
    assert hit[0].frames[hit[1]].image_id == "img-a1-f10"
    assert hit[1] == 1  # after numeric frame ordering (f2, f10, f20)

    kind_d, matched_d, hit_d = search_intervals(records, "cholec-mini-v1-video02-s1226-e1256-f20")
    assert kind_d == "image"
    assert hit_d is not None
    assert hit_d[0].frames[hit_d[1]].image_id == "img-a1-f20"
    assert matched_d[0].segment_id == hit_d[0].segment_id


def test_browse_api_and_search_without_review_reads(tmp_path: Path) -> None:
    from fastapi import FastAPI

    root = tmp_path / "prov"
    build_provenance_tree(root)
    settings = make_settings(data_root=root)
    review_calls: list[str] = []

    app: FastAPI = create_app(settings)

    with TestClient(app) as client:
        store = cast(PortalDataStore, app.state.portal_store)
        original = store.load_review

        def counting_load_review(
            dataset_id: str, dataset_version: str, image_id: str
        ) -> LoadedReview | None:
            review_calls.append(image_id)
            return original(dataset_id, dataset_version, image_id)

        with patch.object(store, "load_review", side_effect=counting_load_review):
            browse = client.get("/api/datasets/cholec-mini/versions/v1/browse")
            assert browse.status_code == 200
            body = browse.json()
            assert body["browse_mode"] == "interval"
            assert body["interval_count"] == 4
            assert body["image_count"] == 6

            listed = client.get(
                "/api/datasets/cholec-mini/versions/v1/intervals",
                params={"offset": 0, "limit": 24},
            )
            assert listed.status_code == 200
            assert listed.json()["total"] == 4

            search = client.get(
                "/api/datasets/cholec-mini/versions/v1/intervals/search",
                params={"q": "video02"},
            )
            assert search.status_code == 200
            search_body = search.json()
            assert search_body["match_kind"] == "video"
            assert search_body["total"] == 3

            image_search = client.get(
                "/api/datasets/cholec-mini/versions/v1/intervals/search",
                params={"q": "img-a1-f10"},
            )
            assert image_search.status_code == 200
            image_body = image_search.json()
            assert image_body["match_kind"] == "image"
            assert image_body["hits"][0]["target_image_id"] == "img-a1-f10"
            assert image_body["hits"][0]["target_frame_index"] == 2

            seg = listed.json()["intervals"][0]["segment_id"]
            frames = client.get(f"/api/datasets/cholec-mini/versions/v1/intervals/{seg}/frames")
            assert frames.status_code == 200
            assert frames.json()["image_count"] == len(frames.json()["frames"])

        assert review_calls == []

        # Single-frame effective view reads exactly one review.
        review_calls.clear()
        with patch.object(store, "load_review", side_effect=counting_load_review):
            view = client.get("/api/datasets/cholec-mini/versions/v1/images/img-a1-f10/view")
            assert view.status_code == 200
            assert view.json()["image"]["image_id"] == "img-a1-f10"
            assert view.json()["position"] == 2
            assert view.json()["prediction"] is None
        assert review_calls == ["img-a1-f10"]


def test_datasets_without_provenance_remain_image_browse(client: TestClient) -> None:
    browse = client.get("/api/datasets/ds-a/versions/v1/browse")
    assert browse.status_code == 200
    assert browse.json()["browse_mode"] == "image"
    assert browse.json()["interval_count"] == 0

    detail = client.get("/api/datasets/ds-a/versions/v1")
    assert detail.status_code == 200
    assert len(detail.json()["images"]) == 3

    intervals = client.get("/api/datasets/ds-a/versions/v1/intervals")
    assert intervals.status_code == 200
    assert intervals.json()["total"] == 0


def test_frame_view_and_run_overview_preserve_existing_get_run(
    client: TestClient, data_root: Path
) -> None:
    _ = data_root
    full = client.get("/api/runs/run-full")
    assert full.status_code == 200
    assert "images" in full.json()

    overview = client.get("/api/runs/run-full/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert body["run_id"] == "run-full"
    assert "images" not in body
    assert body["metrics"]["available"] is True

    view = client.get(
        "/api/datasets/ds-a/versions/v1/images/a/view",
        params={"run_id": "run-full"},
    )
    assert view.status_code == 200
    assert view.json()["image"]["effective_ground_truth"] == 1
    assert view.json()["prediction"]["available"] is True


def test_interval_navigation_boundaries_via_frames_api(tmp_path: Path) -> None:
    root = tmp_path / "prov"
    build_provenance_tree(root)
    with TestClient(create_app(make_settings(data_root=root))) as client:
        search = client.get(
            "/api/datasets/cholec-mini/versions/v1/intervals/search",
            params={"q": "img-a1-f2"},
        ).json()
        segment_id = search["hits"][0]["interval"]["segment_id"]
        frames = client.get(
            f"/api/datasets/cholec-mini/versions/v1/intervals/{segment_id}/frames"
        ).json()
        assert frames["frames"][0]["position"] == 1
        assert frames["frames"][-1]["position"] == frames["image_count"]
        assert frames["frames"][0]["image_id"] == "img-a1-f2"
        # No wraparound semantics: first/last are endpoints.
        assert frames["frames"][0]["position"] != frames["frames"][-1]["position"]


def test_ui_contracts_mention_interval_controls() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "cvs_review_portal" / "web"
    js = (root / "app.js").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    assert "loadIntervalFrame" in js
    assert "addOrFocusInterval" in js
    assert "isIntervalBrowse" in js
    assert "markSummaryStale" in js
    assert "CvsIntervalBrowseLogic" in js
    assert "updateIntervalCardDom" in js
    assert "Previous" in js and "Next" in js
    assert 'id="picker-add-all-btn"' in html
    assert "Load effective summary" in html
    assert "register_interval_browse_logic.mjs" in html
    logic = (root / "interval_browse_logic.mjs").read_text(encoding="utf-8")
    assert "reconcileFrameImage" in logic
    assert "intervalFrameLoadStillValid" in logic
