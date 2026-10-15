/**
 * Production interval-browse async guards and frame reconciliation (Step 2B correction).
 *
 * Used by classic `app.js` via `register_interval_browse_logic.mjs` and by Node tests.
 * Save continuation remains independent of run selection (dataset/version/image only).
 */

/**
 * @typedef {{
 *   datasetId: string,
 *   datasetVersion: string,
 *   segmentId: string,
 *   cardId: string,
 *   loadGen: number,
 *   frameIndex: number,
 *   imageId: string,
 *   selectedRunId: string | null,
 *   selectionGen: number,
 * }} IntervalFrameLoadToken
 */

/**
 * @typedef {{
 *   datasetId: string,
 *   datasetVersion: string,
 *   segmentId: string,
 *   cardId: string,
 *   selectionGen: number,
 * }} IntervalFramesEnsureToken
 */

/**
 * @typedef {{
 *   datasetId: string,
 *   datasetVersion: string,
 *   pickerSession: number,
 *   requestId: number,
 *   query: string,
 *   offset: number,
 *   selectionGen: number,
 * }} PickerRequestToken
 */

/**
 * @typedef {{
 *   datasetId: string,
 *   datasetVersion: string,
 *   selectionGen: number,
 *   batchId: number,
 * }} BatchAddToken
 */

/**
 * Navigation without wraparound (production Previous/Next).
 * @param {number} current
 * @param {number} delta
 * @param {number} length
 * @returns {number | null} next index, or null when blocked at a boundary
 */
export function nextFrameIndex(current, delta, length) {
  if (!Number.isFinite(current) || !Number.isFinite(delta) || !Number.isFinite(length)) {
    return null;
  }
  if (length <= 0) return null;
  const next = current + delta;
  if (next < 0 || next >= length) return null;
  return next;
}

/**
 * @param {IntervalFrameLoadToken} token
 * @param {{
 *   currentIdentity: () => ({ datasetId: string, datasetVersion: string } | null),
 *   findOpenIntervalByCardId: (cardId: string) => (any | null),
 *   selectedRunId: () => (string | null),
 *   selectionGen: () => number,
 * }} deps
 */
export function intervalFrameLoadStillValid(token, deps) {
  if (!token) return false;
  const identity = deps.currentIdentity();
  if (!identity) return false;
  if (
    identity.datasetId !== token.datasetId ||
    identity.datasetVersion !== token.datasetVersion
  ) {
    return false;
  }
  if (deps.selectionGen() !== token.selectionGen) return false;
  const open = deps.findOpenIntervalByCardId(token.cardId);
  if (!open) return false;
  if (open.segmentId !== token.segmentId) return false;
  if (open.loadGen !== token.loadGen) return false;
  // Prediction-bearing and dataset-only requests both bind to the run context
  // captured at fetch start; a run switch invalidates the in-flight response.
  if ((deps.selectedRunId() || null) !== (token.selectedRunId || null)) return false;
  return true;
}

/**
 * @param {IntervalFramesEnsureToken} token
 * @param {{
 *   currentIdentity: () => ({ datasetId: string, datasetVersion: string } | null),
 *   findOpenIntervalByCardId: (cardId: string) => (any | null),
 *   selectionGen: () => number,
 * }} deps
 */
export function intervalFramesEnsureStillValid(token, deps) {
  if (!token) return false;
  const identity = deps.currentIdentity();
  if (!identity) return false;
  if (
    identity.datasetId !== token.datasetId ||
    identity.datasetVersion !== token.datasetVersion
  ) {
    return false;
  }
  if (deps.selectionGen() !== token.selectionGen) return false;
  const open = deps.findOpenIntervalByCardId(token.cardId);
  if (!open) return false;
  if (open.segmentId !== token.segmentId) return false;
  return true;
}

/**
 * @param {PickerRequestToken} token
 * @param {{
 *   currentIdentity: () => ({ datasetId: string, datasetVersion: string } | null),
 *   pickerSession: () => number,
 *   pickerRequestId: () => number,
 *   pickerSearch: () => string,
 *   pickerOffset: () => number,
 *   selectionGen: () => number,
 * }} deps
 */
