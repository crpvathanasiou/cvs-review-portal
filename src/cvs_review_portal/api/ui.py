"""Portal UI routes and static asset registration.

Serves the Step 2 review interface from packaged files under
``cvs_review_portal/web/``. Paths resolve relative to this package, never from
the process working directory. Only the intended static-assets directory is
mounted — ``DATA_ROOT`` is never exposed as static content.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
INDEX_PATH = WEB_DIR / "index.html"
STATIC_MOUNT_PATH = "/ui-assets"

router = APIRouter(tags=["ui"])


@router.get("/")
def portal_index() -> FileResponse:
    """Serve the portal HTML shell."""
    return FileResponse(INDEX_PATH, media_type="text/html; charset=utf-8")


def register_ui(app: FastAPI) -> None:
    """Register the index route and mount local UI assets only."""
    if not WEB_DIR.is_dir():
        msg = f"Portal UI assets directory is missing: {WEB_DIR}"
        raise RuntimeError(msg)
    if not INDEX_PATH.is_file():
        msg = f"Portal UI index is missing: {INDEX_PATH}"
        raise RuntimeError(msg)

    app.include_router(router)
    app.mount(
        STATIC_MOUNT_PATH,
        StaticFiles(directory=str(WEB_DIR)),
        name="ui-assets",
    )
