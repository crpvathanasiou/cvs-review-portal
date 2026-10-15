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
Stage: Step 2B owner-accepted for the current MVP
Performance: open limitation; no further performance changes before Azure
Local UI: http://127.0.0.1:18080/
Imported data root: C:\Users\User\cvs-review-portal\cholec80-data
Azure provisioning, upload, deployment, live verification: not started
```

---

## 2. Owner acceptance (Step 2B)

Step 2B is owner-accepted for the current MVP. The owner decided to proceed toward Azure without further performance changes now. Performance remains an open limitation.

Owner observations recorded for this acceptance:

- Searching `video02` took approximately 45 seconds.
- Searching again after a browser refresh took approximately 2 minutes.
- Add all matching intervals worked.
- Previous/Next navigation worked, taking approximately 2.5 seconds per transition, including revisits.
- Comment Save persisted after page refresh.
- Typing in an existing card was not interrupted while additional intervals loaded.

This list is the acceptance record. It does not mean every previously proposed walkthrough check was separately verified.

Browser image caching was verified in an earlier step. The navigation latency above does not establish whether image-cache reuse failed. Its cause has not been isolated through profiling.

---

## 3. Evidence classes

### Automated verification

Recorded before this documentation checkpoint. Not re-executed while writing these documents.

- `poetry run ruff check .` — exit 0
- `poetry run ruff format --check .` — exit 0
- `poetry run pyright` — exit 0, 0 errors
- `poetry run pytest` — exit 0, including `tests/test_interval_browse.py`
- `node --check` on the production web modules — recorded as passing
- `node --test tests/js/save_async_guards.test.mjs tests/js/interval_nav_save.test.mjs` — 19 passed

The JavaScript tests include delayed-response cases: a response for dataset A is dropped after switching to dataset B with the same segment id, and an older frame GET at revision 1 does not replace a newer Save at revision 2. Those tests are automated coverage. They are not the external review and they are not the owner browser session.

### External code review

External code review closed the reproduced failures in the Step 2B async-guard correction:

- a stale response from a previous dataset could still be applied
- an older frame read could roll back a newer persisted review revision

Production logic for those guards is `src/cvs_review_portal/web/interval_browse_logic.mjs`, registered by `src/cvs_review_portal/web/register_interval_browse_logic.mjs` and called from `src/cvs_review_portal/web/app.js`.

This closure is those reproduced failures. It is not a claim that external review separately approved every Step 2B behavior.

### Owner browser observations

The observations in §2. They are separate from the automated tests and from the code-review closure.

### Not executed for this checkpoint

- Quality gates, Node checks, and the importer
- Docker build, `docker compose up`, and any container smoke test
- Azure account, storage, upload, access configuration, deployment, and live cloud verification

---

## 4. Imported dataset checkpoint

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
  (separate image records preserved)
inference runs published with this import: none
catalog runs: []
dataset display_name: cholec80 v1
```

Local paths:

```text
Export:  C:\Users\User\surgical-exports\data\frames-cholec80-all-1fps-jpeg90-run-001
Excel:   C:\Users\User\surgical-exports\configs\cholec80-CVS.xlsx
Data:    C:\Users\User\cvs-review-portal\cholec80-data
Portal:  http://127.0.0.1:18080/
```

Completed before this checkpoint:

- Comments-only Save
- Browser image caching (earlier step)
- Step 2A real import
- Step 2B interval browsing and corrective review
- Owner acceptance, with performance left open

---

## 5. Exact next action

Guided Azure setup, in this order:

1. Establish account and subscription status.
2. Create storage.
3. Upload the prepared data.
4. Configure application access.
5. Deploy the Dockerized portal.
6. Verify it with real images.

Azure provisioning, live Azure verification, and deployment are not completed. Do not start that work from this documentation checkpoint. Do not treat performance as resolved.

---

## 6. Prerequisites still open

Concrete gaps in the current Docker runtime configuration (details and commands in [../../README.md](../../README.md#docker)):

- Container port is 8000. Compose sets `APP_ENV`, `APP_VERSION`, and `LOG_LEVEL` only. No volume is declared, and the image does not contain `cholec80-data` or `demo-data`.
- Unset identity defaults to `disabled`. `/health` can pass while the UI returns 401.
- Development identity allows loopback clients only, so it does not authenticate a browser that reaches a published container port.
- `.gitignore` and `.dockerignore` exclude `/cholec80-data/`. `git check-ignore` matches `cholec80-data/`. No files under that directory are tracked. `.env` remains excluded. `demo-data/` remains in the Docker build context.

Also still open, and unchanged by this checkpoint:

- Private Blob container, upload, managed identity / Easy Auth, and cloud verification
- Thumbnail pipeline (thumbnails use the full image-content endpoint)
- Immediate browser-cache removal on logout
- Per-image Summary table rows in interval browse (counts load only after an explicit summary action)
