"""Unit tests for Azure Blob conditional review create/update mapping (mocked SDK)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import HttpResponseError, ResourceExistsError

from cvs_review_portal.application.ports import ReviewWriteCommit
from cvs_review_portal.domain.errors import StorageConflictError
from cvs_review_portal.domain.models import ReviewRecord
from cvs_review_portal.infrastructure.azure_blob_store import AzureBlobPortalDataStore
from cvs_review_portal.infrastructure.review_codec import serialize_review_record


def _record(*, revision: int = 1, comments: str = "c") -> ReviewRecord:
    return ReviewRecord(
        schema_version="1",
        dataset_id="ds-a",
        dataset_version="v1",
        image_id="b",
        ground_truth_override=None,
        comments=comments,
        revision=revision,
        actor="tester",
        updated_at=datetime.now(UTC),
    )


def test_conditional_create_uses_if_missing() -> None:
    store = AzureBlobPortalDataStore(
        account_url="https://example.blob.core.windows.net",
        container_name="portal",
        credential=object(),
    )
    blob = MagicMock()
    blob.download_blob.side_effect = __import__(
        "azure.core.exceptions", fromlist=["ResourceNotFoundError"]
    ).ResourceNotFoundError("missing")
    uploaded: dict[str, Any] = {}

    def upload_blob(*_args: object, **kwargs: object) -> None:
        uploaded.update(kwargs)

    blob.upload_blob.side_effect = upload_blob

    with patch.object(store, "_blob", return_value=blob):
        with patch.object(store, "load_review", return_value=None):
            result = store.mutate_review(
                "ds-a",
                "v1",
                "b",
                lambda _current: ReviewWriteCommit(record=_record()),
            )
    assert result.wrote is True
    assert uploaded.get("overwrite") is False
    assert str(uploaded.get("match_condition")).endswith("IfMissing")


def test_conditional_update_uses_etag_if_not_modified() -> None:
    store = AzureBlobPortalDataStore(
        account_url="https://example.blob.core.windows.net",
        container_name="portal",
        credential=object(),
    )
    payload = serialize_review_record(_record())
    download = MagicMock()
    download.readall.return_value = payload
    download.properties = SimpleNamespace(etag='"etag-1"')
    blob = MagicMock()
    blob.download_blob.return_value = download
    uploaded: dict[str, Any] = {}

    def upload_blob(*_args: object, **kwargs: object) -> None:
        uploaded.update(kwargs)

    blob.upload_blob.side_effect = upload_blob

    with patch.object(store, "_blob", return_value=blob):
        with patch.object(store, "load_review", return_value=None):
            store.mutate_review(
                "ds-a",
                "v1",
                "b",
                lambda _current: ReviewWriteCommit(record=_record(revision=2, comments="n")),
            )
    assert uploaded.get("overwrite") is True
    assert uploaded.get("etag") == '"etag-1"'
    assert str(uploaded.get("match_condition")).endswith("IfNotModified")


def test_precondition_conflict_mapped() -> None:
    store = AzureBlobPortalDataStore(
        account_url="https://example.blob.core.windows.net",
        container_name="portal",
        credential=object(),
    )
    blob = MagicMock()
    blob.download_blob.side_effect = __import__(
        "azure.core.exceptions", fromlist=["ResourceNotFoundError"]
    ).ResourceNotFoundError("missing")
    blob.upload_blob.side_effect = ResourceExistsError("exists")

    with patch.object(store, "_blob", return_value=blob):
        with pytest.raises(StorageConflictError):
            store.mutate_review(
                "ds-a",
                "v1",
                "b",
                lambda _current: ReviewWriteCommit(record=_record()),
            )


def test_etag_mismatch_mapped() -> None:
    store = AzureBlobPortalDataStore(
        account_url="https://example.blob.core.windows.net",
        container_name="portal",
        credential=object(),
    )
    payload = serialize_review_record(_record())
    download = MagicMock()
    download.readall.return_value = payload
    download.properties = SimpleNamespace(etag='"etag-1"')
    blob = MagicMock()
    blob.download_blob.return_value = download
    err = HttpResponseError("precondition")
    err.status_code = 412
    blob.upload_blob.side_effect = err

    with patch.object(store, "_blob", return_value=blob):
        with pytest.raises(StorageConflictError):
            store.mutate_review(
                "ds-a",
                "v1",
                "b",
                lambda _current: ReviewWriteCommit(record=_record(revision=2)),
            )
