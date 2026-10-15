# 07 — Code Map

Maps current behavior to repository paths. Product rules live in [08_portal_specification.md](08_portal_specification.md). Commands and the Docker context gap live in [../../README.md](../../README.md). Checkpoint status lives in [06_common_handoff.md](06_common_handoff.md).

Inherited `00_*`, `01_*`, `02_*`, and `04_*` files are legacy template content.

```text
CURRENT          → implemented in this repository
PLANNED          → described for later; not implemented
NOT_IMPLEMENTED  → explicitly absent
```

---

## 1. Behavior to path

| Behavior | Path |
| --- | --- |
| Domain contracts, binary labels, provenance, catalog rules | `src/cvs_review_portal/domain/models.py` |
| Identifier and storage-key rules | `src/cvs_review_portal/domain/identifiers.py` |
| Comment length 8000; review JSON byte cap | `src/cvs_review_portal/domain/constants.py` |
| Review read projection (schema v1 and readable v2) | `src/cvs_review_portal/domain/review_document.py` |
| Typed portal errors | `src/cvs_review_portal/domain/errors.py` |
| Storage and identity ports | `src/cvs_review_portal/application/ports.py`, `src/cvs_review_portal/application/identity.py` |
| Interval grouping, order, titles, video/image search | `src/cvs_review_portal/application/interval_index.py` |
| Read use cases: browse, intervals, frame view, run overview, summary | `src/cvs_review_portal/application/portal_service.py` |
| Read response models | `src/cvs_review_portal/application/views.py` |
| Comments-only Save and revision check | `src/cvs_review_portal/application/review_service.py` |
| Cholec80 join, unused rows, overlap conflicts, copy, catalog-last write | `src/cvs_review_portal/importers/cholec80.py`, `scripts/import_cholec80.py` |
| Local files, atomic review write, review path | `src/cvs_review_portal/infrastructure/local_store.py` |
| Azure Blob adapter (same prefixes; ETag conditional writes) | `src/cvs_review_portal/infrastructure/azure_blob_store.py` |
| Review JSON codec | `src/cvs_review_portal/infrastructure/review_codec.py` |
| Path containment | `src/cvs_review_portal/infrastructure/paths.py` |
| Loopback development identity | `src/cvs_review_portal/infrastructure/identity_dev.py` |
| Azure App Service header identity (`aad:{tid}:{oid}`) | `src/cvs_review_portal/infrastructure/identity_azure.py` |
| Settings and fail-closed validation | `src/cvs_review_portal/settings.py` |
| App factory, open probes, protected routes | `src/cvs_review_portal/main.py` |
| Store and identity construction | `src/cvs_review_portal/api/deps.py` |
| JSON + same-origin mutation guard | `src/cvs_review_portal/api/auth.py` |
| HTTP routes | `src/cvs_review_portal/api/portal.py` |
| Save request/response models | `src/cvs_review_portal/api/review_schemas.py` |
| Image `Cache-Control` / ETag / `304` | `src/cvs_review_portal/api/image_cache.py` |
| UI package mount (`/` and `/ui-assets`; data root not mounted) | `src/cvs_review_portal/api/ui.py` |
| HTML shell and script registration | `src/cvs_review_portal/web/index.html` |
| Cards, picker, paging, thumbnails, summary button, draft memory | `src/cvs_review_portal/web/app.js` |
| Save outcomes: conflict, unconfirmed, draft preservation | `src/cvs_review_portal/web/review_save_logic.mjs` |
| Registers Save logic as `globalThis.CvsReviewSaveLogic` | `src/cvs_review_portal/web/register_save_logic.mjs` |
| Interval async guards, revision reconcile, Previous/Next index | `src/cvs_review_portal/web/interval_browse_logic.mjs` |
| Registers interval logic as `globalThis.CvsIntervalBrowseLogic` | `src/cvs_review_portal/web/register_interval_browse_logic.mjs` |
| Styles | `src/cvs_review_portal/web/styles.css` |
| Synthetic demo bundle | `scripts/generate_demo_data.py` |
| Local server on port 18080 | `scripts/dev.ps1` |
| Container port 8000, no data copy | `Dockerfile`, `docker-compose.yaml`, `.dockerignore` |

