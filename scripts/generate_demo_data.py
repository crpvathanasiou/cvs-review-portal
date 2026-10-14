"""Generate a synthetic demo-data bundle for local portal inspection (stdlib only).

Usage (from repository root):

    poetry run python scripts/generate_demo_data.py

The generator refuses to write into a nonempty target directory and never deletes
existing files. Publish the catalog last, after all referenced artifacts exist.
"""

from __future__ import annotations

import json
import struct
import sys
import zlib
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "demo-data"


class DemoTargetNotEmptyError(RuntimeError):
    """Raised when the demo target already contains files."""


def _png_rgb(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """Return a minimal RGB PNG."""
    r, g, b = rgb
    raw = b"".join(b"\x00" + bytes([r, g, b]) * width for _ in range(height))
    compressed = zlib.compress(raw, level=9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _assert_empty_target(root: Path) -> None:
    if not root.exists():
        return
    if any(root.rglob("*")):
        raise DemoTargetNotEmptyError(
            f"Refusing to overwrite nonempty demo target: {root}. "
            "Leave existing contents untouched."
        )


def generate_demo_bundle(root: Path) -> Path:
    """Write a complete synthetic demo bundle under `root`.

    Raises `DemoTargetNotEmptyError` when `root` already contains any files or
    directories, leaving the target unchanged.
    """
    _assert_empty_target(root)
    root.mkdir(parents=True, exist_ok=True)

    surgical_raw = root / "raw-images" / "demo-surgical" / "v1"
    surgical_raw.mkdir(parents=True)
    (surgical_raw / "img-001.png").write_bytes(_png_rgb(8, 8, (40, 120, 200)))
    (surgical_raw / "img-002.png").write_bytes(_png_rgb(8, 8, (200, 80, 40)))
    (surgical_raw / "img-003.png").write_bytes(_png_rgb(8, 8, (80, 180, 80)))

    empty_raw = root / "raw-images" / "demo-empty-runs" / "v1"
    empty_raw.mkdir(parents=True)
    (empty_raw / "solo-001.png").write_bytes(_png_rgb(4, 4, (120, 120, 120)))

    _write_json(
        root / "runs-output" / "datasets" / "demo-surgical" / "v1" / "dataset.json",
        {
            "schema_version": "1",
            "dataset_id": "demo-surgical",
            "dataset_version": "v1",
            "display_name": "Demo Surgical Dataset",
            "description": ("Synthetic CVS surgical-demo dataset — not patient data."),
            "images": [
                {
                    "image_id": "img-001",
                    "raw_image_key": "img-001.png",
                    "ground_truth": 0,
                    "comments": "Baseline negative example.",
                },
                {
                    "image_id": "img-002",
                    "raw_image_key": "img-002.png",
                    "ground_truth": 1,
                    "comments": None,
                },
                {
                    "image_id": "img-003",
                    "raw_image_key": "img-003.png",
                    "ground_truth": 1,
                    "comments": "Positive example.",
                },
            ],
        },
    )

    _write_json(
        root / "runs-output" / "datasets" / "demo-empty-runs" / "v1" / "dataset.json",
        {
            "schema_version": "1",
            "dataset_id": "demo-empty-runs",
            "dataset_version": "v1",
            "display_name": "Demo Dataset Without Runs",
            "description": "Synthetic dataset published with no runs.",
            "images": [
                {
                    "image_id": "solo-001",
                    "raw_image_key": "solo-001.png",
                    "ground_truth": 0,
                    "comments": "Only image in a run-less dataset.",
                }
            ],
        },
    )

    baseline = root / "runs-output" / "runs" / "run-baseline"
    _write_json(
        baseline / "run.json",
        {
            "schema_version": "1",
            "run_id": "run-baseline",
            "dataset_id": "demo-surgical",
            "dataset_version": "v1",
            "model": {
                "model_id": "demo-classifier-a",
                "model_name": "Demo Classifier A",
                "model_version": "1.0.0",
                "description": "Synthetic baseline model description.",
            },
            "model_parameters": {"threshold": 0.5, "seed": 42},
            "preprocessing": {},
            "execution_description": "Synthetic demo execution with metrics.",
            "executed_at": "2026-03-01T10:15:00+00:00",
            "predictions_artifact": "predictions.json",
            "metrics_artifact": "metrics.json",
            "evaluation_snapshot_artifact": "evaluation_snapshot.json",
        },
    )
    _write_json(
        baseline / "predictions.json",
        {
            "schema_version": "1",
            "predictions": [
                {
                    "image_id": "img-001",
                    "predicted_label": 0,
                    "positive_class_probability": 0.12,
                    "description": "Model notes for img-001.",
                },
                {
                    "image_id": "img-002",
                    "predicted_label": 1,
                    "positive_class_probability": 0.91,
                    "description": "Model notes for img-002.",
                },
                {
                    "image_id": "img-003",
                    "predicted_label": 1,
                    "positive_class_probability": 0.77,
                    "description": None,
                },
            ],
        },
    )
    _write_json(
        baseline / "metrics.json",
        {
            "schema_version": "1",
            "accuracy": 1.0,
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
            "confusion_matrix": {"labels": [0, 1], "matrix": [[1, 0], [0, 2]]},
            "evaluated_image_count": 3,
        },
    )
    _write_json(
        baseline / "evaluation_snapshot.json",
        {
            "schema_version": "1",
            "evaluated_images": [
                {"image_id": "img-001", "ground_truth": 0},
                {"image_id": "img-002", "ground_truth": 1},
                {"image_id": "img-003", "ground_truth": 1},
            ],
        },
    )

    alt = root / "runs-output" / "runs" / "run-alt-model"
    _write_json(
        alt / "run.json",
        {
            "schema_version": "1",
            "run_id": "run-alt-model",
            "dataset_id": "demo-surgical",
            "dataset_version": "v1",
            "model": {
                "model_id": "demo-classifier-b",
                "model_name": "Demo Classifier B",
                "model_version": "2.1.0",
                "description": "Alternate synthetic model configuration.",
            },
            "model_parameters": {"threshold": 0.4, "augment": True},
            "preprocessing": {"resize": [256, 256]},
            "execution_description": "Second execution on the same dataset version.",
            "executed_at": "2026-03-01T11:00:00+00:00",
            "predictions_artifact": "predictions.json",
            "metrics_artifact": None,
            "evaluation_snapshot_artifact": None,
        },
    )
    _write_json(
        alt / "predictions.json",
        {
            "schema_version": "1",
            "predictions": [
                {
                    "image_id": "img-001",
                    "predicted_label": 1,
                    "positive_class_probability": 0.55,
                    "description": "Alt model disagrees on img-001.",
                },
                {
                    "image_id": "img-002",
                    "predicted_label": 1,
                    "positive_class_probability": 0.88,
                    "description": None,
                },
                {
                    "image_id": "img-003",
                    "predicted_label": 0,
                    "positive_class_probability": 0.41,
                    "description": "Alt model predicted zero.",
                },
            ],
        },
    )

    empty = root / "runs-output" / "runs" / "run-empty-preds"
    _write_json(
        empty / "run.json",
        {
            "schema_version": "1",
            "run_id": "run-empty-preds",
            "dataset_id": "demo-surgical",
            "dataset_version": "v1",
            "model": {
                "model_id": "demo-classifier-empty",
                "model_name": "Demo Empty Predictions",
                "model_version": "0.0.1",
                "description": "Run with an empty prediction collection.",
            },
            "model_parameters": {},
            "preprocessing": {},
            "execution_description": "No predictions published.",
            "executed_at": "2026-03-01T12:00:00+00:00",
            "predictions_artifact": "predictions.json",
            "metrics_artifact": None,
            "evaluation_snapshot_artifact": None,
        },
    )
    _write_json(empty / "predictions.json", {"schema_version": "1", "predictions": []})

    partial = root / "runs-output" / "runs" / "run-partial-preds"
    _write_json(
        partial / "run.json",
        {
            "schema_version": "1",
            "run_id": "run-partial-preds",
            "dataset_id": "demo-surgical",
            "dataset_version": "v1",
            "model": {
                "model_id": "demo-classifier-partial",
                "model_name": "Demo Partial Predictions",
                "model_version": "0.3.0",
                "description": "Partial coverage run.",
            },
            "model_parameters": {"batch": 1},
            "preprocessing": {},
            "execution_description": "Only one image predicted.",
            "executed_at": "2026-03-01T13:00:00+00:00",
            "predictions_artifact": "predictions.json",
            "metrics_artifact": None,
            "evaluation_snapshot_artifact": None,
        },
    )
    _write_json(
        partial / "predictions.json",
        {
            "schema_version": "1",
            "predictions": [
                {
                    "image_id": "img-002",
                    "predicted_label": 0,
                    "positive_class_probability": 0.05,
                    "description": "Legitimate zero prediction on img-002.",
                }
            ],
        },
    )

    _write_json(
        root / "reviews" / "demo-surgical" / "v1" / "img-001.json",
        {
            "schema_version": "1",
            "dataset_id": "demo-surgical",
            "dataset_version": "v1",
            "image_id": "img-001",
            "ground_truth_override": 1,
            "comments": "Seeded shared review comment.",
            "revision": 1,
            "actor": "demo-reviewer",
            "updated_at": "2026-03-02T14:00:00+00:00",
        },
    )

    # Catalog is published last so all referenced artifacts already exist.
    _write_json(
        root / "runs-output" / "catalog.json",
        {
            "schema_version": "1",
            "datasets": [
                {"dataset_id": "demo-surgical", "dataset_version": "v1"},
                {"dataset_id": "demo-empty-runs", "dataset_version": "v1"},
            ],
            "runs": [
                {"run_id": "run-baseline"},
                {"run_id": "run-alt-model"},
                {"run_id": "run-empty-preds"},
                {"run_id": "run-partial-preds"},
            ],
        },
    )
    return root


def main() -> int:
    try:
        generate_demo_bundle(DEFAULT_ROOT)
    except DemoTargetNotEmptyError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Wrote demo data under {DEFAULT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
