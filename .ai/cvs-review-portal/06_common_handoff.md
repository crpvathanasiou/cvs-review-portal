# 06 — Common Project Handoff

## 1. Purpose

Shared operational handoff for CVS Review Portal: current state, evidence, and exact next action.

---

## 2. Documentation roles

```text
08_portal_specification.md → Current product + Step contracts (source of truth)
05_code_quality_standards.md → Engineering standards (legacy examples flagged)
06_common_handoff.md → This file
07_code_map.md → Implemented code map
00_*/01_*/02_*/04_* → LEGACY template content
```

---

## 3. Current snapshot

```text
Project: CVS Review Portal
Stage: Step 3 MVP finishing pass (comments-only Save; no audit history)
Package/factory/Docker/deps: preserved (+ filelock, azure-storage-blob, azure-identity)
Local UI URL: http://127.0.0.1:18080/
```

---

## 4. MVP Save summary

1. **Comments-only Save** via PUT review (`comments` + `expected_revision`); ground truth remains read-only.
2. **Persistence**: schema-v1 current-state `ReviewRecord` on write; existing v1/v2 reviews remain readable (comments + GT override preserved). No bulk migration.
3. **Concurrency**: local cross-process lock + atomic replace; Azure ETag conditional writes; stale revision → 409 with draft preserved.
4. **Unconfirmed Save**: lost/ambiguous response → “Save could not be confirmed” + read-only server refresh; draft preserved; no automatic rewrite; no receipt state machine.
5. **Removed from MVP**: History button/modal/endpoint; operation receipts; request_id idempotency UI/API.
6. **Identity / isolation**: explicit identity modes; dataset/run isolation; image viewing unchanged.

Owner local `demo-data/` was not regenerated or deleted. Azure resource creation and cloud deployment remain pending. External approval is not claimed.

---

## 5. Exact next action

```text
Owner local Save verification on http://127.0.0.1:18080/ (IDENTITY_MODE=development), then external review of this finishing pass before Azure setup/deployment.
```

---

## 6. Limitations

* Cloud login / Easy Auth end-to-end verification not done
* Live Azure Blob integration NOT RUN
* Interactive browser Save checks: NOT RUN (owner walkthrough below)
* Audit history / annotation portal not in scope
* `/ready` is not dataset/Azure readiness

---

## 7. Verification evidence

```text
poetry run ruff check .: VERIFIED (exit 0)
poetry run ruff format --check .: VERIFIED (exit 0)
poetry run pyright: VERIFIED (exit 0 — 0 errors)
poetry run pytest: VERIFIED (exit 0 — 95 tests collected/passed)
node --check src/cvs_review_portal/web/app.js: VERIFIED (exit 0)
node --test tests/js/save_async_guards.test.mjs: VERIFIED (exit 0 — 7 passed)
Interactive browser (typing/Save/run-switch/unconfirmed): NOT RUN
Live Azure Blob integration: NOT RUN
External review approval: NOT CLAIMED
```

### Owner walkthrough

1. `.env` with `IDENTITY_MODE=development`.
2. `poetry run uvicorn cvs_review_portal.main:app --host 127.0.0.1 --port 18080 --reload`
3. Open a frame, edit comment, Save, reload — comment persists (including empty).
4. Start Save, switch Run in the same dataset/version — Save must not stick pending.
5. Two-tab stale revision → conflict UI preserves draft; refresh server comment; resolve then re-edit.
6. No History control is present.