`index.html` loads the modules in this order:

```html
<script type="module" src="/ui-assets/register_save_logic.mjs"></script>
<script type="module" src="/ui-assets/register_interval_browse_logic.mjs"></script>
<script src="/ui-assets/app.js" defer></script>
```

`app.js` calls the registered module functions. The `.mjs` files are the production logic under test in `tests/js/`.

---

## 2. Layout

```text
src/cvs_review_portal/
  domain/           contracts and invariants
  application/      read services, interval index, review writes, ports
  infrastructure/   local store, Azure Blob store, identity adapters
  api/              HTTP, auth, image cache headers, UI registration
  web/              HTML, CSS, app.js, production .mjs modules
  importers/        offline Cholec80 preparation
scripts/            demo generator, import CLI, quality and dev PowerShell
tests/              pytest
tests/js/           node:test for production Save and interval modules
```

Factory: `create_app` in `src/cvs_review_portal/main.py`. Uvicorn entry: `cvs_review_portal.main:app`.

Open routes: `/health`, `/ready`, `/version`, `/docs`, `/openapi.json`, `/redoc`. `/ready` reports process configuration only.

Protected routes: `/`, `/ui-assets/*`, `/api/*`.

---

## 3. API routes

| Method | Path | Status |
| --- | --- | --- |
| GET | `/` | CURRENT |
| GET | `/ui-assets/*` | CURRENT |
| GET | `/health`, `/ready`, `/version` | CURRENT (open) |
| GET | `/api/datasets` | CURRENT |
| GET | `/api/datasets/{dataset_id}/versions/{dataset_version}` | CURRENT |
| GET | `/api/datasets/.../browse` | CURRENT |
| GET | `/api/datasets/.../intervals` | CURRENT |
| GET | `/api/datasets/.../intervals/search` | CURRENT |
| GET | `/api/datasets/.../intervals/{segment_id}/frames` | CURRENT |
| GET | `/api/datasets/.../images/{image_id}/view` | CURRENT |
| GET | `/api/datasets/.../images/{image_id}/content` | CURRENT (private cache + ETag) |
| GET | `/api/datasets/.../images/{image_id}/review` | CURRENT |
| PUT | `/api/datasets/.../images/{image_id}/review` | CURRENT |
| GET | `/api/datasets/.../summary` | CURRENT |
| GET | `/api/runs` | CURRENT |
| GET | `/api/runs/{run_id}` | CURRENT |
| GET | `/api/runs/{run_id}/overview` | CURRENT |

Default interval page size is 24 (`limit` 1–100) in `api/portal.py` and `PICKER_PAGE_SIZE` in `app.js`.

---

## 4. Tests

| Path | Focus |
| --- | --- |
| `tests/test_review_save.py` | Save, empty comment, reload, ground-truth preservation, stale revision, cross-process conflict |
| `tests/test_step3_corrections.py` | UI Save wiring, history absent |
| `tests/js/save_async_guards.test.mjs` | Production Save logic |
| `tests/js/interval_nav_save.test.mjs` | Stale dataset response, revision reconcile, navigation/Save isolation |
| `tests/test_interval_browse.py` | Grouping, order, search, browse APIs |
| `tests/test_image_content_cache.py` | Cache-Control, ETag, 304, error `no-store` |
| `tests/test_cholec80_import.py` | Join, unused rows, dry-run, empty destination |
| `tests/test_ui_readonly_gt.py` | Read-only ground truth |
| `tests/test_azure_blob_store.py` | Conditional Blob writes (mocked SDK) |
| `tests/test_portal_api.py` | Publication boundary |
| `tests/test_settings.py` | Settings validation |

---

## 5. Not in this repository

| Item | Status |
| --- | --- |
| Azure account, storage resources, upload, Easy Auth, deployment, live verification | PLANNED |
| Performance changes for search and frame navigation | Deferred; limitation still open |
| Ground-truth editing sub-portal | NOT_IMPLEMENTED |
| Audit history UI/API | NOT_IMPLEMENTED |
| Separate thumbnail files | NOT_IMPLEMENTED |
| Inference runs for the imported Cholec80 dataset | NOT_IMPLEMENTED (catalog `runs` is empty) |
