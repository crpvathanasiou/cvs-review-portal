/**
 * Video-catalog picker helpers used by app.js (production).
 *
 * Typing filters the CSV video list only. Cross-video image_id / display_id
 * lookup is an explicit action (Enter / Search), not every keystroke.
 */

/**
 * @param {string} filename
 * @returns {string}
 */
export function videoLabelFromFilename(filename) {
  const raw = String(filename || "");
  const stem = raw.includes(".") ? raw.slice(0, raw.lastIndexOf(".")) : raw;
  const lower = stem.toLowerCase();
  if (lower.startsWith("video")) {
    const suffix = stem.slice(5);
    const digits = Array.from(suffix)
      .filter((ch) => ch >= "0" && ch <= "9")
      .join("");
    if (digits) {
      return `Video ${digits.length <= 2 ? digits.padStart(2, "0") : digits}`;
    }
  }
  return stem || raw;
}

/**
 * Case-insensitive substring filter over CSV video rows (no JSON).
 *
 * @param {Array<{ video_id: string, video_name: string }>} videos
 * @param {string} query
 * @returns {Array<{ video_id: string, video_name: string }>}
 */
export function filterVideosFromCsv(videos, query) {
  const list = Array.isArray(videos) ? videos : [];
  const q = String(query || "").trim().toLowerCase();
  if (!q) return list.slice();
  return list.filter((video) => {
    const id = String(video.video_id || "").toLowerCase();
    const name = String(video.video_name || "").toLowerCase();
    const stem = name.includes(".") ? name.slice(0, name.lastIndexOf(".")) : name;
    const label = videoLabelFromFilename(video.video_name).toLowerCase();
    return id.includes(q) || name.includes(q) || stem.includes(q) || label.includes(q);
  });
}

/**
 * Decide whether the picker should call /intervals/search (image discovery).
 * Typing never triggers this for video_catalog; only an explicit search action.
 *
 * @param {"video_catalog"|"legacy"|null|undefined} datasetLayout
 * @param {"type"|"explicit"} trigger
 * @returns {"csv_filter"|"intervals_search"}
 */
export function pickerSearchMode(datasetLayout, trigger) {
  if (datasetLayout === "video_catalog" && trigger === "type") {
    return "csv_filter";
  }
  if (datasetLayout === "video_catalog" && trigger === "explicit") {
    return "intervals_search";
  }
  return "intervals_search";
}

/**
 * Cancel a pending typing debounce before explicit image search.
 * The returned handle is 0 so a later fire of the old id is a no-op.
 *
 * @param {number} timerHandle
 * @param {(handle: number) => void} clearTimeoutFn
 * @returns {{ timerHandle: 0, trigger: "explicit" }}
 */
export function beginExplicitImageSearch(timerHandle, clearTimeoutFn) {
  const handle = Number(timerHandle) || 0;
  if (handle) clearTimeoutFn(handle);
  return { timerHandle: 0, trigger: "explicit" };
}

/**
 * Build content URL; optional video_id is a stable ownership hint (not cache-busting).
 *
 * @param {string} datasetId
 * @param {string} version
 * @param {string} imageId
 * @param {string | null | undefined} videoId
 */
export function imageContentUrlWithVideo(datasetId, version, imageId, videoId) {
  let url =
    `/api/datasets/${encodeURIComponent(datasetId)}` +
    `/versions/${encodeURIComponent(version)}` +
    `/images/${encodeURIComponent(imageId)}/content`;
  if (videoId) {
    url += `?video_id=${encodeURIComponent(videoId)}`;
  }
  return url;
}

/**
 * @param {string} datasetId
 * @param {string} version
 * @param {string} imageId
 * @param {string | null | undefined} videoId
 */
export function reviewUrlWithVideo(datasetId, version, imageId, videoId) {
  let url =
    `/api/datasets/${encodeURIComponent(datasetId)}` +
    `/versions/${encodeURIComponent(version)}` +
    `/images/${encodeURIComponent(imageId)}/review`;
  if (videoId) {
    url += `?video_id=${encodeURIComponent(videoId)}`;
  }
  return url;
}
