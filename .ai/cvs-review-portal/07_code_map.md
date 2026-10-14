# 07 — Code Map

## 1. Purpose and Authority

Maps implemented responsibilities to repository locations. Updated after meaningful code changes.

Architectural/product authority for the portal is `08_portal_specification.md`. Inherited `00_*` / `01_*` / `02_*` / `04_*` files are legacy.

---

## 2. Status Legend

```text
CURRENT      → Exists now
PLANNED      → Documented for a later step, not implemented
NOT_IMPLEMENTED → Referenced capability absent
```

---

## 3. Current Repository Summary

Step 3 MVP finishing pass: comments-only Save (latest comment + revision concurrency), identity boundary, Azure Blob adapter, in-place UI draft chrome. No audit history UI/API.

* Package `src/cvs_review_portal/` with `domain/`, `application/`, `infrastructure/`, `api/`, `web/`
* Factory `create_app(settings)` with lifespan store/identity wiring; entry `cvs_review_portal.main:app`
* System routes `/health`, `/ready`, `/version` (intentionally open)
* Protected `/api/*`, `/`, `/ui-assets/*` via identity middleware
* Review write routes under `/api/.../review` and `/history`
* Settings: `DATA_ROOT`, `STORAGE_BACKEND`, Azure Blob URL/container, `IDENTITY_MODE`, actors

---

## 4. Application Code Map

| Path | Status | Responsibility |
| ---- | ------ | -------------- |
| `src/cvs_review_portal/main.py` | CURRENT | `create_app`; lifespan; access middleware |
| `src/cvs_review_portal/settings.py` | CURRENT | Local/Azure storage + identity settings |
| `src/cvs_review_portal/domain/constants.py` | CURRENT | Max comment length; max review document bytes |
| `src/cvs_review_portal/domain/models.py` | CURRENT | Schema v1 artifacts including `ReviewRecord` |
| `src/cvs_review_portal/domain/review_document.py` | CURRENT | LoadedReview projection; v2 read-compat models |
| `src/cvs_review_portal/domain/errors.py` | CURRENT | Auth, conflict, mutation, size, artifact, availability errors |
| `src/cvs_review_portal/application/ports.py` | CURRENT | `PortalDataStore` + atomic `mutate_review` (ReviewRecord write) |
| `src/cvs_review_portal/application/portal_service.py` | CURRENT | Read composition; `persisted_revision`; published-dataset lookup |
| `src/cvs_review_portal/application/review_service.py` | CURRENT | Comments-only Save; revision concurrency |
| `src/cvs_review_portal/application/identity.py` | CURRENT | Principal + IdentityProvider Protocol |
| `src/cvs_review_portal/infrastructure/local_store.py` | CURRENT | Local reads + filelock atomic review writes |
| `src/cvs_review_portal/infrastructure/azure_blob_store.py` | CURRENT | Blob reads + ETag conditional writes |
| `src/cvs_review_portal/infrastructure/review_codec.py` | CURRENT | Parse v1/v2; serialize v1 ReviewRecord |
| `src/cvs_review_portal/infrastructure/identity_dev.py` | CURRENT | Loopback development identity |
| `src/cvs_review_portal/infrastructure/identity_azure.py` | CURRENT | App Service identity; canonical `aad:{tid}:{oid}` |
| `src/cvs_review_portal/api/deps.py` | CURRENT | Store/identity/service DI builders |
| `src/cvs_review_portal/api/auth.py` | CURRENT | Principal dependency; JSON/CSRF mutation guard |
| `src/cvs_review_portal/api/portal.py` | CURRENT | Read + review write routes (no history) |
| `src/cvs_review_portal/api/review_schemas.py` | CURRENT | Save request/response models |
| `src/cvs_review_portal/web/review_save_logic.mjs` | CURRENT | Production Save-state (conflict / unconfirmed) |
| `src/cvs_review_portal/web/register_save_logic.mjs` | CURRENT | Exposes Save logic to classic `app.js` |
| `src/cvs_review_portal/web/*` | CURRENT | In-place draft chrome; Save/Discard; conflict/unconfirmed |

---

## 5. API and UI Routes

| Method | Path | Status |
| ------ | ---- | ------ |
| GET | `/` | CURRENT (portal HTML; auth-protected) |
| GET | `/ui-assets/*` | CURRENT (auth-protected) |
| GET | `/health` | CURRENT (open) |
| GET | `/ready` | CURRENT (open; not Azure/dataset readiness) |
| GET | `/version` | CURRENT (open) |
| GET | `/api/datasets` | CURRENT |
| GET | `/api/datasets/{dataset_id}/versions/{dataset_version}` | CURRENT (+ `persisted_revision`) |
| GET | `/api/runs` | CURRENT |
| GET | `/api/runs/{run_id}` | CURRENT |
| GET | `/api/datasets/.../summary` | CURRENT |
| GET | `/api/datasets/.../images/{image_id}/content` | CURRENT |
| GET | `/api/datasets/.../images/{image_id}/review` | CURRENT |
| PUT | `/api/datasets/.../images/{image_id}/review` | CURRENT (comments-only Save) |

---

## 6. Test Code Map

| Path | Status | Coverage focus |
| ---- | ------ | -------------- |
| `tests/test_review_save.py` | CURRENT | Save, empty, reload, GT preserve, stale conflict, cross-process concurrency |
| `tests/test_azure_blob_store.py` | CURRENT | Conditional create/update + conflict mapping (mocked SDK) |
| `tests/test_step3_corrections.py` | CURRENT | UI Save wiring, empty reload, history removed, actor/artifact checks |
| `tests/js/save_async_guards.test.mjs` | CURRENT | Production Save logic: run-switch, unconfirmed, conflict, draft preserve |
| `tests/test_portal_api.py` | CURRENT | Read composition / publication boundary |
| `tests/test_ui_readonly_gt.py` | CURRENT | Read-only GT + Save UI contracts |
| `tests/fixture_trees.py` | CURRENT | `make_settings` with development identity |

---

## 7. Planned (not implemented)

| Item | Status |
| ---- | ------ |
| Azure resource provisioning / deployment / Easy Auth cloud verification | PLANNED |
| Ground-truth creation/editing sub-portal | NOT_IMPLEMENTED |

---

## 8. Current Snapshot

```text
Ground truth: read-only in review portal
Comments: Save + history + concurrency + Step 3 corrections implemented locally
Storage: local + Azure Blob adapter (config-selected; no silent fallback)
Identity: explicit modes; Azure canonical aad:{tid}:{oid}; development loopback-only
Exact next action: owner local Save verification + external review of corrections before Azure setup
External approval: NOT CLAIMED
```
