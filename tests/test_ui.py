"""Tests for Step 2 portal UI serving."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cvs_review_portal.api.ui import WEB_DIR
from cvs_review_portal.main import create_app
from tests.fixture_trees import build_demo_tree, make_settings


def test_portal_index_serves_html(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert "CVS Review Portal" in body
    assert "/ui-assets/styles.css" in body
    assert "/ui-assets/app.js" in body


def test_ui_assets_are_served(client: TestClient) -> None:
    css = client.get("/ui-assets/styles.css")
    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert "CVS Review Portal" in css.text or ":root" in css.text

    js = client.get("/ui-assets/app.js")
    assert js.status_code == 200
    assert "javascript" in js.headers["content-type"] or "text/" in js.headers["content-type"]
    assert "CVS Review Portal" in js.text or "/api/datasets" in js.text


def test_system_and_api_routes_remain_compatible(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").status_code == 200
    assert client.get("/version").status_code == 200
    assert client.get("/api/datasets").status_code == 200
    assert client.get("/docs").status_code == 200


def test_ui_serving_does_not_require_data_root(tmp_path: Path) -> None:
    missing_root = tmp_path / "absent-data-root"
    settings = make_settings(data_root=missing_root)
    with TestClient(create_app(settings)) as test_client:
        index = test_client.get("/")
        assert index.status_code == 200
        assert "CVS Review Portal" in index.text
        assert test_client.get("/ui-assets/styles.css").status_code == 200
        assert test_client.get("/ui-assets/app.js").status_code == 200
        assert test_client.get("/health").json() == {"status": "ok"}
        # Data endpoints still fail controlled; UI must not depend on DATA_ROOT.
        assert test_client.get("/api/datasets").status_code == 503


def test_ui_does_not_expose_dataset_files_as_static(client: TestClient, data_root: Path) -> None:
    # Mount only web assets; raw image paths under DATA_ROOT must not be static.
    leaked = client.get("/raw-images/ds-a/v1/a.png")
    assert leaked.status_code == 404

    leaked_ui = client.get("/ui-assets/../../demo-data/raw-images/ds-a/v1/a.png")
    assert leaked_ui.status_code in {404, 400}

    # Canonical image access remains the API content endpoint.
    image = client.get("/api/datasets/ds-a/versions/v1/images/a/content")
    assert image.status_code == 200
    assert image.content.startswith(b"\x89PNG")


def test_web_assets_resolve_from_package_not_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "data"
    build_demo_tree(root)
    settings = make_settings(data_root=root)
    with TestClient(create_app(settings)) as test_client:
        assert test_client.get("/").status_code == 200
        assert test_client.get("/ui-assets/app.js").status_code == 200
    assert WEB_DIR.is_dir()
    assert (WEB_DIR / "index.html").is_file()


def test_create_app_with_default_settings_still_serves_ui() -> None:
    app = create_app(make_settings())
    with TestClient(app) as test_client:
        assert test_client.get("/").status_code == 200
