/**
 * Summary / Executive Summary helpers used by app.js (production).
 *
 * Interval + video_catalog browse must use browse metadata for identity
 * (datasetDetail is intentionally null). Load bars stay explicit.
 */

/**
 * @param {{ dataset_id?: string, dataset_version?: string } | null | undefined} browseMeta
 * @param {{ dataset_id?: string, dataset_version?: string } | null | undefined} datasetDetail
 * @returns {{ datasetId: string, datasetVersion: string } | null}
 */
export function datasetIdentityFromMeta(browseMeta, datasetDetail) {
  const meta = browseMeta || datasetDetail;
  if (!meta || !meta.dataset_id || !meta.dataset_version) return null;
  return {
    datasetId: String(meta.dataset_id),
    datasetVersion: String(meta.dataset_version),
  };
}

/**
 * @param {{
 *   browseMode: "interval"|"image"|null|undefined,
 *   summaryLoaded: boolean,
 * }} state
 * @returns {boolean}
 */
export function shouldShowSummaryLoadBar(state) {
  return state.browseMode === "interval" && !state.summaryLoaded;
}

/**
 * @param {{
 *   browseMode: "interval"|"image"|null|undefined,
 *   summaryLoaded: boolean,
 * }} state
 * @returns {boolean}
 */
export function shouldHideSummaryToolbar(state) {
  return state.browseMode === "interval" && !state.summaryLoaded;
}

/**
 * @param {boolean} summaryLoading
 * @param {"effective"|"executive"} kind
 * @returns {string}
 */
export function summaryLoadButtonLabel(summaryLoading, kind) {
  if (summaryLoading) return "Loading summary…";
  return kind === "executive" ? "Load executive summary" : "Load effective summary";
}

/**
 * Build GET .../summary path for the current dataset (+ optional run).
 *
 * @param {string} datasetId
 * @param {string} datasetVersion
 * @param {string | null | undefined} runId
 * @returns {string}
 */
export function summaryApiPath(datasetId, datasetVersion, runId) {
  let path =
    `/api/datasets/${encodeURIComponent(datasetId)}` +
    `/versions/${encodeURIComponent(datasetVersion)}/summary`;
  if (runId) path += `?run_id=${encodeURIComponent(runId)}`;
  return path;
}

/**
 * Format interval ground-truth cell (0, 1, or Mixed).
 *
 * @param {0|1|"Mixed"|string|number|null|undefined} value
 * @returns {string}
 */
export function formatIntervalGroundTruth(value) {
  if (value === "Mixed" || value === "mixed") return "Mixed";
  if (value === 0 || value === "0") return "0";
  if (value === 1 || value === "1") return "1";
  return String(value ?? "");
}

/**
 * Filter interval summary rows by a case-insensitive substring.
 *
 * @param {Array<{
 *   video_label?: string,
 *   time_interval?: string,
 *   ground_truth?: 0|1|"Mixed",
 *   image_count?: number,
 *   segment_id?: string,
 *   video_id?: string,
 * }>} intervals
 * @param {string} query
 */
export function filterSummaryIntervals(intervals, query) {
  const list = Array.isArray(intervals) ? intervals : [];
  const q = String(query || "").trim().toLowerCase();
  if (!q) return list.slice();
  return list.filter((row) => {
    const parts = [
      row.video_label,
      row.time_interval,
      formatIntervalGroundTruth(row.ground_truth),
      row.image_count,
      row.segment_id,
      row.video_id,
    ];
    return parts.some((part) => String(part ?? "").toLowerCase().includes(q));
  });
}
