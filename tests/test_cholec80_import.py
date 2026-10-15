"""Synthetic fixtures for the Cholec80 portal dataset importer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from openpyxl import Workbook
from pydantic import ValidationError

from cvs_review_portal.domain.models import Catalog, DatasetImage, DatasetVersion, ImageProvenance
from cvs_review_portal.importers.cholec80 import (
    Cholec80ImportError,
    prepare_cholec80_dataset,
)
from tests.fixture_trees import png_bytes

VIDEO_ID = "v-aaaa"
SEG_A = f"{VIDEO_ID}-s1226-e1256"
SEG_B = f"{VIDEO_ID}-s1240-e1260"
SKIPPED_VIDEO_ID = "v-skipped70"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_xlsx(path: Path, rows: list[tuple[object, ...]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(
        [
            "video",
            "critical_view",
            "initial_minute",
            "initial_second",
            "final_minute",
            "final_second",
            "two_structures",
            "cystic_plate",
            "hepatocystic_triangle",
            "Total",
        ]
    )
    for row in rows:
        sheet.append(list(row))
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def _manifest_line(
    *,
    image_id: str,
    video_id: str,
    segment_id: str,
    frame_index: int,
    timestamp: float,
    path: str,
    video_filename: str,
    start_seconds: int,
    end_seconds: int,
    excel_row: int,
) -> str:
    return json.dumps(
        {
            "image_id": image_id,
            "video_id": video_id,
            "segment_id": segment_id,
            "frame_index": frame_index,
            "timestamp": timestamp,
            "path": path,
            "video_filename": video_filename,
            "workbook_sheet": "intervals",
            "excel_row": excel_row,
            "start_seconds": start_seconds,
            "end_seconds": end_seconds,
            "image_format": "jpeg",
            "width": 8,
            "height": 8,
        }
    )


def _default_run_payload() -> dict[str, object]:
    return {
        "schema_version": "2",
        "pipeline_name": "frame_extraction",
        "status": "partial",
        "video_jobs": {"total": 2, "processed": 2, "succeeded": 1, "skipped": 1},
        "counts": {
            "segments_planned": 2,
            "segments_completed": 2,
            "images_exported": 3,
        },
        "videos": [
            {
                "video_id": VIDEO_ID,
                "source_filenames": ["video02.mp4"],
                "content_sha256": "aaaa",
                "width": 8,
                "height": 8,
                "timeline_origin": 0.0,
                "usable_video_end": 2000.0,
            }
        ],
        "segments": [
            {
                "segment_id": SEG_A,
                "video_id": VIDEO_ID,
                "video_filename": "video02.mp4",
                "excel_row": 999,
                "start_seconds": 1226,
                "end_seconds": 1256,
                "requested_count": 2,
                "exported_count": 2,
            },
            {
                "segment_id": SEG_B,
                "video_id": VIDEO_ID,
                "video_filename": "video02.mp4",
                "excel_row": 1000,
                "start_seconds": 1240,
                "end_seconds": 1260,
                "requested_count": 1,
                "exported_count": 1,
            },
        ],
        "jobs": [
            {
                "source_filename": "video02.mp4",
                "status": "succeeded",
                "video_id": VIDEO_ID,
                "segments_completed": 2,
                "images_exported": 3,
                "issues": [],
            },
            {
                "source_filename": "video70.mp4",
                "status": "skipped",
                "video_id": SKIPPED_VIDEO_ID,
                "issues": [{"code": "interval_out_of_bounds", "message": "skipped"}],
            },
        ],
    }


def _build_mini_export(root: Path) -> None:
    """Build a tiny export with different excel_row numbers than the GT workbook."""
    images_dir = root / "images" / VIDEO_ID
    (images_dir / SEG_A).mkdir(parents=True)
    (images_dir / SEG_B).mkdir(parents=True)
    (images_dir / SEG_A / "f30650.jpg").write_bytes(png_bytes((1, 2, 3)))
    (images_dir / SEG_A / "f30675.jpg").write_bytes(png_bytes((4, 5, 6)))
    (images_dir / SEG_B / "f30650.jpg").write_bytes(png_bytes((7, 8, 9)))

    lines = [
        _manifest_line(
            image_id=f"{SEG_A}-f30650",
            video_id=VIDEO_ID,
            segment_id=SEG_A,
            frame_index=30650,
            timestamp=1226.0,
            path=f"images/{VIDEO_ID}/{SEG_A}/f30650.jpg",
            video_filename="video02.mp4",
            start_seconds=1226,
            end_seconds=1256,
            excel_row=999,
        ),
        _manifest_line(
            image_id=f"{SEG_A}-f30675",
            video_id=VIDEO_ID,
            segment_id=SEG_A,
            frame_index=30675,
            timestamp=1227.0,
            path=f"images/{VIDEO_ID}/{SEG_A}/f30675.jpg",
            video_filename="video02.mp4",
            start_seconds=1226,
            end_seconds=1256,
            excel_row=999,
        ),
        _manifest_line(
            image_id=f"{SEG_B}-f30650",
            video_id=VIDEO_ID,
            segment_id=SEG_B,
            frame_index=30650,
            timestamp=1240.0,
            path=f"images/{VIDEO_ID}/{SEG_B}/f30650.jpg",
            video_filename="video02.mp4",
            start_seconds=1240,
            end_seconds=1260,
            excel_row=1000,
        ),
    ]
    (root / "manifest.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_json(root / "run.json", _default_run_payload())


def _matching_gt_rows() -> list[tuple[object, ...]]:
    # Required: video=2 @ 1226-1256 (cv=0), 1240-1260 (cv=1)
    # Unused invalid video03-style interval (end < start)
    # Unused video06-style duplicate key
    # Extra unused video 99
    return [
        (2, 0, 20, 26, 20, 56, 0, 0, 0, 0),
        (2, 1, 20, 40, 21, 0, 2, 1, 1, 4),
        (3, 0, 61, 46, 60, 0, 0, 0, 0, 0),  # 3706 > 3600
        (6, 0, 13, 1, 13, 35, 0, 0, 0, 0),  # 781-815
        (6, 1, 13, 1, 13, 35, 0, 0, 0, 0),  # duplicate unused key
        (99, 0, 0, 0, 0, 10, 0, 0, 0, 0),
    ]


def test_existing_dataset_image_without_provenance_remains_valid() -> None:
    image = DatasetImage(
        image_id="img-001",
        raw_image_key="img-001.png",
        ground_truth=0,
        comments="ok",
    )
    assert image.provenance is None


def test_label_join_ignores_excel_row_and_keeps_overlapping_segments(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    _build_mini_export(export_root)
    xlsx = tmp_path / "gt.xlsx"
    _write_xlsx(xlsx, _matching_gt_rows())
    destination = tmp_path / "portal-data"

    report = prepare_cholec80_dataset(
        export_root=export_root,
        ground_truth_xlsx=xlsx,
        destination=destination,
        dataset_id="cholec80",
        dataset_version="v1",
        dry_run=False,
    )
    assert report.image_count == 3
    assert report.segment_count == 2
    assert report.ground_truth_segments == {0: 1, 1: 1}
    assert report.ground_truth_images == {0: 2, 1: 1}
    assert report.skipped_jobs == ["video70.mp4 (interval_out_of_bounds)"]
    assert report.unused_xlsx_rows == 4
    assert len(report.repeated_frame_label_conflicts) == 1

    dataset = DatasetVersion.model_validate_json(
        (destination / "runs-output" / "datasets" / "cholec80" / "v1" / "dataset.json").read_text(
            encoding="utf-8"
        )
    )
    catalog = Catalog.model_validate_json(
        (destination / "runs-output" / "catalog.json").read_text(encoding="utf-8")
    )
    assert catalog.runs == []
    assert len(dataset.images) == 3
    by_id = {image.image_id: image for image in dataset.images}
    assert by_id[f"{SEG_A}-f30650"].ground_truth == 0
    assert by_id[f"{SEG_B}-f30650"].ground_truth == 1
    provenance = by_id[f"{SEG_A}-f30650"].provenance
    assert provenance is not None
    assert provenance.display_id == "cholec80-v1-video02-s1226-e1256-f30650"
    assert (
        destination / "raw-images" / "cholec80" / "v1" / "images" / VIDEO_ID / SEG_A / "f30650.jpg"
    ).is_file()
    assert (
        destination / "raw-images" / "cholec80" / "v1" / "images" / VIDEO_ID / SEG_B / "f30650.jpg"
    ).is_file()


def test_unused_invalid_interval_does_not_block_import(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    _build_mini_export(export_root)
    xlsx = tmp_path / "gt.xlsx"
    # video03-style invalid end<start plus required rows only.
    _write_xlsx(
        xlsx,
        [
            (2, 0, 20, 26, 20, 56, 0, 0, 0, 0),
            (2, 1, 20, 40, 21, 0, 0, 0, 0, 0),
            (3, 0, 61, 46, 60, 0, 0, 0, 0, 0),
        ],
    )
    report = prepare_cholec80_dataset(
        export_root=export_root,
        ground_truth_xlsx=xlsx,
        destination=tmp_path / "out",
        dataset_id="cholec80",
        dataset_version="v1",
        dry_run=True,
    )
    assert report.image_count == 3
    assert report.unused_xlsx_rows == 1


def test_unused_duplicate_key_does_not_block_import(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    _build_mini_export(export_root)
    xlsx = tmp_path / "gt.xlsx"
    _write_xlsx(
        xlsx,
        [
            (2, 0, 20, 26, 20, 56, 0, 0, 0, 0),
            (2, 1, 20, 40, 21, 0, 0, 0, 0, 0),
            (6, 0, 13, 1, 13, 35, 0, 0, 0, 0),
            (6, 1, 13, 1, 13, 35, 0, 0, 0, 0),
        ],
    )
    report = prepare_cholec80_dataset(
        export_root=export_root,
        ground_truth_xlsx=xlsx,
        destination=tmp_path / "out",
        dataset_id="cholec80",
        dataset_version="v1",
        dry_run=True,
    )
    assert report.image_count == 3
    assert report.unused_xlsx_rows == 2


def test_missing_ground_truth_match_fails(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    _build_mini_export(export_root)
    xlsx = tmp_path / "gt.xlsx"
    _write_xlsx(xlsx, [(2, 0, 20, 26, 20, 56, 0, 0, 0, 0)])  # missing second segment
    with pytest.raises(Cholec80ImportError, match="Missing ground-truth match"):
        prepare_cholec80_dataset(
            export_root=export_root,
            ground_truth_xlsx=xlsx,
            destination=tmp_path / "out",
            dataset_id="cholec80",
            dataset_version="v1",
            dry_run=True,
        )


def test_required_duplicate_ground_truth_match_fails(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    _build_mini_export(export_root)
    xlsx = tmp_path / "gt.xlsx"
    _write_xlsx(
        xlsx,
        [
            (2, 0, 20, 26, 20, 56, 0, 0, 0, 0),
            (2, 1, 20, 26, 20, 56, 0, 0, 0, 0),  # duplicate REQUIRED interval
            (2, 1, 20, 40, 21, 0, 0, 0, 0, 0),
        ],
    )
    with pytest.raises(Cholec80ImportError, match="Ambiguous ground-truth match"):
        prepare_cholec80_dataset(
            export_root=export_root,
            ground_truth_xlsx=xlsx,
            destination=tmp_path / "out",
            dataset_id="cholec80",
            dataset_version="v1",
            dry_run=True,
        )


def test_invalid_critical_view_on_required_row_fails(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    _build_mini_export(export_root)
    xlsx = tmp_path / "gt.xlsx"
    _write_xlsx(
        xlsx,
        [
            (2, None, 20, 26, 20, 56, 0, 0, 0, 0),
            (2, 1, 20, 40, 21, 0, 0, 0, 0, 0),
        ],
    )
    with pytest.raises(Cholec80ImportError, match="critical_view"):
        prepare_cholec80_dataset(
            export_root=export_root,
            ground_truth_xlsx=xlsx,
            destination=tmp_path / "out",
            dataset_id="cholec80",
            dataset_version="v1",
            dry_run=True,
        )


def test_substituted_segment_fails_with_unchanged_aggregates(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    _build_mini_export(export_root)
    # Keep 3 images / 2 segments aggregates, but replace SEG_B with a fake segment id.
    fake_seg = f"{VIDEO_ID}-s1240-e1260-fake"
    lines = (export_root / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    rewritten: list[str] = []
    for line in lines:
        payload = json.loads(line)
        if payload["segment_id"] == SEG_B:
            payload["segment_id"] = fake_seg
            payload["image_id"] = f"{fake_seg}-f30650"
            payload["path"] = f"images/{VIDEO_ID}/{SEG_B}/f30650.jpg"
        rewritten.append(json.dumps(payload))
    (export_root / "manifest.jsonl").write_text("\n".join(rewritten) + "\n", encoding="utf-8")
    xlsx = tmp_path / "gt.xlsx"
    _write_xlsx(xlsx, _matching_gt_rows())
    with pytest.raises(Cholec80ImportError, match="absent from run.json segments"):
        prepare_cholec80_dataset(
            export_root=export_root,
            ground_truth_xlsx=xlsx,
            destination=tmp_path / "out",
            dataset_id="cholec80",
            dataset_version="v1",
            dry_run=True,
        )


def test_per_segment_count_mismatch_fails_with_unchanged_aggregates(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    _build_mini_export(export_root)
    run_payload = _default_run_payload()
    segments_obj = run_payload["segments"]
    assert isinstance(segments_obj, list)
    first = cast(dict[str, Any], segments_obj[0])
    second = cast(dict[str, Any], segments_obj[1])
    # Swap exported_count while keeping the sum at 3.
    first["exported_count"] = 1
    second["exported_count"] = 2
    _write_json(export_root / "run.json", run_payload)
    xlsx = tmp_path / "gt.xlsx"
    _write_xlsx(xlsx, _matching_gt_rows())
    with pytest.raises(Cholec80ImportError, match="image count mismatch"):
        prepare_cholec80_dataset(
            export_root=export_root,
            ground_truth_xlsx=xlsx,
            destination=tmp_path / "out",
            dataset_id="cholec80",
            dataset_version="v1",
            dry_run=True,
        )


def test_substituted_video_fails_with_unchanged_aggregates(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    _build_mini_export(export_root)
    lines = (export_root / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    rewritten: list[str] = []
    for line in lines:
        payload = json.loads(line)
        if payload["segment_id"] == SEG_B:
            payload["video_id"] = SKIPPED_VIDEO_ID
        rewritten.append(json.dumps(payload))
    (export_root / "manifest.jsonl").write_text("\n".join(rewritten) + "\n", encoding="utf-8")
    xlsx = tmp_path / "gt.xlsx"
    _write_xlsx(xlsx, _matching_gt_rows())
    with pytest.raises(Cholec80ImportError, match="skipped extraction job"):
        prepare_cholec80_dataset(
            export_root=export_root,
            ground_truth_xlsx=xlsx,
            destination=tmp_path / "out",
            dataset_id="cholec80",
            dataset_version="v1",
            dry_run=True,
        )


def test_missing_image_file_fails(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    _build_mini_export(export_root)
    (export_root / "images" / VIDEO_ID / SEG_A / "f30650.jpg").unlink()
    xlsx = tmp_path / "gt.xlsx"
    _write_xlsx(xlsx, _matching_gt_rows())
    with pytest.raises(Cholec80ImportError, match="Missing source image file"):
        prepare_cholec80_dataset(
            export_root=export_root,
            ground_truth_xlsx=xlsx,
            destination=tmp_path / "out",
            dataset_id="cholec80",
            dataset_version="v1",
            dry_run=True,
        )


def test_unsafe_image_path_fails(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    _build_mini_export(export_root)
    bad_line = _manifest_line(
        image_id=f"{SEG_A}-f30650",
        video_id=VIDEO_ID,
        segment_id=SEG_A,
        frame_index=30650,
        timestamp=1226.0,
        path="../escape.jpg",
        video_filename="video02.mp4",
        start_seconds=1226,
        end_seconds=1256,
        excel_row=1,
    )
    (export_root / "manifest.jsonl").write_text(bad_line + "\n", encoding="utf-8")
    run_payload = _default_run_payload()
    run_payload["counts"] = {
        "segments_planned": 1,
        "segments_completed": 1,
        "images_exported": 1,
    }
    run_payload["segments"] = [
        {
            "segment_id": SEG_A,
            "video_id": VIDEO_ID,
            "video_filename": "video02.mp4",
            "excel_row": 1,
            "start_seconds": 1226,
            "end_seconds": 1256,
            "requested_count": 1,
            "exported_count": 1,
        }
    ]
    run_payload["jobs"] = [
        {
            "source_filename": "video02.mp4",
            "status": "succeeded",
            "video_id": VIDEO_ID,
            "segments_completed": 1,
            "images_exported": 1,
            "issues": [],
        }
    ]
    run_payload["video_jobs"] = {"total": 1, "processed": 1, "succeeded": 1, "skipped": 0}
    run_payload["status"] = "completed"
    _write_json(export_root / "run.json", run_payload)
    xlsx = tmp_path / "gt.xlsx"
    _write_xlsx(xlsx, [(2, 0, 20, 26, 20, 56, 0, 0, 0, 0)])
    with pytest.raises(Cholec80ImportError):
        prepare_cholec80_dataset(
            export_root=export_root,
            ground_truth_xlsx=xlsx,
            destination=tmp_path / "out",
            dataset_id="cholec80",
            dataset_version="v1",
            dry_run=True,
        )


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    _build_mini_export(export_root)
    xlsx = tmp_path / "gt.xlsx"
    _write_xlsx(xlsx, _matching_gt_rows())
    destination = tmp_path / "portal-data"
    report = prepare_cholec80_dataset(
        export_root=export_root,
        ground_truth_xlsx=xlsx,
        destination=destination,
        dataset_id="cholec80",
        dataset_version="v1",
        dry_run=True,
    )
    assert report.dry_run is True
    assert report.image_count == 3
    assert not destination.exists()


def test_nonempty_destination_is_preserved(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    _build_mini_export(export_root)
    xlsx = tmp_path / "gt.xlsx"
    _write_xlsx(xlsx, _matching_gt_rows())
    destination = tmp_path / "portal-data"
    destination.mkdir()
    marker = destination / "keep-me.txt"
    marker.write_text("owner-data", encoding="utf-8")
    with pytest.raises(Cholec80ImportError, match="nonempty destination"):
        prepare_cholec80_dataset(
            export_root=export_root,
            ground_truth_xlsx=xlsx,
            destination=destination,
            dataset_id="cholec80",
            dataset_version="v1",
            dry_run=False,
        )
    assert marker.read_text(encoding="utf-8") == "owner-data"


def test_duplicate_display_id_rejected_by_domain() -> None:
    provenance = ImageProvenance(
        video_id="v-a",
        video_filename="video02.mp4",
        segment_id="v-a-s1-e2",
        start_seconds=1,
        end_seconds=2,
        frame_index=10,
        timestamp=1.0,
        display_id="cholec80-v1-video02-s1-e2-f10",
    )
    with pytest.raises(ValidationError, match="display_id"):
        DatasetVersion(
            schema_version="1",
            dataset_id="cholec80",
            dataset_version="v1",
            display_name="Cholec80",
            description=None,
            images=[
                DatasetImage(
                    image_id="a-1",
                    raw_image_key="images/v-a/s/f10.jpg",
                    ground_truth=0,
                    provenance=provenance,
                ),
                DatasetImage(
                    image_id="a-2",
                    raw_image_key="images/v-a/s/f11.jpg",
                    ground_truth=0,
                    provenance=provenance.model_copy(update={"frame_index": 11, "timestamp": 2.0}),
                ),
            ],
        )