export function pickerRequestStillValid(token, deps) {
  if (!token) return false;
  const identity = deps.currentIdentity();
  if (!identity) return false;
  if (
    identity.datasetId !== token.datasetId ||
    identity.datasetVersion !== token.datasetVersion
  ) {
    return false;
  }
  if (deps.selectionGen() !== token.selectionGen) return false;
  if (deps.pickerSession() !== token.pickerSession) return false;
  if (deps.pickerRequestId() !== token.requestId) return false;
  if (deps.pickerSearch().trim() !== token.query) return false;
  if (deps.pickerOffset() !== token.offset) return false;
  return true;
}

/**
 * @param {BatchAddToken} token
 * @param {{
 *   currentIdentity: () => ({ datasetId: string, datasetVersion: string } | null),
 *   selectionGen: () => number,
 *   activeBatchId: () => number,
 * }} deps
 */
export function batchAddStillValid(token, deps) {
  if (!token) return false;
  const identity = deps.currentIdentity();
  if (!identity) return false;
  if (
    identity.datasetId !== token.datasetId ||
    identity.datasetVersion !== token.datasetVersion
  ) {
    return false;
  }
  if (deps.selectionGen() !== token.selectionGen) return false;
  if (deps.activeBatchId() !== token.batchId) return false;
  return true;
}

/**
 * Compare persisted revisions for the same dataset/version/image.
 * An older frame response must not replace newer review state from Save/refresh.
 * Drafts live outside the image object and are preserved independently.
 *
 * @param {any | null | undefined} existing
 * @param {any} incoming
 * @returns {{ image: any, rolledBackReview: boolean }}
 */
export function reconcileFrameImage(existing, incoming) {
  if (!incoming || typeof incoming !== "object") {
    return { image: existing || incoming, rolledBackReview: false };
  }
  if (!existing || typeof existing !== "object") {
    return { image: incoming, rolledBackReview: false };
  }
  if (existing.image_id && incoming.image_id && existing.image_id !== incoming.image_id) {
    return { image: incoming, rolledBackReview: false };
  }
  const existingRev =
    typeof existing.persisted_revision === "number" && Number.isFinite(existing.persisted_revision)
      ? existing.persisted_revision
      : 0;
  const incomingRev =
    typeof incoming.persisted_revision === "number" && Number.isFinite(incoming.persisted_revision)
      ? incoming.persisted_revision
      : 0;
  if (incomingRev < existingRev) {
    return {
      image: {
        ...incoming,
        review: existing.review,
        persisted_revision: existing.persisted_revision,
        effective_comments: existing.effective_comments,
        effective_ground_truth: existing.effective_ground_truth,
      },
      rolledBackReview: true,
    };
  }
  return { image: incoming, rolledBackReview: false };
}

/**
 * Cache key scoped by dataset identity so image IDs cannot cross datasets.
 * @param {string} datasetId
 * @param {string} datasetVersion
 * @param {string} imageId
 */
export function imageCacheKey(datasetId, datasetVersion, imageId) {
  return `${datasetId}\0${datasetVersion}\0${imageId}`;
}

/**
 * Production frame-load orchestration with injected IO (testable; used by app.js).
 *
 * @param {object} deps
 * @param {string} segmentId
 * @param {number} frameIndex
 * @param {{ predictionRefresh?: boolean }} [options]
 */
