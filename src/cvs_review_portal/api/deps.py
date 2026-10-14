"""FastAPI dependencies for portal routes, storage, and identity."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request

from cvs_review_portal.application.identity import AuthenticatedPrincipal, IdentityProvider
from cvs_review_portal.application.portal_service import PortalReadService
from cvs_review_portal.application.ports import PortalDataStore
from cvs_review_portal.application.review_service import PortalReviewService
from cvs_review_portal.domain.errors import AuthenticationError, ConfigurationError
from cvs_review_portal.infrastructure.azure_blob_store import AzureBlobPortalDataStore
from cvs_review_portal.infrastructure.identity_azure import AzureAppServiceIdentityProvider
from cvs_review_portal.infrastructure.identity_dev import DevelopmentIdentityProvider
from cvs_review_portal.infrastructure.local_store import LocalPortalDataStore
from cvs_review_portal.settings import Settings


def get_current_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_portal_store(request: Request) -> PortalDataStore:
    store = getattr(request.app.state, "portal_store", None)
    if store is None:
        store = build_portal_store(cast(Settings, request.app.state.settings))
        request.app.state.portal_store = store
    return cast(PortalDataStore, store)


def get_identity_provider(request: Request) -> IdentityProvider:
    provider = getattr(request.app.state, "identity_provider", None)
    if provider is None:
        provider = build_identity_provider(cast(Settings, request.app.state.settings))
        request.app.state.identity_provider = provider
    return cast(IdentityProvider, provider)


def get_portal_service(
    store: Annotated[PortalDataStore, Depends(get_portal_store)],
) -> PortalReadService:
    return PortalReadService(store)


def get_review_service(
    store: Annotated[PortalDataStore, Depends(get_portal_store)],
) -> PortalReviewService:
    return PortalReviewService(store)


def build_portal_store(settings: Settings) -> PortalDataStore:
    if settings.storage_backend == "local":
        return LocalPortalDataStore(settings.data_root)
    if settings.storage_backend == "azure_blob":
        account_url = settings.azure_storage_account_url
        container = settings.azure_blob_container
        if not account_url or not container:
            raise ConfigurationError(
                "Azure Blob storage is not configured.",
                safe_context="storage=azure_blob",
            )
        return AzureBlobPortalDataStore(
            account_url=account_url,
            container_name=container,
        )
    raise ConfigurationError(
        "Unsupported storage backend.",
        safe_context=f"storage_backend={settings.storage_backend}",
    )


def build_identity_provider(settings: Settings) -> IdentityProvider:
    if settings.identity_mode == "disabled":
        return _DisabledIdentityProvider()
    if settings.identity_mode == "development":
        actor = settings.development_actor
        if not actor:
            raise ConfigurationError(
                "DEVELOPMENT_ACTOR is required for development identity.",
                safe_context="identity=development",
            )
        allowed = settings.allowed_actor_set() or frozenset({actor.strip()})
        return DevelopmentIdentityProvider(actor=actor, allowed_actors=allowed)
    if settings.identity_mode == "azure_app_service":
        return AzureAppServiceIdentityProvider(allowed_actors=settings.allowed_actor_set())
    raise ConfigurationError(
        "Unsupported identity mode.",
        safe_context=f"identity_mode={settings.identity_mode}",
    )


class _DisabledIdentityProvider:
    """Fail-closed identity: login/access denied until a mode is explicitly enabled."""

    def resolve(self, request: object) -> AuthenticatedPrincipal:
        raise AuthenticationError(
            "Identity is not configured for this application instance.",
            safe_context="identity=disabled",
        )
