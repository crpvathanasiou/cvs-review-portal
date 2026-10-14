"""Focused MVP Save regressions (no audit-history / receipt machine)."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from cvs_review_portal.domain.errors import (
    AuthenticationError,
    AuthorizationError,
    InvalidArtifactError,
    ResourceNotFoundError,
)
from cvs_review_portal.infrastructure.azure_blob_store import AzureBlobPortalDataStore
from cvs_review_portal.infrastructure.identity_azure import AzureAppServiceIdentityProvider
from cvs_review_portal.main import create_app
from tests.fixture_trees import build_demo_tree, make_settings


def _request_with_headers(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "https",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()],
        "client": ("127.0.0.1", 123),
        "server": ("test", 443),
    }
    return Request(scope)


def test_ui_save_wrapper_reaches_backend(tmp_path: Path) -> None:
    root = tmp_path / "data"
    build_demo_tree(root)
    settings = make_settings(data_root=root)
    with TestClient(create_app(settings)) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert b"register_save_logic.mjs" in page.content
        assert b"app.js" in page.content
        save = client.put(
            "/api/datasets/ds-a/versions/v1/images/b/review",
            json={"comments": "from-ui-path", "expected_revision": 0},
            headers={"Origin": "http://testserver"},
        )
        assert save.status_code == 200
        assert save.json()["current"]["comments"] == "from-ui-path"
        got = client.get("/api/datasets/ds-a/versions/v1/images/b/review")
        assert got.json()["review"]["comments"] == "from-ui-path"


def test_save_reload_preserves_empty_comment(client: TestClient) -> None:
    first = client.put(
        "/api/datasets/ds-a/versions/v1/images/b/review",
        json={"comments": "temp", "expected_revision": 0},
        headers={"Origin": "http://testserver"},
    )
    assert first.status_code == 200
    empty = client.put(
        "/api/datasets/ds-a/versions/v1/images/b/review",
        json={"comments": "", "expected_revision": 1},
        headers={"Origin": "http://testserver"},
    )
    assert empty.status_code == 200
    got = client.get("/api/datasets/ds-a/versions/v1/images/b/review")
    assert got.json()["persisted_revision"] == 2
    assert got.json()["review"]["comments"] == ""


def test_history_endpoint_removed(client: TestClient) -> None:
    response = client.get("/api/datasets/ds-a/versions/v1/images/b/review/history")
    assert response.status_code == 404


def test_catalog_missing_dataset_is_artifact_error_not_404(tmp_path: Path) -> None:
    root = tmp_path / "data"
    build_demo_tree(root)
    catalog = json.loads((root / "runs-output" / "catalog.json").read_text(encoding="utf-8"))
    catalog["datasets"].append({"dataset_id": "ghost-ds", "dataset_version": "v1"})
    (root / "runs-output" / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    settings = make_settings(data_root=root)
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/datasets/ghost-ds/versions/v1/images/x/review")
        assert response.status_code == 500
        assert "Catalog references" in response.json()["detail"]["message"]


def test_azure_missing_predictions_is_invalid_artifact() -> None:
    from unittest.mock import patch

    from cvs_review_portal.domain.models import RunManifest

    store = AzureBlobPortalDataStore(
        account_url="https://example.blob.core.windows.net",
        container_name="portal",
        credential=object(),
    )
    run = RunManifest.model_validate(
        {
            "schema_version": "1",
            "run_id": "run-full",
            "dataset_id": "ds-a",
            "dataset_version": "v1",
            "model": {"model_id": "m", "model_name": "M"},
            "predictions_artifact": "predictions.json",
            "metrics_artifact": None,
            "evaluation_snapshot_artifact": None,
        }
    )
    with patch.object(
        store,
        "_download_bytes",
        side_effect=ResourceNotFoundError("missing", safe_context="artifact=blob"),
    ):
        with pytest.raises(InvalidArtifactError):
            store.load_predictions(run)


def test_azure_actor_canonical_tid_oid() -> None:
    tid = "11111111-1111-1111-1111-111111111111"
    oid = "22222222-2222-2222-2222-222222222222"
    actor = f"aad:{tid}:{oid}"
    claims = {
        "claims": [
            {"typ": "tid", "val": tid},
            {"typ": "oid", "val": oid},
        ]
    }
    encoded = base64.b64encode(json.dumps(claims).encode("utf-8")).decode("ascii")
    allowed = AzureAppServiceIdentityProvider(allowed_actors=frozenset({actor}))
    assert allowed.resolve(_request_with_headers({"x-ms-client-principal": encoded})).actor == actor
    # Convenience header must not change format when consistent.
    assert (
        allowed.resolve(
            _request_with_headers(
                {
                    "x-ms-client-principal": encoded,
                    "x-ms-client-principal-id": oid,
                }
            )
        ).actor
        == actor
    )
    with pytest.raises(AuthenticationError):
        allowed.resolve(
            _request_with_headers(
                {
                    "x-ms-client-principal": encoded,
                    "x-ms-client-principal-id": "other-oid",
                }
            )
        )
    denied = AzureAppServiceIdentityProvider(allowed_actors=frozenset({"aad:other:user"}))
    with pytest.raises(AuthorizationError):
        denied.resolve(_request_with_headers({"x-ms-client-principal": encoded}))


def test_ui_typing_and_save_wiring_source_contracts() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "cvs_review_portal" / "web"
    js = (root / "app.js").read_text(encoding="utf-8")
    assert "currentIdentity: currentDatasetIdentity" in js
    assert "function updateCardDraftChromeInPlace" in js
    assert "history-btn" not in js
    assert "openHistory" not in js
    assert "BANNER_UNCONFIRMED" in js
    logic = (root / "review_save_logic.mjs").read_text(encoding="utf-8")
    assert "executeSaveComment" in logic
    assert "Save could not be confirmed" in logic
    assert "findMatchingReceipt" not in logic