export async function executeLoadIntervalFrame(deps, segmentId, frameIndex, options) {
  const predictionRefresh = Boolean(options && options.predictionRefresh);
  const identity = deps.currentIdentity();
  const open = deps.findOpenInterval(segmentId);
  if (!open || !identity) return { outcome: "noop" };

  if (!open.frames) {
    const ensured = await deps.ensureIntervalFrames(open.cardId);
    if (ensured && ensured.outcome === "stale") return { outcome: "stale" };
  }

  const refreshed = deps.findOpenIntervalByCardId(open.cardId);
  if (!refreshed || !refreshed.frames) return { outcome: "noop" };
  if (frameIndex < 0 || frameIndex >= refreshed.frames.length) return { outcome: "noop" };

  const frame = refreshed.frames[frameIndex];
  const loadGen = refreshed.loadGen + 1;
  refreshed.loadGen = loadGen;
  refreshed.currentIndex = frameIndex;
  refreshed.errorMessage = null;

  const previousImageId =
    refreshed.currentImage && refreshed.currentImage.image_id
      ? refreshed.currentImage.image_id
      : null;

  if (!predictionRefresh) {
    refreshed.status = "loading";
    refreshed.currentImage = null;
    refreshed.displayId = frame.display_id || null;
    refreshed.prediction = null;
    deps.onCardLoading?.(refreshed);
  } else {
    refreshed.status = refreshed.currentImage ? "idle" : "loading";
    deps.onCardPredictionPending?.(refreshed);
  }

  /** @type {IntervalFrameLoadToken} */
  const token = {
    datasetId: identity.datasetId,
    datasetVersion: identity.datasetVersion,
    segmentId: refreshed.segmentId,
    cardId: refreshed.cardId,
    loadGen,
    frameIndex,
    imageId: frame.image_id,
    selectedRunId: deps.selectedRunId() || null,
    selectionGen: deps.selectionGen(),
  };

  try {
    const view = await deps.fetchFrameView({
      datasetId: token.datasetId,
      datasetVersion: token.datasetVersion,
      imageId: frame.image_id,
      runId: token.selectedRunId,
    });
    if (!intervalFrameLoadStillValid(token, deps)) {
      return { outcome: "stale" };
    }
    const current = deps.findOpenIntervalByCardId(token.cardId);
    if (!current) return { outcome: "stale" };

    const existing = deps.getCachedImage(token.datasetId, token.datasetVersion, frame.image_id);
    const reconciled = reconcileFrameImage(existing, view.image);
    deps.setCachedImage(token.datasetId, token.datasetVersion, frame.image_id, reconciled.image);

    current.currentImage = reconciled.image;
    current.displayId = view.display_id || frame.display_id || null;
    current.prediction = view.prediction || null;
    current.status = "idle";
    current.errorMessage = null;

    const sameImage =
      predictionRefresh && previousImageId && previousImageId === reconciled.image.image_id;
    if (sameImage) {
      deps.onCardPredictionUpdated?.(current);
    } else {
      deps.onCardUpdated?.(current);
    }
    return { outcome: "loaded", image: reconciled.image, rolledBackReview: reconciled.rolledBackReview };
  } catch (err) {
    if (!intervalFrameLoadStillValid(token, deps)) {
      return { outcome: "stale" };
    }
    const current = deps.findOpenIntervalByCardId(token.cardId);
    if (!current) return { outcome: "stale" };
    if (predictionRefresh && current.currentImage) {
      // Keep the visible frame; surface prediction failure without wiping review UI.
      current.prediction = null;
      current.errorMessage = null;
      current.status = "idle";
      deps.onCardPredictionUpdated?.(current);
      deps.onPredictionError?.(err);
      return { outcome: "prediction_error", error: err };
    }
    current.status = "error";
    current.errorMessage = deps.errorMessage(err) || "Failed to load frame.";
    current.currentImage = null;
    deps.onCardUpdated?.(current);
    return { outcome: "error", error: err };
  }
}

/**
 * @param {object} deps
 * @param {string} cardId
 */
export async function executeEnsureIntervalFrames(deps, cardId) {
  const identity = deps.currentIdentity();
  const open = deps.findOpenIntervalByCardId(cardId);
  if (!open || !identity) return { outcome: "noop" };
  if (open.frames) return { outcome: "ready", frames: open.frames };

  /** @type {IntervalFramesEnsureToken} */
  const token = {
    datasetId: identity.datasetId,
    datasetVersion: identity.datasetVersion,
    segmentId: open.segmentId,
    cardId: open.cardId,
    selectionGen: deps.selectionGen(),
  };

  try {
    const framesView = await deps.fetchIntervalFrames({
      datasetId: token.datasetId,
      datasetVersion: token.datasetVersion,
      segmentId: token.segmentId,
    });
    if (!intervalFramesEnsureStillValid(token, deps)) {
      return { outcome: "stale" };
    }
    const current = deps.findOpenIntervalByCardId(token.cardId);
    if (!current) return { outcome: "stale" };
    current.frames = Array.isArray(framesView.frames) ? framesView.frames : [];
    current.title = framesView.title || current.title;
    current.imageCount = framesView.image_count || current.frames.length;
    return { outcome: "ready", frames: current.frames };
  } catch (err) {
    if (!intervalFramesEnsureStillValid(token, deps)) {
      return { outcome: "stale" };
    }
    return { outcome: "error", error: err };
  }
}

