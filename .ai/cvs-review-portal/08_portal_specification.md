# 08 — CVS Review Portal Specification (Current Source of Truth)

This document is the **approved product and technical specification** for the CVS Review Portal.

Inherited documents under `.ai/cvs-review-portal/` that describe compliance document ingestion, OpenSearch, AWS deployment, or related roadmaps are **legacy template content**. They are retained for history only. Where they conflict with this file, **this file prevails**.

Engineering standards in `05_code_quality_standards.md` remain applicable (structure, typing, errors, tests, quality gates). Compliance/AWS examples in that file are illustrative of writing style, not portal requirements.

---

## 1. Product boundaries

The **CVS Engine** is a separate local application responsible for preprocessing, inference, and performance-metric computation.

The **CVS Review Portal** displays exported datasets and execution results and will later persist human reviews.

Final portal capabilities:

1. **Analytical** — raw image, read-only ground truth, optional predictions and model descriptions, review comments.
2. **Summary** — all images in the selected dataset/version with corresponding information.
3. **Executive Summary** — image count, ground-truth distribution, and available evaluation metrics.

Ground truth is read-only in this review portal (`0 — CVS absent` / `1 — CVS present`). Comments may be drafted and saved (comments-only). Creating or changing ground truth is deferred to a possible future sub-portal at a separate path.

Application deployment and data publication are independent. New datasets and runs must not require application code changes.

Only original raw images are displayed. Preprocessing configuration is metadata; processed images and Engine logic are outside this repository.

---

## 2. Three-step roadmap

| Step | Scope |
| ---- | ----- |
| **1** | Data contracts, local filesystem loading, read-only `/api` endpoints, demo fixtures, focused tests |
| **2** | UI for analytical / summary / executive views (dataset/run selection, frame cards, image viewing, comments-only in-memory drafts) |
| **3** | Comments-only Save endpoints, identity parsing, concurrency control, Azure Blob Storage adapter (no audit history in MVP) |

Exact next action after Step 3 implementation: owner local Save verification on port 18080, then external review of the report and complete repository ZIP before Azure setup/deployment.

---

## 3. Schema version

All stored JSON artifacts use:

```text
schema_version: "1"
```

(string literal `"1"`). Unknown or missing schema versions are invalid artifacts.

---

## 4. Storage layout

Configurable setting: `DATA_ROOT` (default: `demo-data` relative to the process working directory).

```text
<data_root>/
  raw-images/<dataset_id>/<dataset_version>/<relative-key>
  runs-output/catalog.json
  runs-output/datasets/<dataset_id>/<dataset_version>/dataset.json
  runs-output/runs/<run_id>/run.json
  runs-output/runs/<run_id>/predictions.json
  runs-output/runs/<run_id>/metrics.json                 # optional
  runs-output/runs/<run_id>/evaluation_snapshot.json     # optional; required when metrics exist
  reviews/<dataset_id>/<dataset_version>/<image_id>.json # optional seeded reviews
```

Discovery uses `catalog.json` as the **publication boundary**. A dataset may be listed and viewed without any runs.

Catalog rules:

* Duplicate `(dataset_id, dataset_version)` entries or duplicate `run_id`s are invalid artifacts.
* Direct dataset, run, summary, and image reads must not expose artifacts absent from the catalog (404 even if files exist).
* Published runs must reference a published dataset version.
* Unknown/unpublished client requests → `404`.
* Catalog references a missing/invalid manifest, or a published run references an unavailable dataset → controlled `500` artifact error (never an unhandled exception or successful empty stand-in).

Identifiers (`dataset_id`, `dataset_version`, `run_id`, `image_id`) must match `^[A-Za-z0-9][A-Za-z0-9._-]*$`. Relative storage keys must be relative, must not contain `..` or absolute roots, and resolved real paths (including symlinks) must stay under their configured roots.

Image bytes are served only through an application endpoint keyed by dataset identity and `image_id`. Clients never supply filesystem paths; the data root is never mounted as a static directory.

---

## 5. Data contracts (exact shapes)

### 5.1 Catalog — `runs-output/catalog.json`

```json
{
  "schema_version": "1",
  "datasets": [
    { "dataset_id": "demo-surgical", "dataset_version": "v1" },
    { "dataset_id": "demo-empty-runs", "dataset_version": "v1" }
  ],
  "runs": [
    { "run_id": "run-baseline" },
    { "run_id": "run-alt-model" },
    { "run_id": "run-empty-preds" },
    { "run_id": "run-partial-preds" }
  ]
}
```

