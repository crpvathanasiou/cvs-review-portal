"""Application factory and Uvicorn entry point for CVS Review Portal."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from cvs_review_portal.api.deps import build_identity_provider, build_portal_store
from cvs_review_portal.api.portal import router as portal_router
from cvs_review_portal.api.system import router as system_router
from cvs_review_portal.api.ui import register_ui
from cvs_review_portal.domain.errors import AuthenticationError, AuthorizationError
from cvs_review_portal.logging_config import configure_logging
from cvs_review_portal.settings import Settings, get_settings

logger = logging.getLogger("cvs_review_portal.main")

# System endpoints remain intentionally open for liveness/readiness probes.
_OPEN_PATHS = frozenset({"/health", "/ready", "/version", "/docs", "/openapi.json", "/redoc"})


class PortalAccessMiddleware(BaseHTTPMiddleware):
    """Protect portal/UI/data routes consistently; leave health endpoints open."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path in _OPEN_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        provider = getattr(request.app.state, "identity_provider", None)
        if provider is None:
            provider = build_identity_provider(request.app.state.settings)
            request.app.state.identity_provider = provider
        try:
            provider.resolve(request)
        except AuthenticationError as exc:
            return JSONResponse(
                status_code=401,
                content={"detail": {"message": str(exc), "context": exc.safe_context}},
            )
        except AuthorizationError as exc:
            return JSONResponse(
                status_code=403,
                content={"detail": {"message": str(exc), "context": exc.safe_context}},
            )
        return await call_next(request)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure a FastAPI application instance.

    Injected settings always win; the cached default provider is consulted only
    when nothing is injected. No network calls, clients, or workers are created
    at import time. Filesystem/Blob reads for portal data are deferred to request
    handling. Packaged UI assets are registered from the installed package path.
    """
    resolved = settings if settings is not None else get_settings()
    configure_logging(resolved.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        store = build_portal_store(resolved)
        identity = build_identity_provider(resolved)
        app.state.portal_store = store
        app.state.identity_provider = identity
        try:
            yield
        finally:
            close = getattr(store, "close", None)
            if callable(close):
                close()

    app = FastAPI(title="CVS Review Portal", version=resolved.app_version, lifespan=lifespan)
    app.state.settings = resolved
    app.add_middleware(PortalAccessMiddleware)
    app.include_router(system_router)
    app.include_router(portal_router)
    register_ui(app)

    logger.info(
        "application_created service=cvs-review-portal environment=%s version=%s "
        "data_root=%s storage_backend=%s identity_mode=%s",
        resolved.app_env,
        resolved.app_version,
        resolved.data_root,
        resolved.storage_backend,
        resolved.identity_mode,
    )
    return app


app = create_app()
