# CVS Review Portal

The CVS Review Portal shows exported surgical datasets and any published CVS Engine results, and it stores **comments-only** human reviews. Ground truth stays read-only. The CVS Engine (preprocessing, inference, metrics) is a separate application.

The current MVP includes comments-only Save, a local filesystem store, an Azure Blob adapter, development and Azure App Service identity adapters, browser caching of raw image bytes, an offline Cholec80 importer, and interval browsing for provenance-backed datasets. Step 2B is owner-accepted for this MVP. Search and frame-navigation latency remain an open limitation. Azure account setup, upload, and deployment have not started.

Local portal used for that acceptance: [http://127.0.0.1:18080/](http://127.0.0.1:18080/).

## Reading order

Read these in order. Each topic has one canonical home; other files link to it.

| Order | Document | Owns |
| --- | --- | --- |
| 1 | This README | How to install, import, run, stop, and build the container |
| 2 | [Product specification](.ai/cvs-review-portal/08_portal_specification.md) | Purpose, MVP scope, behavior, contracts |
| 3 | [Code map](.ai/cvs-review-portal/07_code_map.md) | Where each behavior is implemented |
| 4 | [Handoff](.ai/cvs-review-portal/06_common_handoff.md) | Owner acceptance, evidence classes, dataset checkpoint, next action |
| 5 | [Engineering standards](.ai/cvs-review-portal/05_code_quality_standards.md) | Lint, types, tests, and review rules |

Legacy template documents describe a different compliance/OpenSearch/AWS product. Do not implement from them:

- [00_project_reference.md](.ai/cvs-review-portal/00_project_reference.md)
- [00_project_reference_compact.md](.ai/cvs-review-portal/00_project_reference_compact.md)
- [01_data_ingest_reference.md](.ai/cvs-review-portal/01_data_ingest_reference.md)
- [02_data_monitoring_reference.md](.ai/cvs-review-portal/02_data_monitoring_reference.md)
- [04_implementation_roadmap.md](.ai/cvs-review-portal/04_implementation_roadmap.md)

There is no separate architecture-decision file. The proceed-to-Azure decision is recorded in the [handoff](.ai/cvs-review-portal/06_common_handoff.md).

## Topic index

| Topic | Canonical section |
| --- | --- |
| Purpose and current MVP scope | [Specification §1](.ai/cvs-review-portal/08_portal_specification.md#1-purpose-and-current-mvp-scope) |
| Implemented capabilities and deferred features | [Specification §1](.ai/cvs-review-portal/08_portal_specification.md#1-purpose-and-current-mvp-scope) |
| Architecture and responsibilities | [Specification §2](.ai/cvs-review-portal/08_portal_specification.md#2-architecture) and [code map](.ai/cvs-review-portal/07_code_map.md) |
| Inputs, ground-truth matching, import outputs | [Specification §5.2.1](.ai/cvs-review-portal/08_portal_specification.md#521-cholec80-export-preparation) |
| Technical IDs and display IDs | [Specification §5.2.2](.ai/cvs-review-portal/08_portal_specification.md#522-technical-ids-and-display-ids) |
| Interval cards, search, Previous/Next, thumbnails | [Specification §7.4](.ai/cvs-review-portal/08_portal_specification.md#74-interval-browse) |
| Read-only ground truth and comments-only Save | [Specification §5.7–§5.8](.ai/cvs-review-portal/08_portal_specification.md#57-shared-review) and [§7.2](.ai/cvs-review-portal/08_portal_specification.md#72-interaction-model) |
| Drafts, conflicts, unconfirmed Save | [Specification §7.2](.ai/cvs-review-portal/08_portal_specification.md#72-interaction-model) |
| Metadata-first browsing and explicit summary | [Specification §7.4](.ai/cvs-review-portal/08_portal_specification.md#74-interval-browse) |
| Browser cache behavior and limits | [Specification §6.3](.ai/cvs-review-portal/08_portal_specification.md#63-image-content-browser-caching) |
| Local versus Azure storage, configuration, authentication | [Specification §6.1–§6.2](.ai/cvs-review-portal/08_portal_specification.md#61-storage-backends) |
| No inference runs for imported Cholec80 | [Specification §5.2.1](.ai/cvs-review-portal/08_portal_specification.md#521-cholec80-export-preparation) |
| Persisted comments versus browser memory | [Persisted state](#persisted-state-and-browser-memory) below |
| Owner acceptance, counts, paths, next Azure step | [Handoff](.ai/cvs-review-portal/06_common_handoff.md) |

## Requirements

- Python 3.11.x (`pyproject.toml` allows `>=3.11,<3.12`)
- Poetry 2.x. Docker and GitHub Actions install Poetry **2.2.1**
- A local `.env` created from [`.env.example`](.env.example). Do not commit `.env`
- Docker Desktop is optional. It is not required for the accepted local portal

Node.js is not required to run the portal. There is no frontend build.

## Install

From the repository root in Windows PowerShell:

```powershell
poetry config virtualenvs.in-project true
poetry install
Copy-Item .env.example .env
```

`poetry install` installs runtime and development dependencies from `pyproject.toml` / `poetry.lock`, including FastAPI, Uvicorn, Pydantic Settings, filelock, azure-storage-blob, azure-identity, openpyxl, pytest, Ruff, and Pyright.

The example `.env` enables loopback development identity and local storage with `DATA_ROOT=demo-data`. Development identity is not production authentication. It is not enabled merely because Azure identity is absent. Invalid settings fail at startup.

This install sequence matches the current project files. It was used to create the existing local `.venv`. It was not re-run for this documentation checkpoint.

## Quality gates

```powershell
.\scripts\lint.ps1
.\scripts\format-check.ps1
.\scripts\typecheck.ps1
.\scripts\test.ps1
.\scripts\quality.ps1
```

Those scripts run, in order when using `quality.ps1`:

```powershell
poetry run ruff check .
poetry run ruff format --check .
poetry run pyright
poetry run pytest
```

`.\scripts\format.ps1` applies Ruff formatting. It is not part of the check gate.

Previously recorded results, not re-executed for this documentation checkpoint: Ruff check, Ruff format check, Pyright (0 errors), and pytest (including `tests/test_interval_browse.py`) exited 0.

JavaScript guard tests are outside `scripts/quality.ps1`. Previously recorded, and not re-executed here: `node --check` on the web modules, and `node --test` with 19 passed (`tests/js/save_async_guards.test.mjs`, `tests/js/interval_nav_save.test.mjs`). PowerShell commands:

```powershell
node --check src/cvs_review_portal/web/app.js
node --check src/cvs_review_portal/web/review_save_logic.mjs
node --check src/cvs_review_portal/web/register_save_logic.mjs
node --check src/cvs_review_portal/web/interval_browse_logic.mjs
node --check src/cvs_review_portal/web/register_interval_browse_logic.mjs
node --test tests/js/save_async_guards.test.mjs tests/js/interval_nav_save.test.mjs
```

## Import

The importer is `scripts/import_cholec80.py`. Behavior is specified in [§5.2.1](.ai/cvs-review-portal/08_portal_specification.md#521-cholec80-export-preparation). The destination must be a new empty directory. A nonempty destination is refused for both `--dry-run` and a copying import. Existing files are left in place.

The completed Cholec80 import already occupies `C:\Users\User\cvs-review-portal\cholec80-data`. Repeating these commands with that destination will be refused. Use a different empty folder for another import.

Dry-run (validates and prints counts; writes nothing when the destination is absent or empty):

```powershell
poetry run python scripts/import_cholec80.py `
  --export-root "C:\Users\User\surgical-exports\data\frames-cholec80-all-1fps-jpeg90-run-001" `
  --ground-truth-xlsx "C:\Users\User\surgical-exports\configs\cholec80-CVS.xlsx" `
  --destination "C:\Users\User\cvs-review-portal\cholec80-data-new" `
  --dataset-id cholec80 `
  --dataset-version v1 `
  --dry-run
```

Copying import: the same command without `--dry-run`.

The real import into `cholec80-data` was completed in Step 2A. These commands were not re-executed for this documentation checkpoint. Counts and paths are in the [handoff](.ai/cvs-review-portal/06_common_handoff.md).

## Start with demo data

Generate the synthetic bundle once. The generator refuses a nonempty `demo-data` directory and does not delete existing files.

```powershell
poetry run python scripts/generate_demo_data.py
.\scripts\dev.ps1
```

`scripts/dev.ps1` runs:

```powershell
poetry run uvicorn cvs_review_portal.main:app --host 127.0.0.1 --port 18080 --reload
```

Open [http://127.0.0.1:18080/](http://127.0.0.1:18080/). API docs: [http://127.0.0.1:18080/docs](http://127.0.0.1:18080/docs).

With `DATA_ROOT=demo-data` in `.env`, and no session override, this serves the synthetic datasets. Demo generation and this launch path were used in earlier steps. They were not re-executed for this documentation checkpoint.

## Start with imported Cholec80 data

Keep identity and storage settings in `.env` (from `.env.example`). Override only the data root in the current PowerShell session. Pydantic Settings gives process environment variables precedence over `.env`.

```powershell
$env:DATA_ROOT = "C:\Users\User\cvs-review-portal\cholec80-data"
poetry run uvicorn cvs_review_portal.main:app --host 127.0.0.1 --port 18080 --reload
```

Open [http://127.0.0.1:18080/](http://127.0.0.1:18080/). The accepted owner session used this host and port with dataset `cholec80` / `v1`.

`--reload` watches code files. It does not reload a changed `DATA_ROOT`. Stop the process and start it again after changing the variable.

## Stop, restart, and clear the session override

Stop the server with Ctrl+C in the PowerShell window that is running Uvicorn.

To serve `DATA_ROOT` from `.env` again, clear the session variable in that same window and start the server again:

```powershell
Remove-Item Env:DATA_ROOT
poetry run uvicorn cvs_review_portal.main:app --host 127.0.0.1 --port 18080 --reload
```

A new PowerShell window does not inherit `$env:DATA_ROOT` from the previous window. Closing the window also drops the override. The `.env` file is unchanged by `Remove-Item Env:DATA_ROOT`.

## Persisted state and browser memory

Comments that Save succeeds in writing are JSON files under the active data root:

```text
<DATA_ROOT>/reviews/<dataset_id>/<dataset_version>/<image_id>.json
```

For the imported dataset that is:

```text
C:\Users\User\cvs-review-portal\cholec80-data\reviews\cholec80\v1\<image_id>.json
```

The importer does not create this directory. The local store creates it on the first Save for an image. A sibling `<image_id>.json.lock` file may remain from the cross-process file lock. That lock file is not the review.

Ground truth, provenance, and image membership stay in `runs-output/datasets/<dataset_id>/<dataset_version>/dataset.json`. Save does not edit that file.

These values exist only in the browser tab (no `localStorage` / `sessionStorage`):

- comment drafts
- conflict and unconfirmed Save UI state
- which interval cards are open and which frame is selected
- picker query and page
- a summary that was loaded in the tab

Refresh or closing the tab drops that memory. A comment that was successfully saved is still in the review JSON file. The owner observed that persistence after refresh. Drafts that were not saved are gone after refresh.

## Docker

The container listens on **port 8000**. That is the port in the Dockerfile `EXPOSE`, `HEALTHCHECK`, `CMD`, and in `docker-compose.yaml` (`8000:8000`). It is not port 18080.

Compose sets only:

```text
APP_ENV=${APP_ENV:-local}
APP_VERSION=${APP_VERSION:-0.1.0}
LOG_LEVEL=${LOG_LEVEL:-INFO}
```

The Dockerfile and Compose file declare **no volumes**. The image build copies `pyproject.toml`, `poetry.lock`, `README.md`, and `src/`. It does not copy `demo-data/` or `cholec80-data/`.

Commands that match those files:

```powershell
docker build -t cvs-review-portal:local .
docker compose up --build
```

`.\scripts\docker-up.ps1` runs `docker compose up --build`. Stop with:

```powershell
docker compose down
```

`.\scripts\docker-down.ps1` runs that. The process command is:

```text
uvicorn cvs_review_portal.main:app --host 0.0.0.0 --port 8000 --workers 2
```

**These Docker commands were not executed for this checkpoint.** There is no local Docker smoke-test result to record. The GitHub Actions workflow file contains `docker build -t cvs-review-portal:ci .`; this checkpoint did not read a CI run result.

### Build context and the local dataset

Build context for both `docker build .` and Compose is the repository root. `.dockerignore` excludes `.env`, `.venv`, `.git`, caches, `.ai/`, and `/cholec80-data/`. The imported dataset stays out of the Docker build context. The Dockerfile still does not copy that directory into an image layer.

`demo-data/` remains outside `.dockerignore` and is tracked. `.env` is excluded, so the owner’s `.env` is not part of the build context.

`.gitignore` excludes `/cholec80-data/`. `git check-ignore` matches `cholec80-data/`. No files under that directory are tracked.

### What a stock container still cannot do

`docker compose up --build` uses the defaults in `settings.py` when the extra variables are unset:

- `IDENTITY_MODE=disabled`, so `/`, `/ui-assets`, and `/api` fail closed (`401`). `/health` stays open, so the Compose healthcheck can pass while the portal UI is unusable.
- `STORAGE_BACKEND=local` and `DATA_ROOT=demo-data`, with no mounted data root, so the container has no catalog.
- Development identity (`src/cvs_review_portal/infrastructure/identity_dev.py`) accepts only loopback client hosts `127.0.0.1`, `::1`, `localhost`, and `testclient`. A browser reaching a published container port is not that loopback client inside the container.

Azure App Service identity is the deployment mode. It requires the hosting layer described in the [specification](.ai/cvs-review-portal/08_portal_specification.md#62-identity-modes). It is not a local Docker login.

Azure provisioning, a private container upload, application access, deployment, and live verification are not done. See the [handoff](.ai/cvs-review-portal/06_common_handoff.md).

## Packaging note

A review ZIP of the application should include `scripts/generate_demo_data.py` and `src/cvs_review_portal/web/`. Exclude `.env`, `.venv`, `cholec80-data/`, credentials, and caches.
