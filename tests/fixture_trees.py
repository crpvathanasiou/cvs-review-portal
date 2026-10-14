"""Helpers for building isolated temporary portal data trees in tests."""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

from pydantic_settings import SettingsConfigDict

from cvs_review_portal.settings import Settings


class IsolatedSettings(Settings):
    """Settings that never load the developer's real `.env` file."""

    model_config = SettingsConfigDict(env_file=None)


def make_settings(**overrides: object) -> IsolatedSettings:
    """Build isolated settings with development identity enabled for tests."""
    payload: dict[str, object] = {
        "identity_mode": "development",
        "development_actor": "test-reviewer",
        "allowed_actors": "test-reviewer",
    }
    payload.update(overrides)
    return IsolatedSettings(**payload)  # type: ignore[arg-type]


def _png(rgb: tuple[int, int, int] = (10, 20, 30)) -> bytes:
    width = height = 2
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


def build_demo_tree(root: Path) -> None:
    """Build a coherent mini fixture tree under `root`."""
    raw = root / "raw-images" / "ds-a" / "v1"
    raw.mkdir(parents=True)
    (raw / "a.png").write_bytes(_png((1, 2, 3)))
    (raw / "b.png").write_bytes(_png((4, 5, 6)))
    (raw / "c.png").write_bytes(_png((7, 8, 9)))

    raw_b = root / "raw-images" / "ds-b" / "v1"
    raw_b.mkdir(parents=True)
    (raw_b / "only.png").write_bytes(_png((9, 9, 9)))

    _write_json(
        root / "runs-output" / "catalog.json",
        {
            "schema_version": "1",
            "datasets": [
                {"dataset_id": "ds-a", "dataset_version": "v1"},
                {"dataset_id": "ds-b", "dataset_version": "v1"},
            ],
            "runs": [
                {"run_id": "run-full"},
                {"run_id": "run-alt"},
                {"run_id": "run-empty"},
                {"run_id": "run-partial"},
            ],
        },
    )

    _write_json(
        root / "runs-output" / "datasets" / "ds-a" / "v1" / "dataset.json",
        {
            "schema_version": "1",
            "dataset_id": "ds-a",
            "dataset_version": "v1",
            "display_name": "Dataset A",
            "description": "Synthetic test dataset.",
            "images": [
                {
                    "image_id": "a",
                    "raw_image_key": "a.png",
                    "ground_truth": 0,
                    "comments": "orig-a",
                },
                {
                    "image_id": "b",
                    "raw_image_key": "b.png",
                    "ground_truth": 1,
                    "comments": None,
                },
                {
                    "image_id": "c",
                    "raw_image_key": "c.png",
                    "ground_truth": 1,
                    "comments": "orig-c",
                },
            ],
        },
    )

    _write_json(
        root / "runs-output" / "datasets" / "ds-b" / "v1" / "dataset.json",
        {
            "schema_version": "1",
            "dataset_id": "ds-b",
            "dataset_version": "v1",
            "display_name": "Dataset B",
            "description": "No runs.",
            "images": [
                {
                    "image_id": "only",
                    "raw_image_key": "only.png",
                    "ground_truth": 0,
                    "comments": None,
                }
            ],
        },
    )

    full = root / "runs-output" / "runs" / "run-full"
    _write_json(
        full / "run.json",
        {
            "schema_version": "1",
            "run_id": "run-full",
            "dataset_id": "ds-a",
            "dataset_version": "v1",
            "model": {
                "model_id": "model-a",
                "model_name": "Model A",
                "model_version": "1.0",
                "description": "full",
            },
            "model_parameters": {"k": 1},
            "preprocessing": {},
            "execution_description": "full run",
            "executed_at": "2026-01-01T00:00:00+00:00",
            "predictions_artifact": "predictions.json",
            "metrics_artifact": "metrics.json",
            "evaluation_snapshot_artifact": "evaluation_snapshot.json",
        },
    )
    _write_json(
        full / "predictions.json",
        {
            "schema_version": "1",
            "predictions": [
                {
                    "image_id": "a",
                    "predicted_label": 0,
                    "positive_class_probability": 0.1,
                    "description": None,
                },
                {
                    "image_id": "b",
                    "predicted_label": 1,
                    "positive_class_probability": 0.9,
                    "description": "b",
                },
                {
                    "image_id": "c",
                    "predicted_label": 1,
                    "positive_class_probability": 0.8,
                    "description": None,
                },
            ],
        },
    )
    _write_json(
        full / "metrics.json",
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
        full / "evaluation_snapshot.json",
        {
            "schema_version": "1",
            "evaluated_images": [
                {"image_id": "a", "ground_truth": 0},
                {"image_id": "b", "ground_truth": 1},
                {"image_id": "c", "ground_truth": 1},
            ],
        },
    )

    alt = root / "runs-output" / "runs" / "run-alt"
    _write_json(
        alt / "run.json",
        {
            "schema_version": "1",
            "run_id": "run-alt",
            "dataset_id": "ds-a",
            "dataset_version": "v1",
            "model": {
                "model_id": "model-b",
                "model_name": "Model B",
                "model_version": "2.0",
                "description": "alt",
            },
            "model_parameters": {},
            "preprocessing": {"x": True},
            "execution_description": None,
            "executed_at": "2026-01-02T00:00:00+00:00",
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
                    "image_id": "a",
                    "predicted_label": 1,
                    "positive_class_probability": 0.6,
                    "description": None,
                },
                {
                    "image_id": "b",
                    "predicted_label": 1,
                    "positive_class_probability": 0.7,
                    "description": None,
                },
                {
                    "image_id": "c",
                    "predicted_label": 0,
                    "positive_class_probability": 0.2,
                    "description": None,
                },
            ],
        },
    )

    empty = root / "runs-output" / "runs" / "run-empty"
    _write_json(
        empty / "run.json",
        {
            "schema_version": "1",
            "run_id": "run-empty",
            "dataset_id": "ds-a",
            "dataset_version": "v1",
            "model": {
                "model_id": "model-empty",
                "model_name": "Empty",
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
        },
    )
    _write_json(empty / "predictions.json", {"schema_version": "1", "predictions": []})

    partial = root / "runs-output" / "runs" / "run-partial"
    _write_json(
        partial / "run.json",
        {
            "schema_version": "1",
            "run_id": "run-partial",
            "dataset_id": "ds-a",
            "dataset_version": "v1",
            "model": {
                "model_id": "model-partial",
                "model_name": "Partial",
                "model_version": "0.1",
                "description": None,
            },
            "model_parameters": {},
            "preprocessing": {},
            "execution_description": None,
            "executed_at": "2026-01-03T00:00:00+00:00",
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
                    "image_id": "b",
                    "predicted_label": 0,
                    "positive_class_probability": 0.01,
                    "description": "zero-label",
                }
            ],
        },
    )

    _write_json(
        root / "reviews" / "ds-a" / "v1" / "a.json",
        {
            "schema_version": "1",
            "dataset_id": "ds-a",
            "dataset_version": "v1",
            "image_id": "a",
            "ground_truth_override": 1,
            "comments": "reviewed-a",
            "revision": 1,
            "actor": "tester",
            "updated_at": "2026-01-04T00:00:00+00:00",
        },
    )
