# CVS Review Portal

## Project Overview

The **CVS Review Portal** displays exported datasets and CVS Engine execution results and persists **comments-only** human reviews. The CVS Engine (preprocessing, inference, metrics) is a separate application. Ground truth is read-only in this portal.

This repository implements **Step 3**: comments-only Save, audit history, concurrency control, injectable identity, and an Azure Blob Storage adapter alongside the local filesystem store.

## Current Scope

- FastAPI application via `create_app(settings)` (`src/cvs_review_portal`)
- Validated settings for environment, storage backend, and identity mode
- Portal API under `/api` (datasets, runs, summary, raw images, review GET/PUT, history)
- Portal UI at [http://127.0.0.1:18080/](http://127.0.0.1:18080/) (packaged HTML/CSS/JS)
- Local filesystem store (default) and configurable Azure Blob adapter
- Development identity (loopback) and Azure App Service header identity adapters
- Reproducible synthetic demo generator (`scripts/generate_demo_data.py`)
- System endpoints: `/health`, `/ready`, `/version` (intentionally open)
- Quality gates: Ruff lint, Ruff format, Pyright strict, pytest

Canonical product specification: `.ai/cvs-review-portal/08_portal_specification.md`.

## Requirements

- Python 3.11.x
- Poetry 2.x
- Docker Desktop is optional and **not** required for local Step 3 work

## Local Setup (Windows PowerShell)

```powershell
poetry config virtualenvs.in-project true
poetry install
```

Create a local `.env` from the safe example (required for local UI access):

```powershell
Copy-Item .env.example .env
```

Ensure at least:

```text
IDENTITY_MODE=development
DEVELOPMENT_ACTOR=local-dev-reviewer
ALLOWED_ACTORS=local-dev-reviewer
STORAGE_BACKEND=local
DATA_ROOT=demo-data
```

Development identity is **not** production authentication and is limited to loopback clients. It is never enabled automatically merely because production identity is absent.

### Generate demo data (required before first portal demo)

```powershell
poetry run python scripts/generate_demo_data.py
```

This writes a synthetic CVS surgical-demo bundle under `demo-data/`. The generator refuses to overwrite a nonempty target and never deletes existing files.

## Environment Configuration

| Variable | Allowed values | Default |
| --- | --- | --- |
| `APP_ENV` | `local`, `dev`, `staging`, `prod` | `local` |
| `APP_VERSION` | non-empty string | `0.1.0` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO` |
| `DATA_ROOT` | path to portal data root (local backend) | `demo-data` |
| `STORAGE_BACKEND` | `local`, `azure_blob` | `local` |
| `AZURE_STORAGE_ACCOUNT_URL` | Blob account URL | unset (required for `azure_blob`) |
| `AZURE_BLOB_CONTAINER` | private container name | unset (required for `azure_blob`) |
| `IDENTITY_MODE` | `disabled`, `development`, `azure_app_service` | `disabled` |
| `DEVELOPMENT_ACTOR` | server-configured actor | unset (required for `development`) |
| `ALLOWED_ACTORS` | comma-separated actors | empty (required for `azure_app_service`) |

Invalid values raise a validation error at startup; there is no silent fallback. Selecting `azure_blob` without Azure settings does **not** fall back to local data.

Azure layout uses one private container with prefixes `raw-images/`, `runs-output/`, and `reviews/`. Credentials use Azure Identity (managed identity intended for deployment). Images are served only through the application endpoint — no public containers or browser SAS links.

`/ready` reports process configuration readiness only. It does **not** establish Azure connectivity or dataset readiness.

## Run Locally

```powershell
.\scripts\dev.ps1
```

or:

```powershell
poetry run uvicorn cvs_review_portal.main:app --host 127.0.0.1 --port 18080 --reload
```

Open the portal UI:

**[http://127.0.0.1:18080/](http://127.0.0.1:18080/)**

API docs remain at [http://127.0.0.1:18080/docs](http://127.0.0.1:18080/docs).

## Comments-only Save (summary)

- Save request: `{ "comments": "...", "expected_revision": 0, "request_id": "<uuid>" }`
- Max comment length: **8000** characters (backend + UI; never truncated)
- Revision `0` = no persisted review yet
- Backend supplies actor + UTC timestamp
- Schema v2 review documents store current state, history, and request-ID receipts atomically
- Legacy schema v1 reviews remain readable; first Save imports them as a baseline
- Identical retry with the same `request_id` does not create a duplicate revision
- Distinguishes “this operation committed” (`committed_revision`) from “still current” (`is_current`)

## Quality Checks

```powershell
.\scripts\lint.ps1
.\scripts\format-check.ps1
.\scripts\typecheck.ps1
.\scripts\test.ps1
.\scripts\quality.ps1
```

## Remaining Azure / deployment work

Not done in Step 3 application code:

1. Provision private Blob container and upload owner datasets
2. Configure managed identity / App Service authentication
3. Set `STORAGE_BACKEND=azure_blob`, account URL, container, `IDENTITY_MODE=azure_app_service`, and `ALLOWED_ACTORS`
4. Verify end-to-end cloud login and Blob access in the authorized environment

## Repository Documentation

- Current specification: `.ai/cvs-review-portal/08_portal_specification.md`
- Engineering standards: `.ai/cvs-review-portal/05_code_quality_standards.md`
- Handoff: `.ai/cvs-review-portal/06_common_handoff.md`
- Code map: `.ai/cvs-review-portal/07_code_map.md`

## Current Non-Goals

Ground-truth editing UI/sub-portal, Engine logic, AWS/OpenSearch/databases, Azure resource provisioning, and cloud deployment verification.

When packaging a repository ZIP for review, include the demo generator and `src/cvs_review_portal/web/`; exclude `.env`, `.venv`, credentials, and caches.
