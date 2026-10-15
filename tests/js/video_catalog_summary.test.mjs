/**
 * Production Summary / Executive Summary helpers (wired into app.js).
 */
import assert from "node:assert/strict";
import test from "node:test";

import {
  datasetIdentityFromMeta,
  filterSummaryIntervals,
  formatIntervalGroundTruth,
  shouldHideSummaryToolbar,
  shouldShowSummaryLoadBar,
  summaryApiPath,
  summaryLoadButtonLabel,
} from "../../src/cvs_review_portal/web/video_catalog_summary_logic.mjs";

test("datasetIdentityFromMeta prefers browseMeta when datasetDetail is null", () => {
  const identity = datasetIdentityFromMeta(
    { dataset_id: "cholec80", dataset_version: "v1" },
    null,
  );
  assert.deepEqual(identity, { datasetId: "cholec80", datasetVersion: "v1" });
});

test("datasetIdentityFromMeta returns null when neither meta is available", () => {
  assert.equal(datasetIdentityFromMeta(null, null), null);
});

test("interval browse shows Load bars until summary is loaded", () => {
  assert.equal(
    shouldShowSummaryLoadBar({ browseMode: "interval", summaryLoaded: false }),
    true,
  );
  assert.equal(
    shouldShowSummaryLoadBar({ browseMode: "interval", summaryLoaded: true }),
    false,
  );
  assert.equal(
    shouldShowSummaryLoadBar({ browseMode: "image", summaryLoaded: false }),
    false,
  );
  assert.equal(
    shouldHideSummaryToolbar({ browseMode: "interval", summaryLoaded: false }),
    true,
  );
});

test("summary load button labels reflect loading state", () => {
  assert.equal(summaryLoadButtonLabel(false, "effective"), "Load effective summary");
  assert.equal(summaryLoadButtonLabel(false, "executive"), "Load executive summary");
  assert.equal(summaryLoadButtonLabel(true, "effective"), "Loading summary…");
  assert.equal(summaryLoadButtonLabel(true, "executive"), "Loading summary…");
});

test("summaryApiPath stays stable and optional run_id is query-only", () => {
  assert.equal(
    summaryApiPath("ds", "v1", null),
    "/api/datasets/ds/versions/v1/summary",
  );
  assert.equal(
    summaryApiPath("ds", "v1", "run-1"),
    "/api/datasets/ds/versions/v1/summary?run_id=run-1",
  );
});

test("formatIntervalGroundTruth keeps Mixed explicit", () => {
  assert.equal(formatIntervalGroundTruth(0), "0");
  assert.equal(formatIntervalGroundTruth(1), "1");
  assert.equal(formatIntervalGroundTruth("Mixed"), "Mixed");
});

test("filterSummaryIntervals matches video label and Mixed GT", () => {
  const rows = [
    {
      video_label: "Video 01",
      time_interval: "00:10–00:20",
      ground_truth: "Mixed",
      image_count: 2,
      segment_id: "seg-a",
      video_id: "vid-a",
    },
    {
      video_label: "Video 02",
      time_interval: "00:30–00:40",
      ground_truth: 0,
      image_count: 1,
      segment_id: "seg-b",
      video_id: "vid-b",
    },
  ];
  assert.equal(filterSummaryIntervals(rows, "Video 02").length, 1);
  assert.equal(filterSummaryIntervals(rows, "mixed").length, 1);
  assert.equal(filterSummaryIntervals(rows, "").length, 2);
});
