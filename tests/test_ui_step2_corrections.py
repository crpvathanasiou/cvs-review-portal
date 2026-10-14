"""Focused regression checks for Step 2 UI corrections (source contracts)."""

from __future__ import annotations

from pathlib import Path

WEB_JS = Path(__file__).resolve().parents[1] / "src" / "cvs_review_portal" / "web" / "app.js"
WEB_CSS = Path(__file__).resolve().parents[1] / "src" / "cvs_review_portal" / "web" / "styles.css"


def _js() -> str:
    return WEB_JS.read_text(encoding="utf-8")


def _css() -> str:
    return WEB_CSS.read_text(encoding="utf-8")


def test_analytical_images_do_not_use_hidden_for_lazy_pending() -> None:
    js = _js()
    css = _css()
    # buildMediaColumn must not hide the pending lazy image from layout.
    media_start = js.index("function buildMediaColumn")
    media_end = js.index("function buildDetailsColumn", media_start)
    media = js[media_start:media_end]
    assert "img.hidden = true" not in media
    assert 'loading: "lazy"' in media or "loading: 'lazy'" in media
    assert 'addEventListener("load"' in media or "addEventListener('load'" in media
    assert "img.src =" in media
    # Handlers must be registered before src assignment.
    assert media.index('addEventListener("load"') < media.index("img.src =")
    assert "is-pending" in media
    assert "is-loaded" in media
    assert ".frame-image.is-pending" in css
    assert "opacity: 0" in css


def test_select_run_clears_summary_and_commits_atomically() -> None:
    js = _js()
    start = js.index("async function selectRun")
    end = js.index("function refreshRunDependentViews", start)
    body = js[start:end]
    assert "state.summary = null" in body
    assert "state.runDetail = null" in body
    assert "Promise.all" in body
    assert "force" in body
    assert "runLoadError" in body
    # Dataset identity / cards / drafts are not cleared in selectRun.
    assert "state.openCards = []" not in body
    assert "state.drafts" not in body or "state.drafts.clear" not in body
    assert "state.datasetDetail = null" not in body


def test_run_load_failure_is_not_described_as_no_prediction() -> None:
    js = _js()
    pred_start = js.index("function buildPredictionBlock")
    pred_end = js.index("function updateCardDraftChrome", pred_start)
    pred = js[pred_start:pred_end]
    assert "runLoadError" in pred
    assert "Prediction unavailable — run failed to load." in pred
    # "No prediction" remains for genuine missing predictions after a successful load.
    assert "NO_PREDICTION" in pred
    assert pred.index("runLoadError") < pred.index("NO_PREDICTION")


def test_retry_uses_force_and_generation_protection() -> None:
    js = _js()
    assert "selectRun(state.selectedRunId, { force: true })" in js
    assert "bumpSelectionGen" in js
    assert "gen !== state.selectionGen" in js
    assert "refreshRunDependentViews" in js
