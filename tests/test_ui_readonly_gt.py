"""Source contracts for read-only ground truth and comments-only drafts."""

from __future__ import annotations

from pathlib import Path

WEB_JS = Path(__file__).resolve().parents[1] / "src" / "cvs_review_portal" / "web" / "app.js"


def _js() -> str:
    return WEB_JS.read_text(encoding="utf-8")


def test_ui_ground_truth_is_read_only_text() -> None:
    js = _js()
    assert "fillReadOnlyGroundTruth" in js
    assert "gt-select" not in js
    assert "ground_truth_editable" not in js
    assert "Editable" not in js
    assert "Fixed (locked)" not in js
    assert "function fillReadOnlyGroundTruth" in js
    # No ground-truth draft field.
    assert "groundTruth:" not in js
    assert "setCommentDraft" in js
    assert "Unsaved comment." in js
    assert "Save comment" in js
    assert "MAX_COMMENT_LENGTH" in js


def test_ui_summary_has_no_editability_column() -> None:
    js = _js()
    start = js.index("function renderSummary")
    end = js.index("function summaryRowMatches", start)
    summary = js[start:end]
    assert '"Editability"' not in summary
    assert "'Editability'" not in summary
    assert "Ground truth" in summary
