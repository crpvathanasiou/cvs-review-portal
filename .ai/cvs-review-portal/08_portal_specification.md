# 08 — CVS Review Portal Specification (Current Source of Truth)

This document is the product and technical specification: what the portal does and the contracts it enforces.

How to run it: [../../README.md](../../README.md).
Where it is implemented: [07_code_map.md](07_code_map.md).
Owner acceptance, dataset counts, and the next action: [06_common_handoff.md](06_common_handoff.md).

Inherited documents `00_*`, `01_*`, `02_*`, and `04_*` describe a compliance/OpenSearch/AWS template. They are history. Where they conflict with this file, this file prevails.

Engineering standards in [05_code_quality_standards.md](05_code_quality_standards.md) remain applicable. Compliance/AWS examples in that file illustrate writing style. They are not portal requirements.

---

## 1. Purpose and current MVP scope

The **CVS Engine** is a separate application. It owns preprocessing, inference, and metric computation.

The **CVS Review Portal** displays exported datasets and any published Engine results, and it persists **comments-only** human reviews. Ground truth is read-only here (`0 — CVS absent` / `1 — CVS present`). Creating or changing ground truth belongs to a possible future sub-portal at a separate path.

Three views:

1. **Analytical** — raw image, read-only ground truth, optional predictions and model description, review comments.
2. **Summary** — dataset-level information for the selected dataset/version. Provenance-backed datasets load effective counts only when the user asks, and they omit the per-image table.
3. **Executive Summary** — image count, effective ground-truth distribution, and available evaluation metrics from the same explicit summary load when the dataset is provenance-backed.

Deployment and data publication are independent. Publishing a dataset or run does not require an application code change.

Only original raw images are displayed. Preprocessing configuration is metadata. Processed images and Engine logic are outside this repository.

### Implemented in the current MVP

- Schema-v1 catalog, dataset, run, prediction, metrics, and evaluation-snapshot reads
- Local filesystem store and an Azure Blob adapter selected by configuration
- Development (loopback) and Azure App Service identity adapters
- Comments-only Save with revision concurrency
- Browser caching of successful raw image-content responses
- Offline Cholec80 import into a new empty data root
- Interval cards, video/image search, Previous/Next, and paginated thumbnails for datasets that carry provenance
- Per-image picker for datasets that do not carry provenance
- Synthetic demo generator

### Deferred

- Azure account, subscription, storage resources, upload, access configuration, deployment, and live verification
- Further performance work. Search and frame-navigation latency are an open limitation. The owner accepted the MVP with that limitation and chose to proceed toward Azure. See the [handoff](06_common_handoff.md).
- Ground-truth editing
- Audit history UI and history API
- A thumbnail pipeline. Thumbnails request the full image-content bytes
- Immediate removal of cached images on logout
- Publishing inference runs for the imported Cholec80 dataset. That import writes a catalog with an empty `runs` array

---

## 2. Architecture

Dependencies point inward: HTTP and the UI call application services; services depend on domain types and on a small storage port; infrastructure adapters implement that port.

| Responsibility | Role | Canonical paths |
| --- | --- | --- |
| Domain | Contracts and invariants: identifiers, binary labels, provenance, review projection, error types | `src/cvs_review_portal/domain/` |
| Read services | Catalog publication, dataset/run/summary composition, interval index, metadata browse, selected-image review read | `application/portal_service.py`, `application/interval_index.py`, `application/views.py` |
| Review writes | Comments-only Save, expected revision, actor and timestamp supplied by the server | `application/review_service.py` |
| Storage adapters | Local filesystem or one private Azure container. Same logical prefixes. No silent fallback | `infrastructure/local_store.py`, `infrastructure/azure_blob_store.py` |
| API | Thin routes, identity middleware, JSON/same-origin mutation guard, image cache headers | `api/portal.py`, `api/auth.py`, `api/image_cache.py`, `main.py` |
| Frontend | Packaged HTML/CSS/JS. Production Save and interval modules plus classic `app.js` | `web/` — registration in [07_code_map.md](07_code_map.md) |

