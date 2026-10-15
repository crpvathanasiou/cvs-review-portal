"""Behavioral tests for browser image-content caching (ETag / Cache-Control / 304)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cvs_review_portal.api.image_cache import (
    IMAGE_CACHE_CONTROL,
    if_none_match_satisfied,
    strong_etag_for_bytes,
)
from cvs_review_portal.infrastructure.azure_blob_store import AzureBlobPortalDataStore
from cvs_review_portal.main import create_app
from tests.fixture_trees import build_demo_tree, make_settings, png_bytes

_IMAGE_PATH = "/api/datasets/ds-a/versions/v1/images/a/content"


def _etag_for(content: bytes) -> str:
    return f'"{hashlib.sha256(content).hexdigest()}"'


def _assert_success_cache_headers(response: Any, *, etag: str) -> None:
    assert response.headers.get("cache-control") == IMAGE_CACHE_CONTROL
    assert response.headers.get("etag") == etag
    vary = response.headers.get("vary") or ""
    tokens = {part.strip().casefold() for part in vary.split(",") if part.strip()}
    assert "cookie" in tokens
    assert "authorization" in tokens


def _assert_no_store(response: Any) -> None:
    assert "no-store" in (response.headers.get("cache-control") or "").casefold()
    assert response.status_code != 304


def test_strong_etag_is_quoted_sha256() -> None:
    body = b"abc"
    assert strong_etag_for_bytes(body) == _etag_for(body)


@pytest.mark.parametrize(
    ("header", "etag", "expected"),
    [
        (None, '"abc"', False),
        ("", '"abc"', False),
        ("*", '"abc"', True),
        ('"abc"', '"abc"', True),
        ('W/"abc"', '"abc"', True),
        ('"abc", "other"', '"abc"', True),
        ('W/"other", "abc"', '"abc"', True),
        ('"other"', '"abc"', False),
        ("not-a-tag", '"abc"', False),
        ('"abc", *', '"abc"', True),  # listed tag still matches
        ("*, junk", '"abc"', False),  # * must be the whole field
        ('"unterminated', '"abc"', False),
    ],
)
def test_if_none_match_semantics(header: str | None, etag: str, expected: bool) -> None:
    assert if_none_match_satisfied(header, etag) is expected


def test_initial_image_response_bytes_media_type_cache_and_etag(
    client: TestClient, data_root: Path
) -> None:
    expected = (data_root / "raw-images" / "ds-a" / "v1" / "a.png").read_bytes()
    response = client.get(_IMAGE_PATH)
    assert response.status_code == 200
    assert response.content == expected
    assert response.headers["content-type"].startswith("image/png")
    etag = _etag_for(expected)
    _assert_success_cache_headers(response, etag=etag)


def test_matching_validator_returns_304_empty_body(client: TestClient, data_root: Path) -> None:
    expected = (data_root / "raw-images" / "ds-a" / "v1" / "a.png").read_bytes()
    etag = _etag_for(expected)
    first = client.get(_IMAGE_PATH)
    assert first.status_code == 200
    assert first.headers["etag"] == etag

    for validator in (etag, f"W/{etag}", f'"other", {etag}', "*"):
        response = client.get(_IMAGE_PATH, headers={"If-None-Match": validator})
        assert response.status_code == 304, validator
        assert response.content == b""
        _assert_success_cache_headers(response, etag=etag)


def test_non_matching_validator_returns_200(client: TestClient, data_root: Path) -> None:
    expected = (data_root / "raw-images" / "ds-a" / "v1" / "a.png").read_bytes()
    response = client.get(_IMAGE_PATH, headers={"If-None-Match": '"deadbeef"'})
    assert response.status_code == 200
    assert response.content == expected
    _assert_success_cache_headers(response, etag=_etag_for(expected))


def test_changed_image_bytes_new_etag_and_200_with_old_validator(
    client: TestClient, data_root: Path
) -> None:
    path = data_root / "raw-images" / "ds-a" / "v1" / "a.png"
    original = path.read_bytes()
    old_etag = _etag_for(original)
    assert client.get(_IMAGE_PATH).headers["etag"] == old_etag

    updated = png_bytes((99, 88, 77))
    assert updated != original
    path.write_bytes(updated)
    new_etag = _etag_for(updated)

    response = client.get(_IMAGE_PATH, headers={"If-None-Match": old_etag})
    assert response.status_code == 200
    assert response.content == updated
    _assert_success_cache_headers(response, etag=new_etag)
    assert new_etag != old_etag


def test_malformed_if_none_match_does_not_500(client: TestClient) -> None:
    response = client.get(
        _IMAGE_PATH,
        headers={"If-None-Match": ',,,W/, "\nbroken'},
    )
    assert response.status_code == 200
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_unauthorized_image_is_not_304_and_not_cacheable(tmp_path: Path) -> None:
    root = tmp_path / "data"
    build_demo_tree(root)
    settings = make_settings(
        data_root=root,
        identity_mode="disabled",
        development_actor=None,
        allowed_actors="",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get(_IMAGE_PATH, headers={"If-None-Match": "*"})
        assert response.status_code == 401
        _assert_no_store(response)


def test_unpublished_dataset_image_is_not_304(tmp_path: Path) -> None:
    root = tmp_path / "data"
    build_demo_tree(root)
    # On-disk image for an unpublished dataset identity.
    orphan_raw = root / "raw-images" / "orphan" / "v1"
    orphan_raw.mkdir(parents=True)
    (orphan_raw / "x.png").write_bytes(png_bytes((1, 1, 1)))
    with TestClient(create_app(make_settings(data_root=root))) as client:
        response = client.get(
            "/api/datasets/orphan/versions/v1/images/x/content",
            headers={"If-None-Match": "*"},
        )
        assert response.status_code == 404
        _assert_no_store(response)


def test_missing_image_is_not_304(client: TestClient) -> None:
    response = client.get(
        "/api/datasets/ds-a/versions/v1/images/missing/content",
        headers={"If-None-Match": "*"},
    )
    assert response.status_code == 404
    _assert_no_store(response)


def test_invalid_path_identifier_is_not_304(client: TestClient) -> None:
    # Encoded ".." as image_id — must fail validation, never become a cached 304.
    response = client.get(
        "/api/datasets/ds-a/versions/v1/images/%2e%2e/content",
        headers={"If-None-Match": "*"},
    )
    assert response.status_code == 422
    _assert_no_store(response)


def test_mutable_json_endpoints_do_not_get_image_cache_policy(client: TestClient) -> None:
    summary = client.get("/api/datasets/ds-a/versions/v1/summary")
    assert summary.status_code == 200
    assert summary.headers.get("cache-control") != IMAGE_CACHE_CONTROL

    review = client.get("/api/datasets/ds-a/versions/v1/images/a/review")
    assert review.status_code == 200
    assert review.headers.get("cache-control") != IMAGE_CACHE_CONTROL


def test_azure_adapter_image_caching_equivalent(tmp_path: Path) -> None:
    """Same cache headers/304 behavior via mocked AzureBlobPortalDataStore (no live Azure)."""
    image_bytes = png_bytes((11, 22, 33))
    catalog = {
        "schema_version": "1",
        "datasets": [{"dataset_id": "ds-a", "dataset_version": "v1"}],
        "runs": [],
    }
    dataset = {
        "schema_version": "1",
        "dataset_id": "ds-a",
        "dataset_version": "v1",
        "display_name": "A",
        "description": None,
        "images": [
            {
                "image_id": "a",
                "raw_image_key": "a.png",
                "ground_truth": 0,
                "comments": None,
            }
        ],
    }
    blobs: dict[str, bytes] = {
        "runs-output/catalog.json": json.dumps(catalog).encode("utf-8"),
        "runs-output/datasets/ds-a/v1/dataset.json": json.dumps(dataset).encode("utf-8"),
        "raw-images/ds-a/v1/a.png": image_bytes,
    }

    store = AzureBlobPortalDataStore(
        account_url="https://example.blob.core.windows.net",
        container_name="portal",
        credential=object(),
    )

    def download_bytes(key: str) -> bytes:
        if key not in blobs:
            from cvs_review_portal.domain.errors import ResourceNotFoundError

            raise ResourceNotFoundError("Artifact not found.", safe_context="artifact=blob")
        return blobs[key]

    settings = make_settings(data_root=tmp_path / "unused-local")
    app: FastAPI = create_app(settings)
    with TestClient(app) as client:
        with (
            patch.object(store, "ensure_available", return_value=None),
            patch.object(store, "_download_bytes", side_effect=download_bytes),
        ):
            app.state.portal_store = store
            etag = _etag_for(image_bytes)

            first = client.get(_IMAGE_PATH)
            assert first.status_code == 200
            assert first.content == image_bytes
            assert first.headers["content-type"].startswith("image/png")
            _assert_success_cache_headers(first, etag=etag)

            cached = client.get(_IMAGE_PATH, headers={"If-None-Match": etag})
            assert cached.status_code == 304
            assert cached.content == b""
            _assert_success_cache_headers(cached, etag=etag)

            miss = client.get(_IMAGE_PATH, headers={"If-None-Match": '"other"'})
            assert miss.status_code == 200
            assert miss.content == image_bytes
