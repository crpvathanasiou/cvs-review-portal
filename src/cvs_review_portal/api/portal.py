"""Portal HTTP routes under `/api` (reads + comments-only review writes)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import ValidationError

from cvs_review_portal.api.auth import require_json_mutation, require_principal
from cvs_review_portal.api.deps import get_portal_service, get_review_service
from cvs_review_portal.api.review_schemas import (
    GetReviewResponse,
    ReviewStateResponse,
    SaveCommentsRequest,
    SaveCommentsResponse,
)
from cvs_review_portal.application.identity import AuthenticatedPrincipal
from cvs_review_portal.application.portal_service import PortalReadService
from cvs_review_portal.application.review_service import PortalReviewService
from cvs_review_portal.application.views import (
    DatasetDetailView,
    DatasetListView,
    RunDetailView,
    RunListView,
    SummaryView,
)
from cvs_review_portal.domain.errors import (
    DataStoreUnavailableError,
    InvalidArtifactError,
    InvalidIdentifierError,
    PortalError,
    ResourceNotFoundError,
    ReviewConflictError,
    ReviewDocumentTooLargeError,
    ReviewMutationRejectedError,
)
from cvs_review_portal.domain.identifiers import validate_identifier
from cvs_review_portal.domain.review_document import LoadedReview

logger = logging.getLogger("cvs_review_portal.api.portal")

router = APIRouter(
    prefix="/api",
    tags=["portal"],
    dependencies=[Depends(require_principal)],
)


def _http_error(exc: PortalError, status_code: int) -> HTTPException:
    detail: dict[str, str] = {"message": str(exc)}
    if exc.safe_context:
        detail["context"] = exc.safe_context
    if isinstance(exc, ReviewConflictError):
        detail["conflict_kind"] = exc.conflict_kind
    return HTTPException(status_code=status_code, detail=detail)


def _review_state(loaded: LoadedReview) -> ReviewStateResponse:
    return ReviewStateResponse(
        ground_truth_override=loaded.ground_truth_override,
        comments=loaded.comments,
        revision=loaded.revision,
        actor=loaded.actor,
        updated_at=loaded.updated_at,
    )


@router.get("/datasets", response_model=DatasetListView)
def list_datasets(
    service: Annotated[PortalReadService, Depends(get_portal_service)],
) -> DatasetListView:
    try:
        return service.list_datasets()
    except DataStoreUnavailableError as exc:
        raise _http_error(exc, 503) from exc
    except InvalidArtifactError as exc:
        logger.exception("invalid_artifact op=list_datasets context=%s", exc.safe_context)
        raise _http_error(exc, 500) from exc
    except InvalidIdentifierError as exc:
        raise _http_error(exc, 422) from exc


@router.get(
    "/datasets/{dataset_id}/versions/{dataset_version}",
    response_model=DatasetDetailView,
)
def get_dataset(
    dataset_id: str,
    dataset_version: str,
    service: Annotated[PortalReadService, Depends(get_portal_service)],
) -> DatasetDetailView:
    try:
        validate_identifier(dataset_id, field="dataset_id")
        validate_identifier(dataset_version, field="dataset_version")
        return service.get_dataset(dataset_id, dataset_version)
    except ResourceNotFoundError as exc:
        raise _http_error(exc, 404) from exc
    except DataStoreUnavailableError as exc:
        raise _http_error(exc, 503) from exc
    except InvalidArtifactError as exc:
        logger.exception(
            "invalid_artifact op=get_dataset context=%s",
            exc.safe_context,
        )
        raise _http_error(exc, 500) from exc
    except InvalidIdentifierError as exc:
        raise _http_error(exc, 422) from exc


@router.get("/runs", response_model=RunListView)
def list_runs(
    service: Annotated[PortalReadService, Depends(get_portal_service)],
    dataset_id: Annotated[str | None, Query()] = None,
    dataset_version: Annotated[str | None, Query()] = None,
) -> RunListView:
    if (dataset_id is None) ^ (dataset_version is None):
        raise HTTPException(
            status_code=422,
            detail={
                "message": "dataset_id and dataset_version must be provided together.",
                "context": "filter=incomplete",
            },
        )
    try:
        return service.list_runs(dataset_id=dataset_id, dataset_version=dataset_version)
    except ResourceNotFoundError as exc:
        raise _http_error(exc, 404) from exc
    except DataStoreUnavailableError as exc:
        raise _http_error(exc, 503) from exc
    except InvalidArtifactError as exc:
        logger.exception("invalid_artifact op=list_runs context=%s", exc.safe_context)
        raise _http_error(exc, 500) from exc
    except InvalidIdentifierError as exc:
        raise _http_error(exc, 422) from exc


@router.get("/runs/{run_id}", response_model=RunDetailView)
def get_run(
    run_id: str,
    service: Annotated[PortalReadService, Depends(get_portal_service)],
) -> RunDetailView:
    try:
        validate_identifier(run_id, field="run_id")
        return service.get_run(run_id)
    except ResourceNotFoundError as exc:
        raise _http_error(exc, 404) from exc
    except DataStoreUnavailableError as exc:
        raise _http_error(exc, 503) from exc
    except InvalidArtifactError as exc:
        logger.exception("invalid_artifact op=get_run context=%s", exc.safe_context)
        raise _http_error(exc, 500) from exc
    except InvalidIdentifierError as exc:
        raise _http_error(exc, 422) from exc


@router.get(
    "/datasets/{dataset_id}/versions/{dataset_version}/summary",
    response_model=SummaryView,
)
def get_summary(
    dataset_id: str,
    dataset_version: str,
    service: Annotated[PortalReadService, Depends(get_portal_service)],
    run_id: Annotated[str | None, Query()] = None,
) -> SummaryView:
    try:
        validate_identifier(dataset_id, field="dataset_id")
        validate_identifier(dataset_version, field="dataset_version")
        if run_id is not None:
            validate_identifier(run_id, field="run_id")
        return service.get_summary(dataset_id, dataset_version, run_id=run_id)
    except ResourceNotFoundError as exc:
        raise _http_error(exc, 404) from exc
    except DataStoreUnavailableError as exc:
        raise _http_error(exc, 503) from exc
    except InvalidArtifactError as exc:
        logger.exception("invalid_artifact op=get_summary context=%s", exc.safe_context)
        raise _http_error(exc, 500) from exc
    except InvalidIdentifierError as exc:
        raise _http_error(exc, 422) from exc


@router.get(
    "/datasets/{dataset_id}/versions/{dataset_version}/images/{image_id}/content",
)
def get_image_content(
    dataset_id: str,
    dataset_version: str,
    image_id: str,
    service: Annotated[PortalReadService, Depends(get_portal_service)],
) -> Response:
    try:
        validate_identifier(dataset_id, field="dataset_id")
        validate_identifier(dataset_version, field="dataset_version")
        validate_identifier(image_id, field="image_id")
        content, media_type = service.get_image_content(dataset_id, dataset_version, image_id)
        return Response(content=content, media_type=media_type)
    except ResourceNotFoundError as exc:
        raise _http_error(exc, 404) from exc
    except DataStoreUnavailableError as exc:
        raise _http_error(exc, 503) from exc
    except InvalidArtifactError as exc:
        logger.exception(
            "invalid_artifact op=get_image_content context=%s",
            exc.safe_context,
        )
        raise _http_error(exc, 500) from exc
    except InvalidIdentifierError as exc:
        raise _http_error(exc, 422) from exc


@router.get(
    "/datasets/{dataset_id}/versions/{dataset_version}/images/{image_id}/review",
    response_model=GetReviewResponse,
)
def get_review(
    dataset_id: str,
    dataset_version: str,
    image_id: str,
    service: Annotated[PortalReviewService, Depends(get_review_service)],
) -> GetReviewResponse:
    try:
        validate_identifier(dataset_id, field="dataset_id")
        validate_identifier(dataset_version, field="dataset_version")
        validate_identifier(image_id, field="image_id")
        loaded = service.get_review(dataset_id, dataset_version, image_id)
        return GetReviewResponse(
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            image_id=image_id,
            persisted_revision=0 if loaded is None else loaded.revision,
            review=None if loaded is None else _review_state(loaded),
        )
    except ResourceNotFoundError as exc:
        raise _http_error(exc, 404) from exc
    except DataStoreUnavailableError as exc:
        raise _http_error(exc, 503) from exc
    except InvalidArtifactError as exc:
        logger.exception("invalid_artifact op=get_review context=%s", exc.safe_context)
        raise _http_error(exc, 500) from exc
    except InvalidIdentifierError as exc:
        raise _http_error(exc, 422) from exc


@router.put(
    "/datasets/{dataset_id}/versions/{dataset_version}/images/{image_id}/review",
    response_model=SaveCommentsResponse,
    dependencies=[Depends(require_json_mutation)],
)
def save_review_comments(
    dataset_id: str,
    dataset_version: str,
    image_id: str,
    body: SaveCommentsRequest,
    service: Annotated[PortalReviewService, Depends(get_review_service)],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
) -> SaveCommentsResponse:
    try:
        validate_identifier(dataset_id, field="dataset_id")
        validate_identifier(dataset_version, field="dataset_version")
        validate_identifier(image_id, field="image_id")
        result = service.save_comments(
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            image_id=image_id,
            comments=body.comments,
            expected_revision=body.expected_revision,
            actor=principal.actor,
        )
        return SaveCommentsResponse(
            current=_review_state(result.current),
            persisted_revision=result.current.revision,
        )
    except ResourceNotFoundError as exc:
        raise _http_error(exc, 404) from exc
    except ReviewConflictError as exc:
        raise _http_error(exc, 409) from exc
    except ReviewMutationRejectedError as exc:
        raise _http_error(exc, 422) from exc
    except ReviewDocumentTooLargeError as exc:
        raise _http_error(exc, 422) from exc
    except DataStoreUnavailableError as exc:
        raise _http_error(exc, 503) from exc
    except InvalidArtifactError as exc:
        logger.exception("invalid_artifact op=save_review context=%s", exc.safe_context)
        raise _http_error(exc, 500) from exc
    except InvalidIdentifierError as exc:
        raise _http_error(exc, 422) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail={"message": "Invalid mutation payload."}
        ) from exc
