# 06 — Common Project Handoff

Shared operational handoff: current checkpoint, evidence classes, and the next action.

Product behavior: [08_portal_specification.md](08_portal_specification.md).
Implementation paths: [07_code_map.md](07_code_map.md).
Commands: [../../README.md](../../README.md).

Legacy template files `00_*`, `01_*`, `02_*`, and `04_*` are not this product. There is no separate architecture-decision record. The owner decision below is the decision record.

---

## 1. Current snapshot

```text
Project: CVS Review Portal
Stage: Azure video-catalog MVP owner-accepted
Local UI: http://127.0.0.1:18080/
Imported data root: C:\Users\User\cvs-review-portal\cholec80-data
DATASET_LAYOUT: video_catalog
Azure image: acrcvsdevvas01-bqe6hec0efcdavf3.azurecr.io/cvs-review-portal:video-catalog-20261015-202611
Azure revision: ca-cvs-portal-dev--0000006
```

The owner accepted this Azure deployment as the video-catalog MVP. That acceptance covers the checks in [§7](#azure-checkpoint). It is not exhaustive testing and it is not an external production certification. The earlier local acceptance remains the local checkpoint; it is not restated as a full walkthrough of every prior step.

---

## 2. Prior Step 2B acceptance

Step 2B (interval browse on the monolithic dataset) was owner-accepted earlier. The owner then chose to proceed toward Azure without further performance work. Search and frame-navigation latency remain an open limitation.

Owner observations recorded for that earlier acceptance (not re-stated as verification of the video-catalog MVP):

- Searching `video02` took approximately 45 seconds.
- Searching again after a browser refresh took approximately 2 minutes.
- Add all matching intervals worked.
- Previous/Next navigation worked, taking approximately 2.5 seconds per transition, including revisits.
- Comment Save persisted after page refresh.
- Typing in an existing card was not interrupted while additional intervals loaded.

Browser image caching was verified in an earlier step. Navigation latency cause was not isolated through profiling. Caching and Save concurrency rules stay in [specification §6.3](08_portal_specification.md#63-image-content-browser-caching) and [§7.2](08_portal_specification.md#72-interaction-model).

---

## 3. Accepted local architecture

Canonical contract: [specification §5.1.1](08_portal_specification.md#511-video-catalog--videoscsv--videosvideo_idjson).
Startup and converter commands: [README](../../README.md#video-catalog-layout-csv--per-video-json).

`DATASET_LAYOUT=video_catalog`:

- `videos.csv` is the sole active-video list, one row per video.
- Columns: `video_id,video_name,metadata_path`.
- One JSON metadata file per video.
- Removing or restoring a CSV row changes visibility after a browser refresh, without restarting the process.
- Image files and saved comments remain intact.
- `dataset.json` is retained for compatibility and conversion. It is not the runtime source in this mode.

---

## 4. Data checkpoint

<a id="data-checkpoint"></a>

Local root: `C:\Users\User\cvs-review-portal\cholec80-data`

Recorded conversion (already on disk; not regenerated for this documentation update):

```text
video JSON files:     75
active CSV videos:    10
active intervals:     70
active images:        10,018
full source:          494 intervals / 72,273 images
```

Active videos (name order):

```text
video02, video04, video05, video07, video08,
video09, video10, video11, video12, video13
```

Imported-dataset baseline (unchanged source counts):

```text
dataset_id: cholec80
dataset_version: v1
videos: 75
intervals: 494
images: 72,273
GT0: 476 intervals / 71,775 images
GT1: 18 intervals / 498 images
video70.mp4: skipped by extraction (interval_out_of_bounds)
unused XLSX rows: 78
repeated source frames with conflicting interval labels: 58
inference runs published with this import: none
catalog runs: []
dataset display_name: cholec80 v1
```

```text
Export:  C:\Users\User\surgical-exports\data\frames-cholec80-all-1fps-jpeg90-run-001
Excel:   C:\Users\User\surgical-exports\configs\cholec80-CVS.xlsx
Data:    C:\Users\User\cvs-review-portal\cholec80-data
Portal:  http://127.0.0.1:18080/
```

---

## 5. Verification and acceptance

<a id="verification-and-acceptance"></a>

These classes are separate. Do not treat one as the other.

### Cursor-recorded automated checks

Reported from implementation sessions in the project Poetry environment (Python 3.11). Not re-run for this documentation update.

Before the Summary-table change:

- `poetry run ruff check .` — exit 0
- `poetry run ruff format --check .` — exit 0
- `poetry run pyright` — 0 errors
- `poetry run pytest` — 159 passed
- `node --test` on the JS suites then in the tree — 30 passed

After the Summary-table change (same session class):

- Ruff check, Ruff format check, and Pyright — exit 0
- `poetry run pytest` — 161 passed
- `node --test` was run on the picker and summary JS files in that session (those files passed). That invocation was not recorded as a full 32-test JS suite.

### External review checks

Latest recorded external checks (not Cursor, and not re-run here):

- Before the Summary-table change: 159 Python tests and 30 JS tests passed.
- After the Summary-table change: 18 targeted Python tests and 32 JS tests passed.
- External Python checks used Python 3.12, not the project's locked Python 3.11 environment.
- External interactive browser verification was not performed.

### Owner local observations / acceptance

Before this Azure revision, the owner accepted the local video-catalog MVP as ready to deploy. Executive Summary was reported working locally before the interval Summary table was added; the Summary table was then requested and implemented. That local acceptance is not the Azure acceptance in [§7](#azure-checkpoint), and it is not a checklist of every earlier walkthrough step.

### Azure owner acceptance

Recorded in [§7](#azure-checkpoint). The previous `step2b-v1` deployment is not this acceptance, and neither deployment proves the historical worker-exit root cause.

---

## 6. Picker timer status

<a id="picker-timer-status"></a>

**Fixed.** `runExplicitImageSearch()` calls production `beginExplicitImageSearch()`, which `clearTimeout`s any pending `pickerSearchTimer` and sets the handle to `0` before the explicit `/intervals/search` load. Typing still schedules the 200 ms CSV filter. A keystroke immediately followed by Enter or Search image ID no longer lets that debounce replace the explicit search.

Verified in this correction: `node --check` on `app.js` and `video_catalog_picker_logic.mjs` exited 0. `node --test` on the four JS suites (`save_async_guards`, `interval_nav_save`, `video_catalog_picker`, `video_catalog_summary`) passed 33/33, including `typing then immediate Enter/Search cancels the pending CSV debounce`. This was not a Python quality-gate run.

---

## 7. Azure checkpoint

<a id="azure-checkpoint"></a>

Existing resources (do not recreate; do not delete the previous image or legacy metadata):

```text
Resource group:     rg-cvs-dev
Storage account:    stcvsdevvas01
Data container:     portal-data (private)
Container Registry: acrcvsdevvas01
Registry server:    acrcvsdevvas01-bqe6hec0efcdavf3.azurecr.io
Container App:      ca-cvs-portal-dev
Container name:     simple-hello-world-container
HTTPS ingress:      target port 8000
Revision mode:      Single
Resources:          1 CPU / 2 GiB
```

Public URL:

```text
https://ca-cvs-portal-dev.thankfulflower-9c425075.northeurope.azurecontainerapps.io/
```

Deployed image (current revision):

```text
acrcvsdevvas01-bqe6hec0efcdavf3.azurecr.io/cvs-review-portal:video-catalog-20261015-202611
Revision: ca-cvs-portal-dev--0000006
DATASET_LAYOUT=video_catalog
```

Previous image, retained and not the active revision:

```text
acrcvsdevvas01-bqe6hec0efcdavf3.azurecr.io/cvs-review-portal:step2b-v1
```

Already on Azure before this revision, and still in place:

- All 72,273 images. This deployment reused them; they were not uploaded again.
- The previous `runs-output` metadata.
- System-assigned managed identity with registry pull and `portal-data` access.
- Entra authentication and the owner’s application allowlist.
- `STORAGE_BACKEND=azure_blob`
- `AZURE_STORAGE_ACCOUNT_URL=https://stcvsdevvas01.blob.core.windows.net`
- `AZURE_BLOB_CONTAINER=portal-data`
- `IDENTITY_MODE=azure_app_service`

Video-catalog metadata uploaded for this deployment:

- 75 video JSON files and `videos.csv`.
- The CSV selects 10 videos, 70 intervals, and 10,018 images.

### Owner verification on this revision

Owner-accepted Azure MVP. Not exhaustive testing. Not an external production certification.

- Summary loads its interval table.
- Executive Summary works.
- Opening a video or interval, and removing it from the view, works.
- Frame navigation and zoom work.
- Comment Save works. The owner confirmed the requested persistence check.

Known limitation, explicitly accepted for this MVP: the initial Summary took approximately 3 minutes. Later browsing was faster. A cache contribution is a hypothesis, not a measured finding.

Worker terminations were observed on the previous deployment. Resources are 1 CPU / 2 GiB. The underlying cause was not proven. This revision does not establish that the historical worker-exit root cause is resolved.

---

## 8. Deployment status

Azure deployment of this video-catalog revision is complete. Performance improvements and CVS Local Review remain future work. They are not blockers for this MVP.

---

## 9. Planned follow-up

<a id="planned-follow-up"></a>

**CVS Local Review** is planned, not implemented.

Windows, offline, single-user distribution using the same portal code and local data, a launcher, bundled runtime/dependencies, and local comment persistence. No training or inference. Video playback is outside the initial image-review scope.

---

## 10. Future work (not blockers)

- Performance improvements. The accepted limitation is the initial Summary time of about 3 minutes on this Azure revision. Later browsing was faster. Cache contribution was not measured. Earlier search and frame-navigation latency remains an open product limitation, not a deploy blocker.
- Historical worker-exit root cause. Observed on the previous deployment. Not claimed resolved by revision `ca-cvs-portal-dev--0000006`.
- CVS Local Review ([§9](#planned-follow-up)). Planned, not implemented.
- Docker runtime gaps for a stock local container (port 8000, identity defaults, no data volume) — [README](../../README.md#docker). Separate from the completed Azure deployment.
- Separate thumbnail files; immediate browser-cache removal on logout.