/**
 * Focus existing interval or create a new card instance for the segment.
 * @param {object} deps
 * @param {string} segmentId
 * @param {{ title?: string, imageCount?: number, targetImageId?: string | null }} [meta]
 */
export async function executeAddOrFocusInterval(deps, segmentId, meta) {
  const identity = deps.currentIdentity();
  if (!identity) return { outcome: "noop" };
  const selectionGen = deps.selectionGen();

  const existing = deps.findOpenInterval(segmentId);
  if (existing) {
    deps.setActiveTabAnalytical?.();
    let index = existing.currentIndex || 0;
    if (meta && meta.targetImageId) {
      if (!existing.frames) {
        const ensured = await deps.ensureIntervalFrames(existing.cardId);
        if (ensured && ensured.outcome === "stale") return { outcome: "stale" };
      }
      if (
        deps.selectionGen() !== selectionGen ||
        !deps.currentIdentity() ||
        deps.currentIdentity().datasetId !== identity.datasetId ||
        deps.currentIdentity().datasetVersion !== identity.datasetVersion
      ) {
        return { outcome: "stale" };
      }
      const again = deps.findOpenIntervalByCardId(existing.cardId);
      if (!again) return { outcome: "stale" };
      if (again.frames) {
        const found = again.frames.findIndex((f) => f.image_id === meta.targetImageId);
        if (found >= 0) index = found;
      }
      const loaded = await deps.loadIntervalFrame(segmentId, index);
      if (loaded && loaded.outcome === "stale") return { outcome: "stale" };
    }
    deps.focusIntervalCard?.(segmentId);
    return { outcome: "focused", cardId: existing.cardId };
  }

  const card = deps.createOpenIntervalCard({
    segmentId,
    title: (meta && meta.title) || segmentId,
    imageCount: (meta && meta.imageCount) || 0,
  });
  deps.appendIntervalCard?.(card);

  try {
    const ensured = await deps.ensureIntervalFrames(card.cardId);
    if (ensured && ensured.outcome === "stale") return { outcome: "stale" };
    if (
      deps.selectionGen() !== selectionGen ||
      !deps.currentIdentity() ||
      deps.currentIdentity().datasetId !== identity.datasetId ||
      deps.currentIdentity().datasetVersion !== identity.datasetVersion
    ) {
      return { outcome: "stale" };
    }
    const open = deps.findOpenIntervalByCardId(card.cardId);
    if (!open) return { outcome: "stale" };
    if (!open.frames || open.frames.length === 0) {
      open.status = "error";
      open.errorMessage = "Interval has no frames.";
      deps.onCardUpdated?.(open);
      return { outcome: "error", errorMessage: open.errorMessage };
    }
    let index = 0;
    if (meta && meta.targetImageId) {
      const found = open.frames.findIndex((f) => f.image_id === meta.targetImageId);
      if (found >= 0) index = found;
    }
    const loaded = await deps.loadIntervalFrame(segmentId, index);
    if (loaded && loaded.outcome === "stale") return { outcome: "stale" };
    if (
      deps.selectionGen() !== selectionGen ||
      !deps.currentIdentity() ||
      deps.currentIdentity().datasetId !== identity.datasetId
    ) {
      return { outcome: "stale" };
    }
    deps.focusIntervalCard?.(segmentId);
    return { outcome: "added", cardId: card.cardId };
  } catch (err) {
    if (
      deps.selectionGen() !== selectionGen ||
      !deps.currentIdentity() ||
      deps.currentIdentity().datasetId !== identity.datasetId
    ) {
      return { outcome: "stale" };
    }
    const open = deps.findOpenIntervalByCardId(card.cardId);
    if (!open) return { outcome: "stale" };
    open.status = "error";
    open.errorMessage = deps.errorMessage(err) || "Failed to open interval.";
    deps.onCardUpdated?.(open);
    return { outcome: "error", error: err };
  }
}
