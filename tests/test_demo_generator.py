"""Tests for the nondestructive demo-data generator."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "generate_demo_data.py"
_SPEC = importlib.util.spec_from_file_location("generate_demo_data", _SCRIPTS)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_generate_demo_bundle_in_empty_directory(tmp_path: Path) -> None:
    target = tmp_path / "fresh-demo"
    _MODULE.generate_demo_bundle(target)

    catalog = json.loads((target / "runs-output" / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["datasets"][0]["dataset_id"] == "demo-surgical"
    assert (target / "runs-output" / "datasets" / "demo-surgical" / "v1" / "dataset.json").is_file()
    assert (target / "runs-output" / "runs" / "run-baseline" / "run.json").is_file()
    assert (target / "reviews" / "demo-surgical" / "v1" / "img-001.json").is_file()
    dataset = json.loads(
        (target / "runs-output" / "datasets" / "demo-surgical" / "v1" / "dataset.json").read_text(
            encoding="utf-8"
        )
    )
    assert "Surgical" in dataset["display_name"]
    assert "Synthetic" in dataset["description"]


def test_generate_demo_bundle_refuses_nonempty_target(tmp_path: Path) -> None:
    target = tmp_path / "occupied"
    target.mkdir()
    sentinel = target / "sentinel.txt"
    sentinel.write_text("keep-me", encoding="utf-8")

    with pytest.raises(_MODULE.DemoTargetNotEmptyError):
        _MODULE.generate_demo_bundle(target)

    assert sentinel.read_text(encoding="utf-8") == "keep-me"
    assert list(target.iterdir()) == [sentinel]