`create_app(settings)` in `src/cvs_review_portal/main.py` builds the store and identity provider in the FastAPI lifespan. Portal data is not read at import time. `DATA_ROOT` is never mounted as static files. Image bytes are returned only by the image-content route.

Blocking storage calls use synchronous endpoints. That is the supported style for the local filesystem and the sync Blob SDK.

### Roadmap status

| Step | Scope | Status |
| --- | --- | --- |
| **1** | Data contracts, local loading, read-only `/api`, demo fixtures, tests | Implemented |
| **2** | Analytical / summary / executive UI, in-memory comment drafts | Implemented |
| **3** | Comments-only Save, identity, concurrency, Azure Blob adapter. No audit history | Implemented |
| **2A** | Offline Cholec80 import | Implemented and imported |
| **2B** | Interval browse, search, Previous/Next, metadata-first reads | Implemented and owner-accepted for this MVP |

The next action is guided Azure setup. It is specified in the [handoff](06_common_handoff.md), and it has not been started.

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

Optional per-image provenance (default `null` / omitted for existing datasets):

```json
"provenance": {
  "video_id": "v-74ddaa361637964e4a32de869ff6a2651cc3da9e2478e770781e13857469d3c3",
  "video_filename": "video02.mp4",
  "segment_id": "v-74ddaa361637964e4a32de869ff6a2651cc3da9e2478e770781e13857469d3c3-s1226-e1256",
  "start_seconds": 1226,
  "end_seconds": 1256,
  "frame_index": 30650,
  "timestamp": 1226.0,
  "display_id": "cholec80-v1-video02-s1226-e1256-f30650"
}
```

Rules:

* Binary labels (`ground_truth`, predicted labels, evaluation snapshot labels, review overrides, confusion-matrix labels) are **strict Python integers** `0` or `1`. Booleans, floats, strings, and other integers are rejected via a shared reusable validator.
* Confusion-matrix cell counts, `evaluated_image_count`, and review `revision` must be actual integers (not bool/float), preserving existing range constraints (`revision >= 1`, counts `>= 0`).
* Ground truth is **read-only** in this review portal. There is no editable/fixed distinction and no `ground_truth_editable` field in active contracts or API responses.
* At the storage-read boundary only, a narrowly scoped compatibility strip may ignore a legacy `ground_truth_editable` key on dataset images so previously written artifacts remain readable. That field is never exposed through domain/API models.
* `image_id` is unique within the dataset version; it joins predictions and reviews. It is not an array index or a globally unique id. Technical export `image_id` values are preserved unchanged by importers.
* When `provenance` is present, `provenance.display_id` must also be unique within the dataset version. Existing datasets may omit `provenance` entirely (`null`).
* Original dataset values are preserved; manifests are never mutated when building responses.
* Creating or changing ground truth belongs to a possible future sub-portal at a separate path and is out of scope here.

### 5.2.1 Cholec80 export preparation

