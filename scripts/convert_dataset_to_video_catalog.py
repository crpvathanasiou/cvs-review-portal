#!/usr/bin/env python3
"""Convert a monolithic dataset.json into per-video JSON + videos.csv.

Reads the full dataset.json once, writes one JSON file per video, and writes
videos.csv for the first N videos (by video_name). Does not modify the original
dataset.json, images, reviews, Excel, or engine exports. Does not copy images.
Refuses to silently overwrite an already edited videos.csv.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

# Allow running without installing the package when Poetry env is active.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from cvs_review_portal.application.video_catalog import (  # noqa: E402
    expected_video_metadata_key,
    format_videos_csv,
)
from cvs_review_portal.domain.models import (  # noqa: E402
    DatasetVersion,
    VideoArtifact,
    VideoCatalogEntry,
)


def _strip_retired(payload: object) -> object:
    if not isinstance(payload, dict):
        return payload
    images = payload.get("images")
    if not isinstance(images, list):
        return payload
    cleaned = []
    changed = False
    for image in images:
        if isinstance(image, dict) and "ground_truth_editable" in image:
            cleaned.append({k: v for k, v in image.items() if k != "ground_truth_editable"})
            changed = True
        else:
            cleaned.append(image)
    if not changed:
        return payload
    return {**payload, "images": cleaned}


def convert(
    *,
    data_root: Path,
    dataset_id: str,
    dataset_version: str,
    active_limit: int,
    write_all_video_json: bool,
    force_csv: bool,
) -> dict[str, int]:
    dataset_dir = data_root / "runs-output" / "datasets" / dataset_id / dataset_version
    dataset_path = dataset_dir / "dataset.json"
    if not dataset_path.is_file():
        raise SystemExit(f"dataset.json not found: {dataset_path}")

    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    dataset = DatasetVersion.model_validate(_strip_retired(raw))

    by_video: dict[str, list] = defaultdict(list)
    video_names: dict[str, str] = {}
    for image in dataset.images:
        if image.provenance is None:
            raise SystemExit(f"Image {image.image_id} has no provenance; cannot split by video.")
        vid = image.provenance.video_id
        by_video[vid].append(image)
        name = image.provenance.video_filename
        if vid in video_names and video_names[vid] != name:
            raise SystemExit(f"Conflicting video_name for {vid}: {video_names[vid]!r} vs {name!r}")
        video_names[vid] = name

    # Stable order by video_name then video_id.
    ordered_ids = sorted(by_video.keys(), key=lambda vid: (video_names[vid].lower(), vid))

    videos_dir = dataset_dir / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    json_written = 0
    ids_for_json = ordered_ids if write_all_video_json else ordered_ids[:active_limit]
    for video_id in ids_for_json:
        images = by_video[video_id]
        artifact = VideoArtifact(
            schema_version=dataset.schema_version,
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.dataset_version,
            display_name=dataset.display_name,
            description=dataset.description,
            video_id=video_id,
            video_name=video_names[video_id],
            images=images,
        )
        out_path = videos_dir / f"{video_id}.json"
        out_path.write_text(
            json.dumps(artifact.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        json_written += 1

    active_ids = ordered_ids[:active_limit]
    entries = [
        VideoCatalogEntry(
            video_id=video_id,
            video_name=video_names[video_id],
            metadata_path=expected_video_metadata_key(dataset_id, dataset_version, video_id),
        )
        for video_id in active_ids
    ]
    csv_path = dataset_dir / "videos.csv"
    if csv_path.is_file() and not force_csv:
        raise SystemExit(
            f"Refusing to overwrite existing videos.csv at {csv_path}. "
            "Pass --force-csv to replace it, or edit the CSV manually."
        )
    csv_path.write_text(format_videos_csv(entries), encoding="utf-8")

    active_intervals = 0
    active_images = 0
    for video_id in active_ids:
        images = by_video[video_id]
        active_images += len(images)
        segs = {img.provenance.segment_id for img in images if img.provenance is not None}
        active_intervals += len(segs)

    total_intervals = 0
    for images in by_video.values():
        segs = {img.provenance.segment_id for img in images if img.provenance is not None}
        total_intervals += len(segs)

    counts = {
        "videos_total": len(ordered_ids),
        "videos_json_written": json_written,
        "videos_active_csv": len(active_ids),
        "intervals_total": total_intervals,
        "intervals_active": active_intervals,
        "images_total": len(dataset.images),
        "images_active": active_images,
    }
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split dataset.json into per-video JSON files and videos.csv."
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        required=True,
        help="Portal data root containing runs-output/datasets/...",
    )
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument(
        "--active-limit",
        type=int,
        default=10,
        help="Number of videos (ordered by name) to list in videos.csv (default: 10).",
    )
    parser.add_argument(
        "--all-video-json",
        action="store_true",
        help="Write JSON for every video (CSV still limited by --active-limit).",
    )
    parser.add_argument(
        "--force-csv",
        action="store_true",
        help="Overwrite an existing videos.csv (default: refuse).",
    )
    args = parser.parse_args()
    if args.active_limit < 0:
        raise SystemExit("--active-limit must be >= 0")

    counts = convert(
        data_root=args.data_root.resolve(),
        dataset_id=args.dataset_id,
        dataset_version=args.dataset_version,
        active_limit=args.active_limit,
        write_all_video_json=args.all_video_json,
        force_csv=args.force_csv,
    )
    print("Conversion complete:")
    for key, value in counts.items():
        print(f"  {key}: {value}")
    print(f"  CSV: runs-output/datasets/{args.dataset_id}/{args.dataset_version}/videos.csv")
    print(
        f"  Videos: runs-output/datasets/{args.dataset_id}/{args.dataset_version}/videos/"
        f"<video_id>.json"
    )
    print("  Original dataset.json was not modified.")


if __name__ == "__main__":
    main()