### 5.2 Dataset version — `.../dataset.json`

Identity: `(dataset_id, dataset_version)`.

```json
{
  "schema_version": "1",
  "dataset_id": "demo-surgical",
  "dataset_version": "v1",
  "display_name": "Demo Surgical Dataset",
  "description": "Synthetic CVS surgical-demo dataset — not patient data.",
  "images": [
    {
      "image_id": "img-001",
      "raw_image_key": "img-001.png",
      "ground_truth": 0,
      "comments": "Baseline negative example."
    },
    {
      "image_id": "img-002",
      "raw_image_key": "img-002.png",
      "ground_truth": 1,
      "comments": null
    }
  ]
}
```

Rules:

* Binary labels (`ground_truth`, predicted labels, evaluation snapshot labels, review overrides, confusion-matrix labels) are **strict Python integers** `0` or `1`. Booleans, floats, strings, and other integers are rejected via a shared reusable validator.
* Confusion-matrix cell counts, `evaluated_image_count`, and review `revision` must be actual integers (not bool/float), preserving existing range constraints (`revision >= 1`, counts `>= 0`).
* Ground truth is **read-only** in this review portal. There is no editable/fixed distinction and no `ground_truth_editable` field in active contracts or API responses.
* At the storage-read boundary only, a narrowly scoped compatibility strip may ignore a legacy `ground_truth_editable` key on dataset images so previously written artifacts remain readable. That field is never exposed through domain/API models.
* `image_id` is unique within the dataset version; it joins predictions and reviews. It is not an array index or a globally unique id.
* Original dataset values are preserved; manifests are never mutated when building responses.
* Creating or changing ground truth belongs to a possible future sub-portal at a separate path and is out of scope here.

### 5.3 Run — `runs/<run_id>/run.json`

Each run identifies one execution and references exactly one dataset version. Distinct runs may share the same dataset. Identical settings still require distinct `run_id`s. One run = one model/configuration execution.

```json
{
  "schema_version": "1",
  "run_id": "run-baseline",
  "dataset_id": "demo-surgical",
  "dataset_version": "v1",
  "model": {
    "model_id": "demo-classifier-a",
    "model_name": "Demo Classifier A",
    "model_version": "1.0.0",
    "description": "Synthetic baseline model description."
  },
  "model_parameters": { "threshold": 0.5, "seed": 42 },
  "preprocessing": {},
  "execution_description": "Synthetic demo execution.",
  "executed_at": "2026-03-01T10:15:00+00:00",
  "predictions_artifact": "predictions.json",
  "metrics_artifact": "metrics.json",
  "evaluation_snapshot_artifact": "evaluation_snapshot.json"
}
```

`preprocessing` may be `{}`. `metrics_artifact` and `evaluation_snapshot_artifact` may be `null` when no evaluation was published. When metrics exist, both metrics and evaluation snapshot artifacts must be present and consistent.

### 5.4 Predictions — `predictions.json`

```json
{
  "schema_version": "1",
  "predictions": [
    {
      "image_id": "img-001",
      "predicted_label": 0,
      "positive_class_probability": 0.12,
      "description": "Model notes for img-001."
    }
  ]
}
```

Rules:

* Join by `image_id` within the run’s dataset version.
* `predicted_label` is strictly `0` or `1`.
* `positive_class_probability` is optional; when present it is the probability of class `1` in `[0, 1]`.
* Empty `predictions` array = **no predictions**.
* Missing entry for an image = **prediction unavailable** (never coerce to `0`).
* Legitimate predicted `0` must never be lost through truthiness checks.
* Duplicate `image_id`s or unknown `image_id`s are invalid artifacts.
* Partial coverage is valid.

### 5.5 Metrics — `metrics.json`

Portal does **not** recompute metrics. Import Engine outputs only.

```json
{
  "schema_version": "1",
  "accuracy": 1.0,
  "precision": 1.0,
  "recall": 1.0,
  "f1": 1.0,
  "confusion_matrix": {
    "labels": [0, 1],
    "matrix": [[1, 0], [0, 1]]
  },
  "evaluated_image_count": 2
}
```

Accuracy, precision, recall, and F1 accept finite numeric values in `[0, 1]`, or `null` when undefined. Booleans, nonnumeric strings, NaN, infinity, and out-of-range values are rejected. The portal never recomputes these scores.