Offline importer: `scripts/import_cholec80.py`. Logic: `src/cvs_review_portal/importers/cholec80.py`. Commands and the completed paths are in the [README](../../README.md#import) and the [handoff](06_common_handoff.md).

Inputs:

| Input | Role |
| --- | --- |
| Extraction export root | `run.json`, `manifest.jsonl`, and the source JPEGs under `images/` |
| Ground-truth workbook | Excel `.xlsx` with the Cholec80 CVS columns, including `critical_view` |
| Destination | A new empty portal data root. Nonempty destinations are refused for dry-run and for a copying import |
| `dataset_id`, `dataset_version` | Portal identity written into the dataset and catalog |

Ground-truth matching uses the required video number (from the video filename) plus start and end seconds. Start is `initial_minute * 60 + initial_second`. End is `final_minute * 60 + final_second`. The join does not use `excel_row`.

Workbook rows that do not match a required export key are unused. They are counted and skipped, including rows with invalid intervals or keys for videos the extraction did not import. The owner workbook is not modified. Each imported segment requires exactly one matching workbook row. Manifest membership is checked against `run.json` `videos[]` and `segments[]`, not against aggregate counts alone.

Binary ground truth comes from `critical_view` only. A missing or invalid label fails the import. The importer does not default a label to `0` and does not derive it from `Total` or component scores.

Every manifest `image_id` is kept. The manifest relative `path` becomes `raw_image_key`. A copying import uses `shutil.copy2` into:

```text
<destination>/raw-images/<dataset_id>/<dataset_version>/<raw_image_key>
```

For this export, `raw_image_key` is the manifest path under `images/<video_id>/<segment_id>/...`.

Then it writes:

```text
<destination>/runs-output/datasets/<dataset_id>/<dataset_version>/dataset.json
<destination>/runs-output/catalog.json
```

`dataset.json` is written before `catalog.json`. The catalog is the publication boundary and is written last. Its `runs` array is empty. The extraction `run.json` is provenance for the export only. It is not registered as an inference `RunManifest`. The importer does not invent predictions, metrics, or reviews.

Overlapping intervals that repeat a source frame stay separate image records, each with its own `image_id`, even when their ground-truth labels disagree. Those disagreements are reported as repeated-frame label conflicts. They do not collapse the records.

`--dry-run` validates and prints counts. It still refuses a nonempty destination, and it writes nothing when the destination is absent or empty.

The completed import’s counts, unused-row count, conflict count, and the skipped extraction job are recorded in the [handoff](06_common_handoff.md). Interval browsing for this provenance is §7.4.

### 5.2.2 Technical IDs and display IDs

| ID | Meaning | Relationship |
| --- | --- | --- |
| `video_id` | Technical id of the source video, taken from the export | Many intervals belong to one video |
| `segment_id` | Technical id of one interval (one video, one start, one end) | One card per `segment_id`. Intervals are not merged by video or by ground truth |
| `image_id` | Technical id of one frame record, preserved from the export | Unique in the dataset version. Reviews and predictions join on it. It is not an array index and not a global id |
| `display_id` | Readable id built at import | Unique in the dataset version when provenance is present |

`display_id` is:

```text
{dataset_id}-{dataset_version}-{video stem}-s{start_seconds}-e{end_seconds}-f{frame_index}
```

Example shape: `cholec80-v1-video02-s1226-e1256-f30650`. The importer default dataset display name, used in card titles, is `{dataset_id} {dataset_version}` (`cholec80 v1`) unless `--display-name` is passed. A title looks like `cholec80 v1 · Video 02 · 20:26–20:56`.

Search treats `video_id`, `image_id`, and `display_id` as exact matches. Video filename and stem match case-insensitively (`video02` and `video02.mp4`). A video match lists that video’s intervals in start/end/`segment_id` order. An image match opens the owning interval at that frame.

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
| `GET` | `/api/datasets/{dataset_id}/versions/{dataset_version}/browse` | Lightweight header + browse mode (`interval` \| `image`); no per-image review reads |
| `GET` | `/api/datasets/.../intervals` | Paginated interval metadata (counts/titles/first-image id); no reviews |
| `GET` | `/api/datasets/.../intervals/search?q=` | Video/image search → interval hits (optional target frame); no reviews |
| `GET` | `/api/datasets/.../intervals/{segment_id}/frames` | Ordered frame metadata for one interval; no reviews |
| `GET` | `/api/datasets/.../images/{image_id}/view` | Effective review state for one frame; optional `run_id` prediction |
| `GET` | `/api/runs/{run_id}/overview` | Run metadata + metrics without composing every image review |
| `GET` | `/api/datasets/{dataset_id}/versions/{dataset_version}/images/{image_id}/content` | Original raw image bytes (browser-cacheable; see §6.3) |
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

* `STORAGE_BACKEND=local` (default): filesystem under `DATA_ROOT`. A process environment variable overrides `.env`. The accepted Cholec80 session sets `DATA_ROOT` that way. Commands are in the [README](../../README.md).
* `STORAGE_BACKEND=azure_blob`: one private container with prefixes `raw-images/`, `runs-output/`, `reviews/`. Requires `AZURE_STORAGE_ACCOUNT_URL` and `AZURE_BLOB_CONTAINER`. Uses Azure Identity credentials (managed identity intended for deployment). Missing config/credentials fail closed — **no fallback to local data**. No network calls at import time; SDK clients closed on app shutdown.

### 6.2 Identity modes

* `IDENTITY_MODE=disabled` (default): fail closed for protected routes.
* `IDENTITY_MODE=development`: loopback-only; server-configured `DEVELOPMENT_ACTOR` (never browser-supplied). Accepted client hosts are `127.0.0.1`, `::1`, `localhost`, and `testclient`. A browser that reaches the process through a published container port is not one of those hosts, so this mode does not authenticate that request. The accepted local portal binds `127.0.0.1:18080`. This mode is not production authentication. It is not enabled automatically when production identity is absent. It is allowed only for `APP_ENV=local` or `dev`.
* `IDENTITY_MODE=azure_app_service`: trust App Service authentication headers only behind a hosting layer that strips client-supplied identity headers and prevents direct backend bypass. Canonical actor format is `aad:{tenant_id}:{object_id}` from validated tenant/object claims (short and mapped claim names). Convenience headers (`X-MS-CLIENT-PRINCIPAL-ID` / name) must not change the actor format; overlapping identity values must be consistent or the request is rejected. Enforce `ALLOWED_ACTORS` using that canonical form. Historical stored actor strings are never rewritten. Parsing a base64 principal header alone is not authentication.

Cookie-authenticated writes require `Content-Type: application/json` and same-origin/CSRF checks. No permissive CORS.

### 6.3 Image content browser caching

Successful `GET .../images/{image_id}/content` responses:

* `Cache-Control: private, max-age=3600`
* `Vary: Cookie, Authorization` (merged with any existing Vary tokens)
* Strong quoted `ETag` = SHA-256 of the **response body bytes** actually returned
* `If-None-Match` support (quoted/weak tags, lists, `*`) → matching validators yield `304` with an empty body and the same cache-policy/ETag/Vary headers; non-matching validators yield `200` with the image and current ETag
* PNG/JPEG content types preserved from storage adapters

Authentication, authorization, catalog publication, dataset membership, and path validation run **before** any `304`. Image endpoint errors (including auth failures) use `Cache-Control: no-store` and must never become cacheable `304`s.

This policy applies **only** to the raw image-content route. Reviews, Save responses, summaries, and other mutable JSON are not covered.

Limitations:

* Calculating the ETag still reads image bytes from storage when the request reaches the server. Fresh browser-cache hits avoid the request entirely; `304` avoids retransmitting the body. Not every Blob/filesystem read is eliminated.
* Browser cache eviction is controlled by the browser; immediate removal on logout is not implemented. Fresh cached images may be reused for up to one hour without another server authorization check.
* Changed image bytes should be published under a **new dataset version** so URLs/ETags diverge cleanly.
* UI thumbnails remain enabled and currently load via the same full image-content endpoint (no separate thumbnail generation). Thumbnails, cards, and the zoom viewer share `imageContentUrl()` and do not add a cache-busting query.
* Elapsed time for Previous/Next does not identify a cache miss or a cache hit. The owner acceptance recorded that latency and left its cause unprofiled. See the [handoff](06_common_handoff.md).

---

## 7. Portal UI

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

Local launch URL (development server in `scripts/dev.ps1`):

```text
http://127.0.0.1:18080/
```

The Docker image uses port 8000. Commands, session `DATA_ROOT`, and that distinction are in the [README](../../README.md).

Existing `/api`, `/health`, `/ready`, `/version`, and `/docs` remain available.

### 7.2 Interaction model

* Load `/api/datasets`, then select a dataset/version. Selection loads `/browse` and the run list. Datasets without provenance then load dataset detail and the summary. Provenance-backed datasets stay on the metadata path in §7.4.
* Offer **“Dataset only — no run selected”** even when runs exist.
* One selected run = one model/configuration execution. No hardcoded multi-model columns in this step.
* Changing runs within the same dataset/version preserves open frame cards and comment drafts (reviews are independent of `run_id`).
* Changing dataset/version never reuses prior images, predictions, metrics, or comments; unsaved comment drafts require discard-or-cancel.
* Rapid selection changes use a selection-generation token / abort so stale responses cannot overwrite current state.
* Ground truth is displayed as plain read-only labels (`0 — CVS absent` / `1 — CVS present`). Never treat `0` or probability `0` as missing via truthiness.
* Original vs effective ground truth is shown when they differ. There is no GT editing control and no editable/fixed indicator.
* Missing predictions display **“No prediction”**.
* Temporary drafts are **comments only**, in browser memory keyed by `(dataset_id, dataset_version, image_id)`. **Save comment** / **Discard changes** per card (no History). No `localStorage` or `sessionStorage`. Max comment length 8000 (no silent truncation).
* A draft lives until a successful Save clears it, the user discards it, or the tab is refreshed or closed. Refresh drops unsaved drafts. A successful Save remains in `reviews/<dataset_id>/<dataset_version>/<image_id>.json` under the active data root.
* Switching dataset/version asks before discarding unsaved comments or unresolved Saves. `beforeunload` warns while any draft or unresolved Save exists.
* Conflict (`409`): the draft stays, the current server comment is shown, and the user reloads or re-edits before another Save. The client does not overwrite the newer comment.
* Unconfirmed Save (response lost or otherwise unconfirmed): the UI shows “Save could not be confirmed”, keeps the draft, and offers a read-only refresh of the server comment. It does not send the write again and it does not claim the Save failed.
* Typing updates draft banners/buttons/status **in place**. The textarea DOM node, focus, selection, caret, and composition input are preserved; the image is not reloaded and the full card is not rebuilt per keystroke.
* Save captures comment + `expected_revision`; prevents duplicate in-flight clicks; keeps comments read-only while pending.
* Run selection may bump selection generation for run-scoped loads, but must not orphan an in-flight review Save when dataset/version/image still match. Summary refresh after Save uses the **current** run context with stale-response protection.
* Save-state rules live in packaged `web/review_save_logic.mjs` (wired from `app.js` via `currentIdentity: currentDatasetIdentity`).
* Summary and Executive Summary show persisted API values only; when comment drafts exist, show a notice that unsaved drafts are excluded. Warn on leave/reload for dirty or unresolved Saves.
* Historical metrics are never recomputed; they retain the recorded evaluation-snapshot ground-truth semantics. Show the snapshot note and a drift notice when current persisted labels differ from the evaluation snapshot.
* API text is rendered safely (`textContent` / DOM construction). Image URLs are built from encoded identity segments via a stable `imageContentUrl()` (no timestamps, run IDs, or cache-busting query parameters) shared by thumbnails, cards, and the zoom viewer.

### 7.3 Still deferred

Azure resource provisioning, cloud Easy Auth verification, and deployment. Ground-truth creation/editing remains deferred. Performance work on search and frame changes is deferred by owner decision; the limitation is open. The checkpoint is the [handoff](06_common_handoff.md).

### 7.4 Interval browse (Step 2B)

For datasets whose images carry `provenance`:

* Display unit is one **interval** (`segment_id`) per card. Intervals are never merged by video or ground truth. Overlapping intervals remain separate records with distinct image IDs.
* Interval order within a video: `start_seconds`, `end_seconds`, then `segment_id`. Frames within an interval: numeric `frame_index`, then `image_id`.
* Titles are derived from metadata (`{display_name} · {Video NN} · {start}–{end}`). With the importer default display name, Video 02 at 1226–1256 seconds is `cholec80 v1 · Video 02 · 20:26–20:56`. See §5.2.2.
* Each open card shows title, image count, one current frame, position (`n / N`), `display_id` + technical `image_id`, read-only effective GT, comments/Save, and prediction when a run is selected.
* Ground truth and comments remain **per-image**. No interval-level review records.
* Picker searches (case-insensitive video filename/stem; exact `video_id`, `image_id`, or `display_id`). A video match lists all of that video’s intervals chronologically; an image match opens the owning interval at that frame. Duplicate-add focuses; remove only hides the card.
* Picker pages are bounded (default 24) with one representative thumbnail per interval result (lazy), using the existing image content URL/cache.
* Previous/Next navigate within the interval only (no wraparound). Only the selected frame’s content and effective review are fetched; no next-frame prefetch.
* Opening a dataset loads `/browse` and a page of interval metadata. That bootstrap does not read every image review and does not scan the summary. The selected frame then loads `GET .../images/{image_id}/view` for effective ground truth, comments, revision, and the optional run prediction. Frame bytes load from the image-content route.
* Effective summary and executive figures in interval mode load only when the user chooses “Load effective summary” or “Load executive summary” (`GET .../summary`). After a relevant Save, a summary already on screen is marked stale. The UI does not substitute original ground-truth counts for effective counts.
* Datasets without provenance keep the per-image picker and load dataset detail plus summary during selection.
* Interval async loads capture dataset/version, card instance (`cardId`), load generation, selection generation, and run context. A delayed response after a dataset switch, remove/reopen, or run switch is ignored. Applying a frame never replaces a newer persisted review revision with an older GET. Card updates target the affected nodes so typing in another card’s comment field continues while more intervals load. Those guards live in `web/interval_browse_logic.mjs`.

---

## 8. Module placement

The directory roles and the file-level map, including production JavaScript registration, are in [07_code_map.md](07_code_map.md).

```text
src/cvs_review_portal/
  domain/          # contracts and invariants (including review schema v2 reads)
  application/     # read services, interval index, comments-only Save
  infrastructure/  # local filesystem + Azure Blob adapters; identity adapters
  api/             # thin HTTP routes, auth/CSRF guards, UI registration
  web/             # index.html, styles.css, app.js, review_save_logic.mjs,
                   # register_save_logic.mjs, interval_browse_logic.mjs,
                   # register_interval_browse_logic.mjs
  importers/       # offline Cholec80 preparation
```

One small storage Protocol isolates the local and Blob adapters. There is no generic repository framework.

---

## 9. Demonstration fixtures

Copy-paste commands, including the session `DATA_ROOT` override for the imported dataset, are in the [README](../../README.md).

Rules for `scripts/generate_demo_data.py`:

* Target defaults to `demo-data/` under the repository root.
* The generator refuses to write into a nonempty target and never deletes existing files.
* The catalog is written last, after all referenced artifacts exist.
* Generated fixtures use CVS/surgical-demo naming (`demo-surgical`, “Demo Surgical Dataset”). The content is synthetic.

Generated scenarios include: two datasets; PNG placeholders; multiple runs on one dataset version; a dataset with no runs; empty and partial predictions; labels `0`/`1`; one seeded shared review (including a ground-truth override); one consistent metrics + evaluation snapshot. New generations omit the retired `ground_truth_editable` field.

The imported Cholec80 dataset is a separate data root. It is not produced by this generator, and it publishes no inference runs.

---

## 10. Non-goals

Ground-truth editing UI or schema; annotation sub-portal; Engine logic; AWS/OpenSearch/database wiring; treating the current navigation latency as a resolved cache defect; Azure resource provisioning and cloud deployment verification in this checkpoint; Docker redesign; renaming the package or replacing `create_app`.
