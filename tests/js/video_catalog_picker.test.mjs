/**
 * Production video-catalog picker logic regressions (wired into app.js).
 */
import assert from "node:assert/strict";
import test from "node:test";

import {
  beginExplicitImageSearch,
  filterVideosFromCsv,
  imageContentUrlWithVideo,
  pickerSearchMode,
  reviewUrlWithVideo,
  videoLabelFromFilename,
} from "../../src/cvs_review_portal/web/video_catalog_picker_logic.mjs";

const VIDEOS = [
  {
    video_id: "v-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    video_name: "video02.mp4",
  },
  {
    video_id: "v-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    video_name: "video04.mp4",
  },
  {
    video_id: "v-cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    video_name: "video10.mp4",
  },
];

test("videoLabelFromFilename produces readable Video NN labels", () => {
  assert.equal(videoLabelFromFilename("video02.mp4"), "Video 02");
  assert.equal(videoLabelFromFilename("video10.mp4"), "Video 10");
});

test("typing filter uses CSV rows only (partial video name)", () => {
  const filtered = filterVideosFromCsv(VIDEOS, "video0");
  assert.equal(filtered.length, 2);
  assert.deepEqual(
    filtered.map((v) => v.video_name),
    ["video02.mp4", "video04.mp4"],
  );
});

test("typing filter matches readable label and technical id", () => {
  assert.equal(filterVideosFromCsv(VIDEOS, "Video 10").length, 1);
  assert.equal(
    filterVideosFromCsv(VIDEOS, VIDEOS[0].video_id.slice(0, 12)).length,
    1,
  );
});

test("pickerSearchMode: video_catalog typing never chooses intervals_search", () => {
  assert.equal(pickerSearchMode("video_catalog", "type"), "csv_filter");
  assert.equal(pickerSearchMode("video_catalog", "explicit"), "intervals_search");
  assert.equal(pickerSearchMode("legacy", "type"), "intervals_search");
});

test("partial video-name typing stays on csv_filter (no intervals/search)", () => {
  // Models app.js scheduleIntervalPickerSearch → trigger "type".
  assert.equal(pickerSearchMode("video_catalog", "type"), "csv_filter");
  const filtered = filterVideosFromCsv(VIDEOS, "video0");
  assert.equal(filtered.length, 2);
  // Explicit Enter / Search button is the only path to image discovery.
  assert.equal(pickerSearchMode("video_catalog", "explicit"), "intervals_search");
});

test("typing then immediate Enter/Search cancels the pending CSV debounce", () => {
  /** @type {Map<number, () => void>} */
  const pending = new Map();
  let nextId = 1;
  const setTimer = (fn) => {
    const id = nextId;
    nextId += 1;
    pending.set(id, fn);
    return id;
  };
  const clearTimer = (id) => {
    pending.delete(id);
  };
  /** @type {string[]} */
  const applied = [];
  const typingHandle = setTimer(() => {
    applied.push(pickerSearchMode("video_catalog", "type"));
  });
  const started = beginExplicitImageSearch(typingHandle, clearTimer);
  applied.push(pickerSearchMode("video_catalog", started.trigger));
  const leftover = pending.get(typingHandle);
  if (leftover) leftover();
  assert.equal(started.timerHandle, 0);
  assert.equal(pending.has(typingHandle), false);
  assert.deepEqual(applied, ["intervals_search"]);
});

test("image/review URLs stay path-stable and add optional video_id hint", () => {
  assert.equal(
    imageContentUrlWithVideo("ds", "v1", "img-1", null),
    "/api/datasets/ds/versions/v1/images/img-1/content",
  );
  assert.equal(
    imageContentUrlWithVideo("ds", "v1", "img-1", "vid-1"),
    "/api/datasets/ds/versions/v1/images/img-1/content?video_id=vid-1",
  );
  assert.equal(
    reviewUrlWithVideo("ds", "v1", "img-1", "vid-1"),
    "/api/datasets/ds/versions/v1/images/img-1/review?video_id=vid-1",
  );
});