Confusion-matrix orientation: **rows are ground truth**, **columns are predictions**, both following `labels` order. Labels and cell counts use the same strict integer rules as above. When a matrix is present, its cells must sum to `evaluated_image_count`.

A published metrics/snapshot pair with `evaluated_image_count == 0` is an invalid stored artifact (controlled `500`). It must never produce `available=true`. A valid run without published metrics remains supported (`available=false`).

Metrics must not appear available when there are no evaluable predictions. Predictions without a metrics artifact remain distinguishable from an evaluation with metrics.

### 5.6 Evaluation snapshot — `evaluation_snapshot.json`

Preserved independently of current reviews. Never silently recompute historical metrics from reviewed labels.

```json
{
  "schema_version": "1",
  "evaluated_images": [
    { "image_id": "img-001", "ground_truth": 0 },
    { "image_id": "img-002", "ground_truth": 1 }
  ]
}
```

Consistency checks: evaluated IDs belong to the dataset, have predictions, and the list length equals `evaluated_image_count` from metrics.

### 5.7 Shared review — `reviews/.../<image_id>.json`

Identity: `(dataset_id, dataset_version, image_id)` — **independent of `run_id`**.

#### Schema v1 (legacy; still readable)

```json
{
  "schema_version": "1",
  "dataset_id": "demo-surgical",
  "dataset_version": "v1",
  "image_id": "img-001",
  "ground_truth_override": 1,
  "comments": "Seeded shared review comment.",
  "revision": 1,
  "actor": "demo-reviewer",
  "updated_at": "2026-03-02T14:00:00+00:00"
}
```

#### Schema v2 (read-only compatibility)

Existing schema-v2 envelopes (current + history + operations) remain **readable**. The portal projects `current` comments and ground-truth overrides. New Saves write schema v1 current-state records only. Owner data is never bulk-migrated, regenerated, or deleted.

Rules:

* New Saves persist the latest comment plus minimal current-state metadata (`revision`, `actor`, `updated_at`, preserved `ground_truth_override`) using the schema-v1 `ReviewRecord` shape.
* An existing ground-truth override is preserved across comment Saves and is never edited by this portal.
* Owner data is never rewritten during startup, reads, tests, or generation.
* Maximum comment length: **8000** characters (backend + UI; never silently truncated).
* Practical per-image document size bound: **512_000** UTF-8 JSON bytes; exceeding the bound fails explicitly.
* Revision `0` means no persisted review exists (`expected_revision` for first Save). Existing seeded reviews keep their actual revision.
* Audit history UI, history API, and request-receipt reconciliation are **out of MVP scope**.

Effective image composition (read path) for v1 and readable v2:

* Original ground truth always remains visible (read-only display).
* Effective ground truth uses a valid override when present (including legitimate `0`).
* Comments use the review value when present (including intentional `""`).
* Without a review, use dataset baseline comments/ground truth.
* The same shared review appears consistently across runs.
* API image views include additive `persisted_revision` (`0` when no review).

### 5.8 Comments-only Save contract

`PUT .../review` body (extra fields forbidden):

* `comments` (required string; empty allowed)
* `expected_revision` (required strict int ≥ 0)

Backend supplies actor (from identity) and UTC timestamp. Catalog publication, dataset identity, and image membership are verified before reads/writes.

Response:

* `current` — persisted review state after a successful write
* `persisted_revision` — revision of that current state

Concurrency: storage uses atomic compare-and-write (local cross-process file lock + atomic replace; Azure ETag conditional create/update). Never unconditional overwrite. Stale `expected_revision` → `409` conflict; the UI preserves the user’s draft and offers reload/re-edit of the current server comment. No silent overwrite of a newer comment.

If the Save HTTP response is lost or otherwise unconfirmed, the UI shows “Save could not be confirmed”, preserves the draft, and offers a **read-only refresh** of the current server comment. It does not automatically resend the write and does not claim the Save failed.

Controlled responses: `401` auth, `403` unauthorized, `404` unpublished/unknown, `409` conflict, `422` invalid mutation, controlled storage errors without leaking paths/credentials/comment contents.

Publication vs artifact errors:

* Unknown/unpublished target → `404`
* Published target with missing required/declared artifact (predictions, declared metrics, declared evaluation snapshot) → controlled artifact error (`500`)
* Storage/credential unavailability → controlled availability error
* Catalog reference to a missing/invalid dataset → controlled artifact error (not an ordinary client `404`)

Ground-truth mutation remains out of scope for this portal. There is no review History endpoint or History UI in MVP.

