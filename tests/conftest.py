"""Shared pytest fixtures for portal tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cvs_review_portal.main import create_app
from tests.fixture_trees import build_demo_tree, make_settings


@pytest.fixture()
def data_root(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    build_demo_tree(root)
    return root


@pytest.fixture()
def client(data_root: Path) -> Iterator[TestClient]:
    settings = make_settings(data_root=data_root)
    with TestClient(create_app(settings)) as test_client:
        yield test_client
