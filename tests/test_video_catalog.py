"""CSV video catalog + per-video JSON layout (DATASET_LAYOUT=video_catalog)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cvs_review_portal.application.ports import PortalDataStore
from cvs_review_portal.application.video_catalog import (
    expected_video_metadata_key,
    format_videos_csv,
    parse_videos_csv,
)
from cvs_review_portal.domain.errors import InvalidArtifactError, ResourceNotFoundError
from cvs_review_portal.domain.models import VideoCatalogEntry
from cvs_review_portal.infrastructure.azure_blob_store import AzureBlobPortalDataStore
from cvs_review_portal.infrastructure.local_store import LocalPortalDataStore
from cvs_review_portal.main import create_app
from tests.fixture_trees import make_settings, png_bytes

VIDEO_A = "v-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
VIDEO_B = "v-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
VIDEO_C = "v-cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"


def _prov(
    *,
    video_id: str,
    video_filename: str,
    segment_id: str,
    start: int,
    end: int,
    frame_index: int,
    display_id: str,
) -> dict[str, Any]:
    return {
        "video_id": video_id,
        "video_filename": video_filename,
        "segment_id": segment_id,
        "start_seconds": start,
        "end_seconds": end,
        "frame_index": frame_index,
        "timestamp": float(start),
        "display_id": display_id,
    }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _video_artifact(
    *,
    dataset_id: str,
    dataset_version: str,
    video_id: str,
    video_name: str,
    images: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "display_name": f"{dataset_id} {dataset_version}",
        "description": None,
        "video_id": video_id,
        "video_name": video_name,
        "images": images,
    }


def build_video_catalog_tree(root: Path) -> None:
    """Three videos on disk; CSV activates only A and B.

    Video A has two intervals: one Mixed (labels 0+1) and one uniform label 1.
    """
    raw = root / "raw-images" / "vc-mini" / "v1"
    raw.mkdir(parents=True)
    for name in ("a1.png", "a2.png", "a3.png", "b1.png", "c1.png"):
        (raw / name).write_bytes(png_bytes((1, 2, 3)))

    seg_a_mixed = f"{VIDEO_A}-s10-e20"
    seg_a_second = f"{VIDEO_A}-s25-e35"
    seg_b = f"{VIDEO_B}-s30-e40"
    seg_c = f"{VIDEO_C}-s50-e60"

    images_a = [
        {
            "image_id": "img-a1",
            "raw_image_key": "a1.png",
            "ground_truth": 0,
            "comments": None,
            "provenance": _prov(
                video_id=VIDEO_A,
                video_filename="video01.mp4",
                segment_id=seg_a_mixed,
                start=10,
                end=20,
                frame_index=1,
                display_id="vc-mini-v1-video01-s10-e20-f1",
            ),
        },
        {
            "image_id": "img-a2",
            "raw_image_key": "a2.png",
            "ground_truth": 1,
            "comments": None,
            "provenance": _prov(
                video_id=VIDEO_A,
                video_filename="video01.mp4",
                segment_id=seg_a_mixed,
                start=10,
                end=20,
                frame_index=2,
                display_id="vc-mini-v1-video01-s10-e20-f2",
            ),
        },
        {
            "image_id": "img-a3",
            "raw_image_key": "a3.png",
            "ground_truth": 1,
            "comments": None,
            "provenance": _prov(
                video_id=VIDEO_A,
                video_filename="video01.mp4",
                segment_id=seg_a_second,
                start=25,
                end=35,
                frame_index=1,
                display_id="vc-mini-v1-video01-s25-e35-f1",
            ),
        },
    ]
    images_b = [
        {
            "image_id": "img-b1",
            "raw_image_key": "b1.png",
            "ground_truth": 0,
            "comments": None,
            "provenance": _prov(
                video_id=VIDEO_B,
                video_filename="video02.mp4",
                segment_id=seg_b,
                start=30,
                end=40,
                frame_index=1,
                display_id="vc-mini-v1-video02-s30-e40-f1",
            ),
        },
    ]
    images_c = [
        {
            "image_id": "img-c1",
            "raw_image_key": "c1.png",
            "ground_truth": 0,
            "comments": None,
            "provenance": _prov(
                video_id=VIDEO_C,
                video_filename="video03.mp4",
                segment_id=seg_c,
                start=50,
                end=60,
                frame_index=1,
                display_id="vc-mini-v1-video03-s50-e60-f1",
            ),
        },
    ]

    base = root / "runs-output" / "datasets" / "vc-mini" / "v1"
    for video_id, video_name, images in (
        (VIDEO_A, "video01.mp4", images_a),
        (VIDEO_B, "video02.mp4", images_b),
        (VIDEO_C, "video03.mp4", images_c),
    ):
        _write_json(
            base / "videos" / f"{video_id}.json",
            _video_artifact(
                dataset_id="vc-mini",
                dataset_version="v1",
                video_id=video_id,
                video_name=video_name,
                images=images,
            ),
        )

    # Unlisted video C remains on disk; CSV activates only A and B.
    entries = [
        VideoCatalogEntry(
            video_id=VIDEO_A,
            video_name="video01.mp4",
            metadata_path=expected_video_metadata_key("vc-mini", "v1", VIDEO_A),
        ),
        VideoCatalogEntry(
            video_id=VIDEO_B,
            video_name="video02.mp4",
            metadata_path=expected_video_metadata_key("vc-mini", "v1", VIDEO_B),
        ),
    ]
    (base / "videos.csv").write_text(format_videos_csv(entries), encoding="utf-8")

    # Legacy dataset.json must not be used; leave a sentinel that would fail if read.
    (base / "dataset.json").write_text(
        '{"schema_version":"1","broken":true}\n',
        encoding="utf-8",
    )

    _write_json(
        root / "runs-output" / "catalog.json",
        {
            "schema_version": "1",
            "datasets": [{"dataset_id": "vc-mini", "dataset_version": "v1"}],
            "runs": [],
        },
    )


def _client(root: Path) -> TestClient:
    settings = make_settings(data_root=root, dataset_layout="video_catalog")
    return TestClient(create_app(settings))


def test_parse_header_only_csv_means_zero_videos() -> None:
    catalog = parse_videos_csv(
        "video_id,video_name,metadata_path\n",
        dataset_id="vc-mini",
        dataset_version="v1",
    )
    assert catalog.entries == []


def test_parse_duplicate_video_id_is_error() -> None:
    path = expected_video_metadata_key("vc-mini", "v1", VIDEO_A)
    text = (
        "video_id,video_name,metadata_path\n"
        f"{VIDEO_A},video01.mp4,{path}\n"
        f"{VIDEO_A},video01.mp4,{path}\n"
    )
    try:
        parse_videos_csv(text, dataset_id="vc-mini", dataset_version="v1")
        raise AssertionError("expected InvalidArtifactError")
    except InvalidArtifactError as exc:
        assert "duplicate" in str(exc).lower() or "Duplicate" in (exc.safe_context or "")


def test_csv_exposes_only_listed_videos(tmp_path: Path) -> None:
    root = tmp_path / "data"
    build_video_catalog_tree(root)
    with _client(root) as client:
        videos = client.get("/api/datasets/vc-mini/versions/v1/videos").json()
        assert videos["total"] == 2
        ids = {v["video_id"] for v in videos["videos"]}
        assert ids == {VIDEO_A, VIDEO_B}
        assert VIDEO_C not in ids

        browse = client.get("/api/datasets/vc-mini/versions/v1/browse").json()
        assert browse["dataset_layout"] == "video_catalog"
        assert browse["video_count"] == 2
        assert browse["image_count"] is None
        assert browse["interval_count"] is None


def test_bootstrap_does_not_load_video_json(tmp_path: Path) -> None:
    root = tmp_path / "data"
    build_video_catalog_tree(root)
    settings = make_settings(data_root=root, dataset_layout="video_catalog")
    app: FastAPI = create_app(settings)
    with TestClient(app) as client:
        store = cast(LocalPortalDataStore, cast(PortalDataStore, app.state.portal_store))
        with patch.object(store, "load_video", wraps=store.load_video) as spy_video:
            client.get("/api/datasets")
            client.get("/api/datasets/vc-mini/versions/v1/browse")
            client.get("/api/datasets/vc-mini/versions/v1/videos")
            assert spy_video.call_count == 0


def test_selecting_video_a_does_not_load_video_b(tmp_path: Path) -> None:
    root = tmp_path / "data"
    build_video_catalog_tree(root)
    settings = make_settings(data_root=root, dataset_layout="video_catalog")
    app: FastAPI = create_app(settings)
    with TestClient(app) as client:
        store = cast(LocalPortalDataStore, cast(PortalDataStore, app.state.portal_store))
        with patch.object(store, "load_video", wraps=store.load_video) as spy_video:
            resp = client.get(f"/api/datasets/vc-mini/versions/v1/intervals?video_id={VIDEO_A}")
            assert resp.status_code == 200
            body = resp.json()
            assert body["total"] == 2
            assert {item["video_id"] for item in body["intervals"]} == {VIDEO_A}
            loaded = {call.args[2] for call in spy_video.call_args_list}
            assert VIDEO_A in loaded
            assert VIDEO_B not in loaded
            assert VIDEO_C not in loaded


def test_remove_and_restore_csv_row_without_restart(tmp_path: Path) -> None:
    root = tmp_path / "data"
    build_video_catalog_tree(root)
    csv_path = root / "runs-output" / "datasets" / "vc-mini" / "v1" / "videos.csv"
    settings = make_settings(data_root=root, dataset_layout="video_catalog")
    with TestClient(create_app(settings)) as client:
        # Save a comment on video B while it is active.
        save = client.put(
            "/api/datasets/vc-mini/versions/v1/images/img-b1/review",
            json={"comments": "keep-me", "expected_revision": 0},
        )
        assert save.status_code == 200

        # Remove B from CSV (A only).
        only_a = format_videos_csv(
            [
                VideoCatalogEntry(
                    video_id=VIDEO_A,
                    video_name="video01.mp4",
                    metadata_path=expected_video_metadata_key("vc-mini", "v1", VIDEO_A),
                )
            ]
        )
        csv_path.write_text(only_a, encoding="utf-8")

        videos = client.get("/api/datasets/vc-mini/versions/v1/videos").json()
        assert videos["total"] == 1
        assert videos["videos"][0]["video_id"] == VIDEO_A

        missing = client.get("/api/datasets/vc-mini/versions/v1/images/img-b1/content")
        assert missing.status_code == 404

        save_blocked = client.put(
            "/api/datasets/vc-mini/versions/v1/images/img-b1/review",
            json={"comments": "should-fail", "expected_revision": 1},
        )
        assert save_blocked.status_code == 404

        # Restore B.
        both = format_videos_csv(
            [
                VideoCatalogEntry(
                    video_id=VIDEO_A,
                    video_name="video01.mp4",
                    metadata_path=expected_video_metadata_key("vc-mini", "v1", VIDEO_A),
                ),
                VideoCatalogEntry(
                    video_id=VIDEO_B,
                    video_name="video02.mp4",
                    metadata_path=expected_video_metadata_key("vc-mini", "v1", VIDEO_B),
                ),
            ]
        )
        csv_path.write_text(both, encoding="utf-8")

        review = client.get("/api/datasets/vc-mini/versions/v1/images/img-b1/review")
        assert review.status_code == 200
        assert review.json()["review"]["comments"] == "keep-me"

        content = client.get("/api/datasets/vc-mini/versions/v1/images/img-b1/content")
        assert content.status_code == 200


def test_content_and_save_do_not_read_legacy_dataset_json(tmp_path: Path) -> None:
    root = tmp_path / "data"
    build_video_catalog_tree(root)
    settings = make_settings(data_root=root, dataset_layout="video_catalog")
    app: FastAPI = create_app(settings)
    with TestClient(app) as client:
        store = cast(LocalPortalDataStore, cast(PortalDataStore, app.state.portal_store))
        with patch.object(store, "load_dataset", wraps=store.load_dataset) as spy_ds:
            content = client.get("/api/datasets/vc-mini/versions/v1/images/img-a1/content")
            assert content.status_code == 200
            save = client.put(
                "/api/datasets/vc-mini/versions/v1/images/img-a1/review",
                json={"comments": "x", "expected_revision": 0},
            )
            assert save.status_code == 200
            assert spy_ds.call_count == 0


def test_missing_active_video_json_is_controlled_error(tmp_path: Path) -> None:
    root = tmp_path / "data"
    build_video_catalog_tree(root)
    missing = root / "runs-output" / "datasets" / "vc-mini" / "v1" / "videos" / f"{VIDEO_B}.json"
    missing.unlink()
    with _client(root) as client:
        resp = client.get(f"/api/datasets/vc-mini/versions/v1/intervals?video_id={VIDEO_B}")
        assert resp.status_code == 500
        detail = resp.json()["detail"]
        assert "missing" in detail["message"].lower() or "video" in detail["message"].lower()


def test_intervals_without_video_id_require_selection(tmp_path: Path) -> None:
    root = tmp_path / "data"
    build_video_catalog_tree(root)
    with _client(root) as client:
        resp = client.get("/api/datasets/vc-mini/versions/v1/intervals")
        assert resp.status_code == 404


def test_video_b_frame_ops_do_not_load_video_a_even_cold_cache(tmp_path: Path) -> None:
    """With video_id hint, content/view/review/Save resolve only within video B."""
    root = tmp_path / "data"
    build_video_catalog_tree(root)
    settings = make_settings(data_root=root, dataset_layout="video_catalog")
    app: FastAPI = create_app(settings)
    with TestClient(app) as client:
        # Fresh app store starts with an empty video cache (cold-cache case).
        store = cast(LocalPortalDataStore, cast(PortalDataStore, app.state.portal_store))
        with patch.object(store, "load_video", wraps=store.load_video) as spy_video:
            params = {"video_id": VIDEO_B}
            assert (
                client.get(
                    "/api/datasets/vc-mini/versions/v1/images/img-b1/content",
                    params=params,
                ).status_code
                == 200
            )
            assert (
                client.get(
                    "/api/datasets/vc-mini/versions/v1/images/img-b1/view",
                    params=params,
                ).status_code
                == 200
            )
            assert (
                client.get(
                    "/api/datasets/vc-mini/versions/v1/images/img-b1/review",
                    params=params,
                ).status_code
                == 200
            )
            assert (
                client.put(
                    "/api/datasets/vc-mini/versions/v1/images/img-b1/review",
                    params=params,
                    json={"comments": "b-only", "expected_revision": 0},
                ).status_code
                == 200
            )
            loaded = {call.args[2] for call in spy_video.call_args_list}
            assert VIDEO_B in loaded
            assert VIDEO_A not in loaded
            assert VIDEO_C not in loaded


def test_removed_csv_row_blocks_requests_even_with_video_id_hint(tmp_path: Path) -> None:
    root = tmp_path / "data"
    build_video_catalog_tree(root)
    csv_path = root / "runs-output" / "datasets" / "vc-mini" / "v1" / "videos.csv"
    csv_path.write_text(
        format_videos_csv(
            [
                VideoCatalogEntry(
                    video_id=VIDEO_A,
                    video_name="video01.mp4",
                    metadata_path=expected_video_metadata_key("vc-mini", "v1", VIDEO_A),
                )
            ]
        ),
        encoding="utf-8",
    )
    with _client(root) as client:
        params = {"video_id": VIDEO_B}
        assert (
            client.get(
                "/api/datasets/vc-mini/versions/v1/images/img-b1/content",
                params=params,
            ).status_code
            == 404
        )
        assert (
            client.put(
                "/api/datasets/vc-mini/versions/v1/images/img-b1/review",
                params=params,
                json={"comments": "nope", "expected_revision": 0},
            ).status_code
            == 404
        )


def test_video_preview_loads_only_requested_video(tmp_path: Path) -> None:
    root = tmp_path / "data"
    build_video_catalog_tree(root)
    settings = make_settings(data_root=root, dataset_layout="video_catalog")
    app: FastAPI = create_app(settings)
    with TestClient(app) as client:
        store = cast(LocalPortalDataStore, cast(PortalDataStore, app.state.portal_store))
        with patch.object(store, "load_video", wraps=store.load_video) as spy_video:
            resp = client.get(f"/api/datasets/vc-mini/versions/v1/videos/{VIDEO_B}/preview")
            assert resp.status_code == 200
            body = resp.json()
            assert body["video_label"] == "Video 02"
            assert body["first_image_id"] == "img-b1"
            loaded = {call.args[2] for call in spy_video.call_args_list}
            assert loaded == {VIDEO_B}


def test_summary_covers_active_videos_only(tmp_path: Path) -> None:
    root = tmp_path / "data"
    build_video_catalog_tree(root)
    with _client(root) as client:
        summary = client.get("/api/datasets/vc-mini/versions/v1/summary")
        assert summary.status_code == 200
        body = summary.json()
        # A has 3 images, B has 1; C is unlisted.
        assert body["total_images"] == 4
        assert body["effective_ground_truth"]["label_0"] == 2
        assert body["effective_ground_truth"]["label_1"] == 2


def test_summary_interval_rows_multi_interval_and_mixed(tmp_path: Path) -> None:
    """One video with multiple intervals yields separate rows; Mixed is explicit."""
    root = tmp_path / "data"
    build_video_catalog_tree(root)
    with _client(root) as client:
        body = client.get("/api/datasets/vc-mini/versions/v1/summary").json()
        rows = body["intervals"]
        assert len(rows) == 3
        by_segment = {row["segment_id"]: row for row in rows}

        mixed_seg = f"{VIDEO_A}-s10-e20"
        second_seg = f"{VIDEO_A}-s25-e35"
        b_seg = f"{VIDEO_B}-s30-e40"

        assert by_segment[mixed_seg]["video_label"] == "Video 01"
        assert by_segment[mixed_seg]["time_interval"] == "00:10–00:20"
        assert by_segment[mixed_seg]["ground_truth"] == "Mixed"
        assert by_segment[mixed_seg]["image_count"] == 2

        assert by_segment[second_seg]["video_label"] == "Video 01"
        assert by_segment[second_seg]["time_interval"] == "00:25–00:35"
        assert by_segment[second_seg]["ground_truth"] == 1
        assert by_segment[second_seg]["image_count"] == 1

        assert by_segment[b_seg]["video_label"] == "Video 02"
        assert by_segment[b_seg]["ground_truth"] == 0

        # Ordered by video name, then start/end/segment_id.
        assert [row["segment_id"] for row in rows] == [mixed_seg, second_seg, b_seg]


def test_summary_interval_rows_exclude_removed_csv_video(tmp_path: Path) -> None:
    root = tmp_path / "data"
    build_video_catalog_tree(root)
    csv_path = root / "runs-output" / "datasets" / "vc-mini" / "v1" / "videos.csv"
    csv_path.write_text(
        format_videos_csv(
            [
                VideoCatalogEntry(
                    video_id=VIDEO_A,
                    video_name="video01.mp4",
                    metadata_path=expected_video_metadata_key("vc-mini", "v1", VIDEO_A),
                )
            ]
        ),
        encoding="utf-8",
    )
    with _client(root) as client:
        body = client.get("/api/datasets/vc-mini/versions/v1/summary").json()
        video_ids = {row["video_id"] for row in body["intervals"]}
        assert VIDEO_A in video_ids
        assert VIDEO_B not in video_ids
        assert VIDEO_C not in video_ids
        assert body["total_images"] == 3
        assert len(body["intervals"]) == 2


def test_typing_style_csv_list_does_not_scan_video_json(tmp_path: Path) -> None:
    """Partial video-name filter uses GET /videos only (no load_video / JSON scan)."""
    root = tmp_path / "data"
    build_video_catalog_tree(root)
    settings = make_settings(data_root=root, dataset_layout="video_catalog")
    app: FastAPI = create_app(settings)
    with TestClient(app) as client:
        store = cast(LocalPortalDataStore, cast(PortalDataStore, app.state.portal_store))
        with patch.object(store, "load_video", wraps=store.load_video) as spy_video:
            listed = client.get("/api/datasets/vc-mini/versions/v1/videos")
            assert listed.status_code == 200
            names = [v["video_name"] for v in listed.json()["videos"]]
            # Client-side CSV filter equivalent of typing "video0".
            filtered = [n for n in names if "video0" in n.lower()]
            assert filtered == ["video01.mp4", "video02.mp4"]
            assert spy_video.call_count == 0


def test_explicit_image_search_still_scans_active_videos(tmp_path: Path) -> None:
    root = tmp_path / "data"
    build_video_catalog_tree(root)
    with _client(root) as client:
        resp = client.get(
            "/api/datasets/vc-mini/versions/v1/intervals/search",
            params={"q": "img-b1", "offset": 0, "limit": 24},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["match_kind"] == "image"
        assert body["total"] >= 1
        hit = body["hits"][0]
        assert hit["target_image_id"] == "img-b1"
        assert hit["interval"]["video_id"] == VIDEO_B


def test_azure_etag_checked_before_body_download() -> None:
    """Unchanged ETag reuses cache without a second body download; ETag change reloads."""
    store = AzureBlobPortalDataStore(
        account_url="https://example.blob.core.windows.net",
        container_name="portal",
        credential=object(),
        dataset_layout="video_catalog",
    )
    entries = [
        VideoCatalogEntry(
            video_id=VIDEO_A,
            video_name="video01.mp4",
            metadata_path=expected_video_metadata_key("vc-mini", "v1", VIDEO_A),
        )
    ]
    catalog = parse_videos_csv(
        format_videos_csv(entries),
        dataset_id="vc-mini",
        dataset_version="v1",
    )
    video_payload = _video_artifact(
        dataset_id="vc-mini",
        dataset_version="v1",
        video_id=VIDEO_A,
        video_name="video01.mp4",
        images=[
            {
                "image_id": "img-a1",
                "raw_image_key": "a1.png",
                "ground_truth": 0,
                "comments": None,
                "provenance": _prov(
                    video_id=VIDEO_A,
                    video_filename="video01.mp4",
                    segment_id=f"{VIDEO_A}-s10-e20",
                    start=10,
                    end=20,
                    frame_index=1,
                    display_id="vc-mini-v1-video01-s10-e20-f1",
                ),
            }
        ],
    )
    raw = json.dumps(video_payload).encode("utf-8")

    blob = MagicMock()
    props_v1 = type("P", (), {"etag": '"e1"', "size": len(raw)})()
    props_v2 = type("P", (), {"etag": '"e2"', "size": len(raw)})()
    blob.get_blob_properties.side_effect = [props_v1, props_v1, props_v2]
    download = MagicMock()
    download.readall.return_value = raw
    blob.download_blob.return_value = download

    with patch.object(store, "ensure_available", return_value=None):
        with patch.object(store, "load_video_catalog", return_value=catalog):
            with patch.object(store, "_blob", return_value=blob):
                first = store.load_video("vc-mini", "v1", VIDEO_A)
                second = store.load_video("vc-mini", "v1", VIDEO_A)
                assert first.video_id == VIDEO_A
                assert second is first or second.video_id == VIDEO_A
                assert blob.download_blob.call_count == 1
                assert blob.get_blob_properties.call_count == 2

                third = store.load_video("vc-mini", "v1", VIDEO_A)
                assert third.video_id == VIDEO_A
                assert blob.download_blob.call_count == 2
                assert blob.get_blob_properties.call_count == 3

        with patch.object(store, "load_video_catalog", return_value=catalog):
            try:
                store.load_video("vc-mini", "v1", VIDEO_B)
                raise AssertionError("expected ResourceNotFoundError")
            except ResourceNotFoundError as exc:
                assert "not in the active" in str(exc)