---

## 6. Portal API (`/api`)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/api/datasets` | List published datasets and versions from the catalog |
| `GET` | `/api/datasets/{dataset_id}/versions/{dataset_version}` | Dataset version with effective image review information |
| `GET` | `/api/runs` | List runs; optional `dataset_id` / `dataset_version` filters |
| `GET` | `/api/runs/{run_id}` | Selected run with joined image/prediction information |
| `GET` | `/api/datasets/{dataset_id}/versions/{dataset_version}/summary` | Full-dataset summary; optional `run_id` for prediction coverage and historical metrics |
| `GET` | `/api/datasets/{dataset_id}/versions/{dataset_version}/images/{image_id}/content` | Original raw image bytes |
| `GET` | `/api/datasets/.../images/{image_id}/review` | Current persisted review state |
| `PUT` | `/api/datasets/.../images/{image_id}/review` | Comments-only Save |

Response models are explicit Pydantic models. Route handlers do not perform storage joins.

Summary covers the full selected dataset/version (not a UI subset): total images, effective ground-truth counts, prediction coverage, and separately identified historical evaluation metrics when available. Historical metrics are never recomputed on comment Save.

Errors:

* Missing/invalid authentication → `401`
* Authenticated but unauthorized → `403`
* Unknown/unpublished resources → `404`
* Stale revision / request-ID reuse conflict → `409`
* Malformed / unsupported mutation payloads → `422`
* Invalid stored artifacts → controlled `500` (log safe context; never leak local paths, credentials, or comment contents)
* Missing/unreadable data root on data endpoints → controlled error; `/health` and import-time `create_app` remain healthy

Do not silently skip corrupt artifacts or return successful empty results in their place.

System endpoints remain: `/health`, `/ready`, `/version` (intentionally open for probes). `/ready` does **not** establish Azure or dataset readiness. Portal/UI/data/image/review routes are protected by the identity boundary.

### 6.1 Storage backends

* `STORAGE_BACKEND=local` (default): filesystem under `DATA_ROOT`.
* `STORAGE_BACKEND=azure_blob`: one private container with prefixes `raw-images/`, `runs-output/`, `reviews/`. Requires `AZURE_STORAGE_ACCOUNT_URL` and `AZURE_BLOB_CONTAINER`. Uses Azure Identity credentials (managed identity intended for deployment). Missing config/credentials fail closed — **no fallback to local data**. No network calls at import time; SDK clients closed on app shutdown.

### 6.2 Identity modes

* `IDENTITY_MODE=disabled` (default): fail closed for protected routes.
* `IDENTITY_MODE=development`: loopback-only; server-configured `DEVELOPMENT_ACTOR` (never browser-supplied). Not production authentication. Not enabled automatically when production identity is absent. Allowed only for `APP_ENV=local` or `dev`.
* `IDENTITY_MODE=azure_app_service`: trust App Service authentication headers only behind a hosting layer that strips client-supplied identity headers and prevents direct backend bypass. Canonical actor format is `aad:{tenant_id}:{object_id}` from validated tenant/object claims (short and mapped claim names). Convenience headers (`X-MS-CLIENT-PRINCIPAL-ID` / name) must not change the actor format; overlapping identity values must be consistent or the request is rejected. Enforce `ALLOWED_ACTORS` using that canonical form. Historical stored actor strings are never rewritten. Parsing a base64 principal header alone is not authentication.

Cookie-authenticated writes require `Content-Type: application/json` and same-origin/CSRF checks. No permissive CORS.

---

## 7. Portal UI (Step 2)

### 7.1 Serving

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/` | Portal HTML shell |
| `GET` | `/ui-assets/*` | Packaged local CSS/JS (and related UI files) |

Implementation:

* Plain HTML, local CSS, plain JavaScript (native browser APIs).
* Packaged under `src/cvs_review_portal/web/` and resolved relative to the Python package path (not the shell cwd).
* Only the intended static-assets directory is mounted. **`DATA_ROOT` is never mounted**.
* No React, Node build pipeline, CDN, externally hosted fonts, charting library, or new Python dependency.

Local launch URL after demo data generation (Step 3 default port):

```text
http://127.0.0.1:18080/
```

Existing `/api`, `/health`, `/ready`, `/version`, and `/docs` remain available.

### 7.2 Interaction model

* Load `/api/datasets`, select dataset/version, load dataset detail + runs + summary.
* Offer **“Dataset only — no run selected”** even when runs exist.
* One selected run = one model/configuration execution. No hardcoded multi-model columns in this step.
* Changing runs within the same dataset/version preserves open frame cards and comment drafts (reviews are independent of `run_id`).
* Changing dataset/version never reuses prior images, predictions, metrics, or comments; unsaved comment drafts require discard-or-cancel.
* Rapid selection changes use a selection-generation token / abort so stale responses cannot overwrite current state.
* Ground truth is displayed as plain read-only labels (`0 — CVS absent` / `1 — CVS present`). Never treat `0` or probability `0` as missing via truthiness.
* Original vs effective ground truth is shown when they differ. There is no GT editing control and no editable/fixed indicator.
* Missing predictions display **“No prediction”**.
* Temporary drafts are **comments only**, in browser memory keyed by `(dataset_id, dataset_version, image_id)`. **Save comment** / **Discard changes** per card (no History). No `localStorage`. Max comment length 8000 (no silent truncation).
* Typing updates draft banners/buttons/status **in place**. The textarea DOM node, focus, selection, caret, and composition input are preserved; the image is not reloaded and the full card is not rebuilt per keystroke.
* Save captures comment + `expected_revision`; prevents duplicate in-flight clicks; keeps comments read-only while pending.
* Stale revision → conflict: preserve draft, show current server comment, explicit resolve/re-edit before a new Save. Never silently overwrite.
* Lost/unconfirmed Save response → “Save could not be confirmed”; preserve draft; offer read-only server refresh; do not auto-resend or claim failure.
* Run selection may bump selection generation for run-scoped loads, but must not orphan an in-flight review Save when dataset/version/image still match. Summary refresh after Save uses the **current** run context with stale-response protection.
* Save-state rules live in packaged `web/review_save_logic.mjs` (wired from `app.js` via `currentIdentity: currentDatasetIdentity`).
* Summary and Executive Summary show persisted API values only; when comment drafts exist, show a notice that unsaved drafts are excluded. Warn on leave/reload for dirty or unresolved Saves.
* Historical metrics are never recomputed; they retain the recorded evaluation-snapshot ground-truth semantics. Show the snapshot note and a drift notice when current persisted labels differ from the evaluation snapshot.
* API text is rendered safely (`textContent` / DOM construction). Image URLs are built from encoded identity segments.

### 7.3 Remaining non-goals after Step 3

Azure resource provisioning, cloud Easy Auth end-to-end verification, and deployment. Ground-truth creation/editing (possible separate sub-portal) remains deferred.

---

## 8. Module placement

```text
src/cvs_review_portal/
  domain/          # contracts and invariants (including review schema v2)
  application/     # read + comments-only Save use cases
  infrastructure/  # local filesystem + Azure Blob adapters; identity adapters
  api/             # thin HTTP routes, auth/CSRF guards, UI registration
  web/             # packaged HTML/CSS/JS for GET / and /ui-assets
```

One small storage Protocol isolates local and Blob adapters. No generic repository framework.

Blocking I/O uses synchronous endpoints (justified for local/Blob SDK calls via sync clients). No portal data network/filesystem reads at module import time.

---

## 9. Demonstration fixtures

Demo data is produced by the reproducible generator (not assumed checked in):

```powershell
poetry run python scripts/generate_demo_data.py
```

Rules:

* Target defaults to `demo-data/` under the repository root.
* The generator **refuses** to write into a nonempty target and never deletes existing files.
* The catalog is written **last**, after all referenced artifacts exist.
* Newly generated fixtures use CVS/surgical-demo naming (`demo-surgical`, “Demo Surgical Dataset”); all content is explicitly synthetic.

Generated scenarios include: two datasets; PNG placeholders; multiple runs on one dataset version; a dataset with no runs; empty and partial predictions; labels `0`/`1`; one seeded shared review (including a ground-truth override); one consistent metrics + evaluation snapshot. New generations omit the retired `ground_truth_editable` field.

Then start with development identity configured and:

```powershell
poetry run uvicorn cvs_review_portal.main:app --host 127.0.0.1 --port 18080 --reload
```

Open `http://127.0.0.1:18080/` (UI) or `/docs` (API).

---

## 10. Non-goals (after Step 3)

Ground-truth editing UI or schema; annotation sub-portal; Engine logic; AWS/OpenSearch/DB wiring; Azure resource provisioning and cloud deployment verification; Docker redesign; renaming the package or replacing `create_app`.
