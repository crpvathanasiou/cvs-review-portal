/**
 * CVS Review Portal — Step 2B / Step 3 UI
 *
 * Same-origin fetch against /api. All API text is rendered via textContent /
 * safe DOM APIs. Drafts live in memory only, keyed by dataset identity + image_id.
 * Comments-only Save uses expected_revision concurrency (latest comment only).
 * Provenance-backed datasets browse by interval; datasets without provenance keep
 * per-image cards.
 */
(() => {
  "use strict";

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  const LABEL_ABSENT = "0 — CVS absent";
  const LABEL_PRESENT = "1 — CVS present";
  const MAX_COMMENT_LENGTH = 8000;
  const BANNER_UNSAVED = "Unsaved comment.";
  const BANNER_PENDING = "Saving comment…";
  const BANNER_UNCONFIRMED =
    "Save could not be confirmed. Your draft is preserved. Refresh the server comment to compare — this does not resend the Save.";
  const BANNER_CONFLICT =
    "Revision conflict — another Save changed this review. Your text is preserved. Compare with the current server comment, then re-edit before saving again.";
  const NO_PREDICTION = "No prediction";
  const METRICS_SNAPSHOT_NOTE =
    "Metrics use the ground-truth snapshot recorded for this run.";
  const PICKER_PAGE_SIZE = 24;

  /** @param {unknown} value */
  function isBinaryLabel(value) {
    return value === 0 || value === 1;
  }

  /** @param {unknown} value */
  function formatBinaryLabel(value) {
    if (value === 0) return LABEL_ABSENT;
    if (value === 1) return LABEL_PRESENT;
    return "—";
  }

  /** @param {unknown} value */
  function formatProbability(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) return null;
    return String(value);
  }

  /** @param {unknown} value */
  function formatMetric(value) {
    if (value === null || value === undefined) return "N/A";
    if (typeof value !== "number" || !Number.isFinite(value)) return "N/A";
    return String(value);
  }

  /** @param {string} datasetId @param {string} version @param {string} imageId */
  function draftKey(datasetId, version, imageId) {
    return `${datasetId}\0${version}\0${imageId}`;
  }

  /** @param {string} datasetId @param {string} version */
  function datasetKey(datasetId, version) {
    return `${datasetId}\0${version}`;
  }

  /** @returns {typeof globalThis.CvsVideoCatalogPickerLogic} */
  function videoCatalogLogic() {
    const logic = globalThis.CvsVideoCatalogPickerLogic;
    if (!logic) {
      throw new Error("Video catalog picker logic module failed to load.");
    }
    return logic;
  }

  function videoCatalogSummaryLogic() {
    const logic = globalThis.CvsVideoCatalogSummaryLogic;
    if (!logic) {
      throw new Error("Video catalog summary logic module failed to load.");
    }
    return logic;
  }

  /**
   * Stable image content URL. Optional video_id is an ownership hint for
   * video_catalog direct resolution (not a cache-busting parameter).
   * @param {string} datasetId @param {string} version @param {string} imageId
   * @param {string | null} [videoId]
   */
  function imageContentUrl(datasetId, version, imageId, videoId) {
    return videoCatalogLogic().imageContentUrlWithVideo(
      datasetId,
      version,
      imageId,
      videoId || null,
    );
  }

  /**
   * @param {string} datasetId @param {string} version @param {string} imageId
   * @param {string | null} [videoId]
   */
  function reviewUrl(datasetId, version, imageId, videoId) {
    return videoCatalogLogic().reviewUrlWithVideo(
      datasetId,
      version,
      imageId,
      videoId || null,
    );
  }

  /** Resolve owning video_id from an open interval card when known. */
  function videoIdForImage(imageId) {
    for (const open of state.openIntervals) {
      if (open.videoId && open.currentImage && open.currentImage.image_id === imageId) {
        return open.videoId;
      }
      if (open.videoId && Array.isArray(open.frames)) {
        if (open.frames.some((frame) => frame.image_id === imageId)) {
          return open.videoId;
        }
      }
    }
    return state.selectedVideoId || null;
  }

  /** @param {any} image */
  function baseRevision(image) {
    if (typeof image.persisted_revision === "number" && Number.isFinite(image.persisted_revision)) {
      return image.persisted_revision;
    }
    if (image.review && typeof image.review.revision === "number" && Number.isFinite(image.review.revision)) {
      return image.review.revision;
    }
    return 0;
  }

  /** @param {unknown} err */
  function errorMessage(err) {
    if (err && typeof err === "object" && "name" in err && err.name === "AbortError") {
      return null;
    }
    if (err instanceof Error) return err.message;
    return "Request failed.";
  }

  /**
   * @param {any} body
   * @param {number} status
   */
  function detailFromBody(body, status) {
    let detail = `HTTP ${status}`;
    if (body && typeof body === "object" && body.detail) {
      if (typeof body.detail === "string") detail = body.detail;
      else if (body.detail.message) detail = String(body.detail.message);
    }
    return detail;
  }

  /**
   * @param {string} path
   * @param {AbortSignal} [signal]
   */
  async function apiGet(path, signal) {
    const response = await fetch(path, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal,
      credentials: "same-origin",
    });
    if (!response.ok) {
      let body = null;
      try {
        body = await response.json();
      } catch {
        /* keep status text */
      }
      const err = new Error(detailFromBody(body, response.status));
      /** @type {any} */ (err).status = response.status;
      /** @type {any} */ (err).body = body;
      throw err;
    }
    return response.json();
  }

  /**
   * @param {string} path
   * @param {object} payload
   * @param {AbortSignal} [signal]
   */
  async function apiPutJson(path, payload, signal) {
    const response = await fetch(path, {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        Origin: window.location.origin,
      },
      credentials: "same-origin",
      body: JSON.stringify(payload),
      signal,
    });
    let body = null;
    try {
      body = await response.json();
    } catch {
      body = null;
    }
    if (!response.ok) {
      const err = new Error(detailFromBody(body, response.status));
      /** @type {any} */ (err).status = response.status;
      /** @type {any} */ (err).body = body;
      throw err;
    }
    return body;
  }

  /** @param {ParentNode} parent */
  function clearChildren(parent) {
    while (parent.firstChild) parent.removeChild(parent.firstChild);
  }

  /**
   * @param {string} tag
   * @param {Record<string, string|boolean|null|undefined>} [attrs]
   * @param {(Node|string)[]} [children]
   */
  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const [key, value] of Object.entries(attrs)) {
        if (value === null || value === undefined || value === false) continue;
        if (key === "className") node.className = String(value);
        else if (key === "text") node.textContent = String(value);
        else if (value === true) node.setAttribute(key, "");
        else node.setAttribute(key, String(value));
      }
    }
    if (children) {
      for (const child of children) {
        if (typeof child === "string") node.appendChild(document.createTextNode(child));
        else if (child) node.appendChild(child);
      }
    }
    return node;
  }

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  const state = {
    selectionGen: 0,
    /** @type {AbortController | null} */
    loadAbort: null,
    /** @type {any[]} */
    datasets: [],
    /** @type {string | null} datasetKey */
    selectedDatasetKey: null,
    /** @type {any | null} full effective image list (image browse mode only) */
    datasetDetail: null,
    /** @type {any | null} lightweight browse header (always set when a dataset is loaded) */
    browseMeta: null,
    /** @type {"interval"|"image"|null} */
    browseMode: null,
    /** @type {"legacy"|"video_catalog"|null} */
    datasetLayout: null,
    /** @type {string | null} currently opened video (video_catalog layout) */
    selectedVideoId: null,
    /** @type {any[]} */
    runs: [],
    /** @type {string | null} */
    selectedRunId: null,
    /** @type {any | null} */
    runDetail: null,
    /** @type {any | null} run overview without per-image rows (interval mode) */
    runOverview: null,
    /** @type {any | null} */
    summary: null,
    /** Explicit summary scan has been loaded for the current dataset/run context */
    summaryLoaded: false,
    /** Loaded summary may be stale after comment Saves */
    summaryStale: false,
    summaryLoading: false,
    /** @type {string | null} last explicit summary load error (shown in-panel) */
    summaryError: null,
    /** @type {Array<{ video_id: string, video_name: string }> | null} CSV video rows for picker */
    videoCatalogList: null,
    /** When true, picker shows /intervals/search hits instead of CSV filter results. */
    pickerExplicitImageSearch: false,
    /** @type {string[]} image IDs (image browse mode) */
    openCards: [],
    /**
     * Open interval cards (interval browse mode).
     * @type {Array<{
     *   cardId: string,
     *   segmentId: string,
     *   title: string,
     *   imageCount: number,
     *   videoId: string | null,
     *   frames: any[] | null,
     *   currentIndex: number,
     *   currentImage: any | null,
     *   displayId: string | null,
     *   prediction: any | null,
     *   loadGen: number,
     *   status: "idle"|"loading"|"error",
     *   errorMessage: string | null,
     * }>}
     */
    openIntervals: [],
    /** Monotonic id so remove/reopen cannot accept a prior card's responses. */
    intervalCardSeq: 0,
    /** @type {Map<string, any>} dataset/version/image → EffectiveImageView cache */
    imageCache: new Map(),
    pickerSession: 0,
    pickerRequestId: 0,
    activeBatchId: 0,
    /** @type {Map<string, {comments: string}>} */
    drafts: new Map(),
    /**
     * Per-image Save operation state (pending / conflict / unconfirmed / error).
     * `submittedComments` is the immutable payload of the in-flight/conflicted operation.
     * Latest user draft remains in `drafts` and may diverge during conflict/unconfirmed.
     * @type {Map<string, {
     *   status: "pending"|"conflict"|"unconfirmed"|"error",
     *   submittedComments: string,
     *   expected_revision: number,
     *   datasetId: string,
     *   datasetVersion: string,
     *   imageId: string,
     *   errorMessage: string | null,
     *   serverReview: any | null,
     *   serverPersistedRevision: number | null,
     *   showCompare: boolean,
     *   serverFetchFailed: boolean,
     * }>}
     */
    saves: new Map(),
    /** @type {"analytical"|"summary"|"executive"} */
    activeTab: "analytical",
    loading: false,
    /** @type {string | null} */
    error: null,
    /** @type {string | null} run/dataset-only load failure for the current selection */
    runLoadError: null,
    summarySearch: "",
    /** @type {Set<string>} segment_id or image_id depending on browse mode */
    pickerSelected: new Set(),
    pickerSearch: "",
    pickerOffset: 0,
    /** @type {any | null} */
    pickerResults: null,
    pickerLoading: false,
    /** @type {string | null} */
    pickerError: null,
    /** When image search hits, map segment_id → target image_id */
    /** @type {Map<string, string>} */
    pickerTargetImages: new Map(),
    /** Results are usable only when they match this request id and picker is not loading. */
    pickerResultsRequestId: 0,
    /** @type {HTMLElement | null} */
    lastFocus: null,
    viewer: {
      open: false,
      imageId: null,
      naturalWidth: 0,
      naturalHeight: 0,
      scale: 1,
      fitScale: 1,
      offsetX: 0,
      offsetY: 0,
      panning: false,
      panStartX: 0,
      panStartY: 0,
      originOffsetX: 0,
      originOffsetY: 0,
    },
  };

  // ---------------------------------------------------------------------------
  // DOM refs
  // ---------------------------------------------------------------------------

  const dom = {
    datasetSelect: /** @type {HTMLSelectElement} */ (document.getElementById("dataset-select")),
    runSelect: /** @type {HTMLSelectElement} */ (document.getElementById("run-select")),
    selectionStatus: document.getElementById("selection-status"),
    datasetMeta: document.getElementById("dataset-meta"),
    globalBanner: document.getElementById("global-banner"),
    tabs: Array.from(document.querySelectorAll(".tab")),
    panelAnalytical: document.getElementById("panel-analytical"),
    panelSummary: document.getElementById("panel-summary"),
    panelExecutive: document.getElementById("panel-executive"),
    runInfoPanel: document.getElementById("run-info-panel"),
    addFramesBtn: /** @type {HTMLButtonElement} */ (document.getElementById("add-frames-btn")),
    analyticalHint: document.getElementById("analytical-hint"),
    frameCards: document.getElementById("frame-cards"),
    analyticalEmpty: document.getElementById("analytical-empty"),
    summaryDraftNotice: document.getElementById("summary-draft-notice"),
    executiveDraftNotice: document.getElementById("executive-draft-notice"),
    summaryLoadBar: document.getElementById("summary-load-bar"),
    summaryLoadBtn: /** @type {HTMLButtonElement | null} */ (
      document.getElementById("summary-load-btn")
    ),
    summaryStaleNotice: document.getElementById("summary-stale-notice"),
    summaryToolbar: document.getElementById("summary-toolbar"),
    summarySearch: /** @type {HTMLInputElement} */ (document.getElementById("summary-search")),
    summaryRowCount: document.getElementById("summary-row-count"),
    summaryTableWrap: document.getElementById("summary-table-wrap"),
    executiveLoadBar: document.getElementById("executive-load-bar"),
    executiveLoadBtn: /** @type {HTMLButtonElement | null} */ (
      document.getElementById("executive-load-btn")
    ),
    executiveStaleNotice: document.getElementById("executive-stale-notice"),
    executiveContent: document.getElementById("executive-content"),
    pickerModal: document.getElementById("picker-modal"),
    pickerTitle: document.getElementById("picker-title"),
    pickerSearchLabel: document.getElementById("picker-search-label"),
    pickerSearch: /** @type {HTMLInputElement} */ (document.getElementById("picker-search")),
    pickerSearchBtn: /** @type {HTMLButtonElement | null} */ (
      document.getElementById("picker-search-btn")
    ),
    pickerMatchInfo: document.getElementById("picker-match-info"),
    pickerGrid: document.getElementById("picker-grid"),
    pickerPager: document.getElementById("picker-pager"),
    pickerPrevPage: /** @type {HTMLButtonElement | null} */ (
      document.getElementById("picker-prev-page")
    ),
    pickerNextPage: /** @type {HTMLButtonElement | null} */ (
      document.getElementById("picker-next-page")
    ),
    pickerPageLabel: document.getElementById("picker-page-label"),
    pickerAddAllBtn: /** @type {HTMLButtonElement | null} */ (
      document.getElementById("picker-add-all-btn")
    ),
    pickerAddBtn: /** @type {HTMLButtonElement} */ (document.getElementById("picker-add-btn")),
    pickerSelectionCount: document.getElementById("picker-selection-count"),
    viewerModal: document.getElementById("viewer-modal"),
    viewerTitle: document.getElementById("viewer-title"),
    viewerStage: /** @type {HTMLElement} */ (document.getElementById("viewer-stage")),
    viewerImage: /** @type {HTMLImageElement} */ (document.getElementById("viewer-image")),
    viewerError: document.getElementById("viewer-error"),
    viewerZoomLabel: document.getElementById("viewer-zoom-label"),
    viewerFit: document.getElementById("viewer-fit"),
    viewer100: document.getElementById("viewer-100"),
    viewerZoomIn: document.getElementById("viewer-zoom-in"),
    viewerZoomOut: document.getElementById("viewer-zoom-out"),
    viewerReset: document.getElementById("viewer-reset"),
  };

  // ---------------------------------------------------------------------------
  // Selection / loading
  // ---------------------------------------------------------------------------

  function currentDatasetIdentity() {
    // video_catalog / interval browse keeps datasetDetail null; use browseMeta.
    return videoCatalogSummaryLogic().datasetIdentityFromMeta(
      state.browseMeta,
      state.datasetDetail,
    );
  }

  function isIntervalBrowse() {
    return state.browseMode === "interval";
  }

  function markSummaryStale() {
    if (!state.summaryLoaded || !state.summary) return;
    state.summaryStale = true;
    updateSummaryStaleNotices();
  }

  function updateSummaryStaleNotices() {
    const message = state.summaryStale
      ? "Summary needs refresh — comments or reviews changed since it was loaded. Effective ground-truth counts may be outdated."
      : null;
    for (const node of [dom.summaryStaleNotice, dom.executiveStaleNotice]) {
      if (!node) continue;
      if (!message) {
        node.hidden = true;
        clearChildren(node);
        continue;
      }
      clearChildren(node);
      node.appendChild(document.createTextNode(message));
      const refresh = el("button", {
        type: "button",
        className: "btn btn-secondary btn-sm",
        text: "Refresh summary",
      });
      refresh.addEventListener("click", () => loadSummaryExplicit({ force: true }));
      node.appendChild(refresh);
      node.hidden = false;
    }
  }

  function syncSummaryLoadBars() {
    const ui = {
      browseMode: state.browseMode,
      summaryLoaded: state.summaryLoaded,
    };
    const showLoad = videoCatalogSummaryLogic().shouldShowSummaryLoadBar(ui);
    if (dom.summaryLoadBar) dom.summaryLoadBar.hidden = !showLoad;
    if (dom.executiveLoadBar) dom.executiveLoadBar.hidden = !showLoad;
    if (dom.summaryToolbar) {
      dom.summaryToolbar.hidden = videoCatalogSummaryLogic().shouldHideSummaryToolbar(ui);
    }
    if (dom.summaryLoadBtn) {
      dom.summaryLoadBtn.disabled = state.summaryLoading;
      dom.summaryLoadBtn.textContent = videoCatalogSummaryLogic().summaryLoadButtonLabel(
        state.summaryLoading,
        "effective",
      );
    }
    if (dom.executiveLoadBtn) {
      dom.executiveLoadBtn.disabled = state.summaryLoading;
      dom.executiveLoadBtn.textContent = videoCatalogSummaryLogic().summaryLoadButtonLabel(
        state.summaryLoading,
        "executive",
      );
    }
    updateSummaryStaleNotices();
  }

  function hasAnyDrafts() {
    return state.drafts.size > 0;
  }

  /** @param {string} [prefix] */
  function keysWithPrefix(map, prefix) {
    /** @type {string[]} */
    const keys = [];
    for (const key of map.keys()) {
      if (key.startsWith(prefix)) keys.push(key);
    }
    return keys;
  }

  function draftsForCurrentDataset() {
    const identity = currentDatasetIdentity();
    if (!identity) return [];
    const prefix = `${identity.datasetId}\0${identity.datasetVersion}\0`;
    return keysWithPrefix(state.drafts, prefix);
  }

  function savesForCurrentDataset() {
    const identity = currentDatasetIdentity();
    if (!identity) return [];
    const prefix = `${identity.datasetId}\0${identity.datasetVersion}\0`;
    return keysWithPrefix(state.saves, prefix);
  }

  /** Unresolved Save states that should block leave / dataset switch. */
  function hasUnresolvedSaves(keys) {
    for (const key of keys) {
      const op = state.saves.get(key);
      if (!op) continue;
      if (
        op.status === "pending" ||
        op.status === "unconfirmed" ||
        op.status === "conflict"
      ) {
        return true;
      }
    }
    return false;
  }

  function hasUnresolvedWorkForCurrentDataset() {
    return (
      draftsForCurrentDataset().length > 0 ||
      hasUnresolvedSaves(savesForCurrentDataset())
    );
  }

  function hasAnyUnresolvedWork() {
    if (hasAnyDrafts()) return true;
    return hasUnresolvedSaves(Array.from(state.saves.keys()));
  }

  /** @param {string} imageId */
  function saveOpForImage(imageId) {
    const identity = currentDatasetIdentity();
    if (!identity) return null;
    return state.saves.get(draftKey(identity.datasetId, identity.datasetVersion, imageId)) || null;
  }

  /**
   * @param {string | null} message
   * @param {string} [kind]
   * @param {{ label: string, onClick: () => void } | null} [action]
   */
  function showBanner(message, kind, action) {
    if (!dom.globalBanner) return;
    if (!message) {
      dom.globalBanner.hidden = true;
      clearChildren(dom.globalBanner);
      return;
    }
    clearChildren(dom.globalBanner);
    const text = el("span");
    text.appendChild(document.createTextNode(message));
    dom.globalBanner.appendChild(text);
    if (action) {
      const retry = el("button", {
        type: "button",
        className: "btn btn-secondary retry-btn",
        text: action.label,
      });
      retry.addEventListener("click", () => action.onClick());
      dom.globalBanner.appendChild(retry);
    }
    dom.globalBanner.dataset.kind = kind || "info";
    dom.globalBanner.hidden = false;
  }

  function renderSelectionBanner() {
    if (state.runLoadError) {
      const target = state.selectedRunId
        ? `run ${state.selectedRunId}`
        : "dataset-only summary";
      showBanner(`Failed to load ${target}: ${state.runLoadError}`, "error", {
        label: "Retry",
        onClick: () => {
          selectRun(state.selectedRunId, { force: true });
        },
      });
      return;
    }
    if (state.error) {
      showBanner(state.error, "error");
      return;
    }
    showBanner(null);
  }

  function setSelectionStatus(text) {
    if (dom.selectionStatus) {
      clearChildren(dom.selectionStatus);
      if (text) dom.selectionStatus.appendChild(document.createTextNode(text));
    }
  }

  function bumpSelectionGen() {
    state.selectionGen += 1;
    if (state.loadAbort) state.loadAbort.abort();
    state.loadAbort = new AbortController();
    return { gen: state.selectionGen, signal: state.loadAbort.signal };
  }

  async function bootstrap() {
    setSelectionStatus("Loading datasets…");
    showBanner(null);
    try {
      const data = await apiGet("/api/datasets");
      state.datasets = Array.isArray(data.datasets) ? data.datasets : [];
      populateDatasetSelect();
      if (state.datasets.length === 0) {
        setSelectionStatus("No published datasets.");
        showBanner("No published datasets are available.", "warning");
        return;
      }
      const first = state.datasets[0];
      await selectDataset(datasetKey(first.dataset_id, first.dataset_version), {
        force: true,
      });
    } catch (err) {
      const msg = errorMessage(err) || "Failed to load datasets.";
      showBanner(msg, "error");
      setSelectionStatus("Failed to load datasets.");
      clearChildren(dom.datasetSelect);
      const opt = el("option", { value: "", text: "Retry needed" });
      dom.datasetSelect.appendChild(opt);
      dom.datasetSelect.disabled = true;
      const retry = el("button", {
        type: "button",
        className: "btn btn-secondary retry-btn",
        text: "Retry",
      });
      retry.addEventListener("click", () => {
        bootstrap();
      });
      if (dom.globalBanner) dom.globalBanner.appendChild(retry);
    }
  }

  function populateDatasetSelect() {
    clearChildren(dom.datasetSelect);
    for (const item of state.datasets) {
      const value = datasetKey(item.dataset_id, item.dataset_version);
      const label = `${item.display_name} (${item.dataset_id} / ${item.dataset_version})`;
      const opt = el("option", { value, text: label });
      dom.datasetSelect.appendChild(opt);
    }
    dom.datasetSelect.disabled = state.datasets.length === 0;
  }

  function populateRunSelect() {
    clearChildren(dom.runSelect);
    const none = el("option", {
      value: "",
      text: "Dataset only — no run selected",
    });
    dom.runSelect.appendChild(none);
    for (const run of state.runs) {
      const modelBits = [run.model_name, run.model_version].filter(Boolean).join(" ");
      const label = `${run.run_id}${modelBits ? ` — ${modelBits}` : ""}`;
      const opt = el("option", { value: run.run_id, text: label });
      dom.runSelect.appendChild(opt);
    }
    dom.runSelect.value = state.selectedRunId || "";
    dom.runSelect.disabled = !currentDatasetIdentity();
  }

  /**
   * @param {string} key
   * @param {{force?: boolean}} [opts]
   */
  async function selectDataset(key, opts) {
    const force = opts && opts.force;
    if (!force && key === state.selectedDatasetKey) return;

    if (!force && hasUnresolvedWorkForCurrentDataset()) {
      const ok = window.confirm(
        "You have unsaved comments or unresolved Saves for the current dataset. Discard them and switch datasets?",
      );
      if (!ok) {
        if (state.selectedDatasetKey) dom.datasetSelect.value = state.selectedDatasetKey;
        return;
      }
      clearDraftsForCurrentDataset();
    }

    const parts = key.split("\0");
    if (parts.length !== 2) return;
    const [datasetId, datasetVersion] = parts;

    const { gen, signal } = bumpSelectionGen();
    state.selectedDatasetKey = key;
    state.selectedRunId = null;
    state.datasetDetail = null;
    state.browseMeta = null;
    state.browseMode = null;
    state.datasetLayout = null;
    state.selectedVideoId = null;
    state.runDetail = null;
    state.runOverview = null;
    state.summary = null;
    state.summaryLoaded = false;
    state.summaryStale = false;
    state.summaryLoading = false;
    state.summaryError = null;
    state.videoCatalogList = null;
    state.pickerExplicitImageSearch = false;
    state.runs = [];
    state.openCards = [];
    state.openIntervals = [];
    state.intervalCardSeq = 0;
    state.imageCache = new Map();
    state.activeBatchId += 1;
    state.pickerSession += 1;
    state.pickerRequestId += 1;
    state.pickerResults = null;
    state.pickerResultsRequestId = 0;
    state.pickerLoading = false;
    state.pickerError = null;
    state.pickerSelected = new Set();
    state.error = null;
    state.runLoadError = null;
    state.loading = true;
    dom.datasetSelect.value = key;
    setSelectionStatus("Loading dataset…");
    renderAll();

    try {
      const [browse, runsView] = await Promise.all([
        apiGet(
          `/api/datasets/${encodeURIComponent(datasetId)}/versions/${encodeURIComponent(datasetVersion)}/browse`,
          signal,
        ),
        apiGet(
          `/api/runs?dataset_id=${encodeURIComponent(datasetId)}&dataset_version=${encodeURIComponent(datasetVersion)}`,
          signal,
        ),
      ]);
      if (gen !== state.selectionGen) return;

      state.browseMeta = browse;
      state.browseMode = browse.browse_mode === "interval" ? "interval" : "image";
      state.datasetLayout =
        browse.dataset_layout === "video_catalog" ? "video_catalog" : "legacy";
      state.runs = Array.isArray(runsView.runs) ? runsView.runs : [];

      if (state.browseMode === "interval") {
        // Interval datasets: do not scan all reviews or ship every image record.
        state.datasetDetail = null;
        state.summary = null;
        state.summaryLoaded = false;
        state.openIntervals = [];
        state.openCards = [];
        state.selectedVideoId = null;
        if (dom.addFramesBtn) {
          clearChildren(dom.addFramesBtn);
          const btnLabel =
            state.datasetLayout === "video_catalog" ? "+ Open video" : "+ Add intervals";
          dom.addFramesBtn.appendChild(document.createTextNode(btnLabel));
          dom.addFramesBtn.disabled = false;
        }
        state.loading = false;
        if (state.datasetLayout === "video_catalog") {
          const videoCount =
            typeof browse.video_count === "number" ? browse.video_count : 0;
          setSelectionStatus(
            state.runs.length === 0
              ? `Video catalog loaded · ${videoCount} active video(s) (no published runs). Open a video to load its intervals.`
              : `Video catalog loaded · ${videoCount} active video(s) · ${state.runs.length} run(s). Open a video to load its intervals.`,
          );
        } else {
          setSelectionStatus(
            state.runs.length === 0
              ? `Interval dataset loaded · ${browse.interval_count} interval(s), ${browse.image_count} image(s) (no published runs).`
              : `Interval dataset loaded · ${browse.interval_count} interval(s), ${browse.image_count} image(s) · ${state.runs.length} run(s).`,
          );
        }
        populateRunSelect();
        renderAll();
        return;
      }

      const [detail, summary] = await Promise.all([
        apiGet(
          `/api/datasets/${encodeURIComponent(datasetId)}/versions/${encodeURIComponent(datasetVersion)}`,
          signal,
        ),
        apiGet(
          `/api/datasets/${encodeURIComponent(datasetId)}/versions/${encodeURIComponent(datasetVersion)}/summary`,
          signal,
        ),
      ]);
      if (gen !== state.selectionGen) return;

      state.datasetDetail = detail;
      state.summary = summary;
      state.summaryLoaded = true;
      state.summaryStale = false;
      state.openCards = [];
      if (Array.isArray(detail.images) && detail.images.length > 0) {
        state.openCards.push(detail.images[0].image_id);
      }
      if (dom.addFramesBtn) {
        clearChildren(dom.addFramesBtn);
        dom.addFramesBtn.appendChild(document.createTextNode("+ Add frames"));
        dom.addFramesBtn.disabled = false;
      }
      state.loading = false;
      setSelectionStatus(
        state.runs.length === 0
          ? "Dataset loaded (no published runs)."
          : `Dataset loaded · ${state.runs.length} run(s).`,
      );
      populateRunSelect();
      renderAll();
    } catch (err) {
      if (gen !== state.selectionGen) return;
      state.loading = false;
      const msg = errorMessage(err);
      if (!msg) return;
      state.error = msg;
      showBanner(msg, "error");
      setSelectionStatus("Failed to load dataset.");
      renderAll();
    }
  }

  /**
   * Load run detail + summary (or dataset-only summary) for the current dataset.
   * Preserves dataset detail, open cards, and drafts. Clears prior run predictions
   * and summary/metrics immediately so stale values cannot remain on screen.
   *
   * Interval browse mode loads run overview only (no full-image review scan) and
   * leaves the effective summary for an explicit Load action.
   *
   * @param {string | null} runId
   * @param {{ force?: boolean }} [options]
   */
  async function selectRun(runId, options) {
    const force = Boolean(options && options.force);
    if (
      !force &&
      runId === state.selectedRunId &&
      !state.runLoadError &&
      !state.loading
    ) {
      return;
    }
    const identity = currentDatasetIdentity();
    if (!identity) return;

    const { gen, signal } = bumpSelectionGen();
    state.selectedRunId = runId;
    // Drop previous run-scoped data immediately (including historical metrics).
    state.runDetail = null;
    state.runOverview = null;
    state.summary = null;
    state.summaryLoaded = false;
    state.summaryStale = false;
    state.error = null;
    state.runLoadError = null;
    state.loading = true;
    populateRunSelect();
    setSelectionStatus(
      runId
        ? `Loading run ${runId}…`
        : isIntervalBrowse()
          ? "Dataset only — no run selected"
          : "Loading dataset summary…",
    );
    refreshRunDependentViews();

    try {
      if (isIntervalBrowse()) {
        /** @type {any | null} */
        let overview = null;
        if (runId) {
          overview = await apiGet(`/api/runs/${encodeURIComponent(runId)}/overview`, signal);
          if (gen !== state.selectionGen) return;
        }
        state.runOverview = overview;
        state.runDetail = null;
        state.summary = null;
        state.summaryLoaded = false;
        state.loading = false;
        state.runLoadError = null;
        setSelectionStatus(
          runId ? `Run selected: ${runId}` : "Dataset only — no run selected",
        );
        // Reload predictions for currently open interval frames only (targeted; keep textareas).
        for (const card of state.openIntervals) {
          void loadIntervalFrame(card.segmentId, card.currentIndex, {
            predictionRefresh: true,
          });
        }
        refreshRunDependentViews();
        renderSelectionBanner();
        return;
      }

      let summaryPath =
        `/api/datasets/${encodeURIComponent(identity.datasetId)}` +
        `/versions/${encodeURIComponent(identity.datasetVersion)}/summary`;
      /** @type {any | null} */
      let runDetail = null;
      /** @type {any} */
      let summary;

      if (runId) {
        summaryPath += `?run_id=${encodeURIComponent(runId)}`;
        // Commit only after both requests succeed for this generation.
        const results = await Promise.all([
          apiGet(`/api/runs/${encodeURIComponent(runId)}`, signal),
          apiGet(summaryPath, signal),
        ]);
        if (gen !== state.selectionGen) return;
        runDetail = results[0];
        summary = results[1];
      } else {
        summary = await apiGet(summaryPath, signal);
        if (gen !== state.selectionGen) return;
        runDetail = null;
      }

      state.runDetail = runDetail;
      state.runOverview = null;
      state.summary = summary;
      state.summaryLoaded = true;
      state.summaryStale = false;
      state.loading = false;
      state.runLoadError = null;
      setSelectionStatus(
        runId ? `Run selected: ${runId}` : "Dataset only — no run selected",
      );
      refreshRunDependentViews();
      renderSelectionBanner();
    } catch (err) {
      if (gen !== state.selectionGen) return;
      state.loading = false;
      state.runDetail = null;
      state.runOverview = null;
      state.summary = null;
      state.summaryLoaded = false;
      const msg = errorMessage(err);
      if (!msg) return;
      state.runLoadError = msg;
      setSelectionStatus(
        runId ? "Failed to load run." : "Failed to load dataset-only summary.",
      );
      refreshRunDependentViews();
      renderSelectionBanner();
    }
  }

  /**
   * Explicit effective-summary scan (required for interval browse; optional refresh).
   * @param {{ force?: boolean }} [options]
   */
  async function loadSummaryExplicit(options) {
    const force = Boolean(options && options.force);
    const identity = currentDatasetIdentity();
    if (!identity) {
      state.summaryError =
        "No dataset is selected. Choose a dataset, then load the summary again.";
      state.summaryLoading = false;
      syncSummaryLoadBars();
      showBanner(state.summaryError, "error");
      renderSummary();
      renderExecutive();
      return;
    }
    if (state.summaryLoaded && !state.summaryStale && !force) return;
    const gen = state.selectionGen;
    const runId = state.selectedRunId;
    state.summaryLoading = true;
    state.summaryError = null;
    syncSummaryLoadBars();
    renderSummary();
    renderExecutive();
    try {
      const path = videoCatalogSummaryLogic().summaryApiPath(
        identity.datasetId,
        identity.datasetVersion,
        runId,
      );
      const summary = await apiGet(path);
      if (gen !== state.selectionGen) return;
      const current = currentDatasetIdentity();
      if (
        !current ||
        current.datasetId !== identity.datasetId ||
        current.datasetVersion !== identity.datasetVersion
      ) {
        return;
      }
      if ((state.selectedRunId || null) !== (runId || null)) return;
      state.summary = summary;
      state.summaryLoaded = true;
      state.summaryStale = false;
      state.summaryError = null;
      state.summaryLoading = false;
      syncSummaryLoadBars();
      renderSummary();
      renderExecutive();
    } catch (err) {
      if (gen !== state.selectionGen) return;
      state.summaryLoading = false;
      state.summaryError = errorMessage(err) || "Failed to load summary.";
      syncSummaryLoadBars();
      showBanner(state.summaryError, "error");
      renderSummary();
      renderExecutive();
    }
  }

  /** Refresh run-scoped UI without rebuilding frame cards (preserves drafts/caret). */
  function refreshRunDependentViews() {
    renderRunInfo();
    renderCardsPredictionsOnly();
    updateDraftNotices();
    renderSummary();
    renderExecutive();
    renderSelectionBanner();
    const canAdd = Boolean(currentDatasetIdentity()) && !state.loading;
    dom.addFramesBtn.disabled = !canAdd;
    syncSummaryLoadBars();
  }

  function clearDraftsForCurrentDataset() {
    for (const key of draftsForCurrentDataset()) state.drafts.delete(key);
    for (const key of savesForCurrentDataset()) state.saves.delete(key);
  }

  // ---------------------------------------------------------------------------
  // Image / prediction lookups
  // ---------------------------------------------------------------------------

  /** @returns {typeof globalThis.CvsIntervalBrowseLogic} */
  function intervalLogic() {
    const logic = globalThis.CvsIntervalBrowseLogic;
    if (!logic) {
      throw new Error("Interval browse logic module failed to load.");
    }
    return logic;
  }

  /** @param {string} imageId */
  function findImage(imageId) {
    const identity = currentDatasetIdentity();
    if (identity) {
      const key = intervalLogic().imageCacheKey(
        identity.datasetId,
        identity.datasetVersion,
        imageId,
      );
      const cached = state.imageCache.get(key);
      if (cached) return cached;
    }
    if (!state.datasetDetail || !Array.isArray(state.datasetDetail.images)) return null;
    return state.datasetDetail.images.find((img) => img.image_id === imageId) || null;
  }

  /**
   * @param {string} datasetId
   * @param {string} datasetVersion
   * @param {string} imageId
   * @param {any} image
   */
  function cacheImageForIdentity(datasetId, datasetVersion, imageId, image) {
    const key = intervalLogic().imageCacheKey(datasetId, datasetVersion, imageId);
    state.imageCache.set(key, image);
    if (
      state.datasetDetail &&
      state.datasetDetail.dataset_id === datasetId &&
      state.datasetDetail.dataset_version === datasetVersion &&
      Array.isArray(state.datasetDetail.images)
    ) {
      const idx = state.datasetDetail.images.findIndex((img) => img.image_id === imageId);
      if (idx >= 0) state.datasetDetail.images[idx] = image;
    }
  }

  /** @param {string} imageId @param {any} image */
  function cacheImage(imageId, image) {
    const identity = currentDatasetIdentity();
    if (!identity) return;
    cacheImageForIdentity(identity.datasetId, identity.datasetVersion, imageId, image);
  }

  /** @param {string} imageId */
  function findPrediction(imageId) {
    if (isIntervalBrowse()) {
      const card = state.openIntervals.find(
        (item) => item.currentImage && item.currentImage.image_id === imageId,
      );
      if (card && card.prediction) return card.prediction;
      return null;
    }
    if (!state.runDetail || !Array.isArray(state.runDetail.images)) return null;
    const row = state.runDetail.images.find((item) => item.image && item.image.image_id === imageId);
    return row ? row.prediction : null;
  }

  /** @param {string} segmentId */
  function findOpenInterval(segmentId) {
    return state.openIntervals.find((item) => item.segmentId === segmentId) || null;
  }

  /** @param {string} cardId */
  function findOpenIntervalByCardId(cardId) {
    return state.openIntervals.find((item) => item.cardId === cardId) || null;
  }

  /**
   * @param {{ segmentId: string, title: string, imageCount: number, videoId?: string | null }} args
   */
  function createOpenIntervalCard(args) {
    state.intervalCardSeq += 1;
    return {
      cardId: `card-${state.intervalCardSeq}`,
      segmentId: args.segmentId,
      title: args.title,
      imageCount: args.imageCount,
      videoId: args.videoId || null,
      frames: null,
      currentIndex: 0,
      currentImage: null,
      displayId: null,
      prediction: null,
      loadGen: 0,
      status: "loading",
      errorMessage: null,
    };
  }

  /** @param {any} image */
  function persistedComments(image) {
    return image.effective_comments == null ? "" : String(image.effective_comments);
  }

  /** @param {any} image */
  function effectiveDraft(image) {
    const identity = currentDatasetIdentity();
    const persisted = persistedComments(image);
    if (!identity) return { comments: persisted, dirty: false };
    const key = draftKey(identity.datasetId, identity.datasetVersion, image.image_id);
    const draft = state.drafts.get(key);
    if (!draft) return { comments: persisted, dirty: false };
    return {
      comments: draft.comments,
      dirty: true,
    };
  }

  /**
   * @param {any} image
   * @param {string} comments
   */
  function setCommentDraft(image, comments) {
    const identity = currentDatasetIdentity();
    if (!identity) return;
    const op = saveOpForImage(image.image_id);
    if (op && (op.status === "pending" || op.status === "unconfirmed")) return;
    const key = draftKey(identity.datasetId, identity.datasetVersion, image.image_id);
    if (comments === persistedComments(image)) {
      state.drafts.delete(key);
    } else {
      state.drafts.set(key, { comments });
    }
    updateDraftNotices();
    // In-place chrome only — never rebuild/replace the textarea while typing.
    updateCardDraftChromeInPlace(image.image_id);
  }

  /** @param {string} imageId */
  function discardDraft(imageId) {
    const identity = currentDatasetIdentity();
    if (!identity) return;
    const key = draftKey(identity.datasetId, identity.datasetVersion, imageId);
    const op = state.saves.get(key);
    if (op && op.status === "pending") {
      window.alert("A Save is still in progress. Wait for it to finish.");
      return;
    }
    if (op && op.status === "unconfirmed") {
      window.alert(
        "Save could not be confirmed. Discarding clears the local draft display only; it does not prove the Save failed or succeeded. Refresh the server comment to compare first if needed.",
      );
    }
    state.drafts.delete(key);
    if (op && op.status !== "pending") {
      state.saves.delete(key);
    }
    const card = dom.frameCards && dom.frameCards.querySelector(`[data-image-id="${cssEscape(imageId)}"]`);
    if (card) {
      const image = findImage(imageId);
      if (image) refreshCardFields(/** @type {HTMLElement} */ (card), image);
    }
    updateDraftNotices();
  }

  /** @param {any} image */
  function cardBannerText(image) {
    const op = saveOpForImage(image.image_id);
    if (!op) {
      return effectiveDraft(image).dirty ? BANNER_UNSAVED : null;
    }
    if (op.status === "pending") return BANNER_PENDING;
    if (op.status === "unconfirmed") return BANNER_UNCONFIRMED;
    if (op.status === "conflict") return BANNER_CONFLICT;
    if (op.status === "error") return op.errorMessage || "Save failed.";
    return effectiveDraft(image).dirty ? BANNER_UNSAVED : null;
  }

  /** @param {string} imageId */
  function commentsLocked(imageId) {
    const op = saveOpForImage(imageId);
    return Boolean(op && op.status === "pending");
  }

  /** @param {string} imageId */
  function saveBlockedByConflict(imageId) {
    const op = saveOpForImage(imageId);
    return Boolean(op && (op.status === "conflict" || op.status === "unconfirmed"));
  }

  /**
   * Apply a review only when dataset/version/image still match.
   * Run selection changes must not block applying a completed Save.
   * Never replace newer persisted state with a lower revision.
   * @param {{
   *   datasetId: string,
   *   datasetVersion: string,
   *   imageId: string,
   *   review: any,
   *   persistedRevision: number,
   * }} args
   */
  function applyPersistedReviewToImage(args) {
    const identity = currentDatasetIdentity();
    if (!identity) return false;
    if (
      identity.datasetId !== args.datasetId ||
      identity.datasetVersion !== args.datasetVersion
    ) {
      return false;
    }
    const image = findImage(args.imageId);
    if (!image || !args.review) return false;
    const currentRev =
      typeof image.persisted_revision === "number" && Number.isFinite(image.persisted_revision)
        ? image.persisted_revision
        : 0;
    if (args.persistedRevision < currentRev) return false;
    image.review = args.review;
    image.persisted_revision = args.persistedRevision;
    if (args.review.comments !== undefined && args.review.comments !== null) {
      image.effective_comments = args.review.comments;
    } else {
      image.effective_comments = image.original_comments;
    }
    cacheImage(args.imageId, image);
    markSummaryStale();
    return true;
  }

  /** @returns {typeof globalThis.CvsReviewSaveLogic} */
  function saveLogic() {
    const logic = globalThis.CvsReviewSaveLogic;
    if (!logic) {
      throw new Error("Review Save logic module failed to load.");
    }
    return logic;
  }

  /** Shared deps for production Save logic (also used by refresh helpers). */
  function saveDeps() {
    return {
      saves: state.saves,
      drafts: state.drafts,
      currentIdentity: currentDatasetIdentity,
      draftKey,
      findImage,
      effectiveDraft,
      baseRevision,
      putReview: apiPutJson,
      getReview: apiGet,
      reviewUrl: (datasetId, version, imageId) =>
        reviewUrl(datasetId, version, imageId, videoIdForImage(imageId)),
      errorMessage,
      applyPersistedReview: applyPersistedReviewToImage,
      refreshSummary: async (token) => {
        if (isIntervalBrowse()) {
          // Avoid a full-dataset review scan on every Save in interval mode.
          markSummaryStale();
          return;
        }
        await refreshSummaryQuiet({
          datasetId: token.datasetId,
          datasetVersion: token.datasetVersion,
          runId: state.selectedRunId,
          selectionGen: state.selectionGen,
        });
      },
      onOpChanged: (id) => {
        refreshCardFieldsAfterSave(id);
        updateDraftNotices();
        updateCardDraftChromeInPlace(id);
      },
      maxCommentLength: MAX_COMMENT_LENGTH,
    };
  }

  /** @param {string} imageId */
  async function saveComment(imageId) {
    const logic = saveLogic();
    await logic.executeSaveComment(saveDeps(), imageId);
  }

  /** @param {string} imageId */
  async function refreshUnconfirmedServerReview(imageId) {
    const logic = saveLogic();
    await logic.refreshServerReview(saveDeps(), imageId);
  }

  /**
   * Summary refresh uses the current run context. Stale protection is against the
   * generation/run captured for this quiet refresh — not the Save-start generation.
   * @param {{ datasetId: string, datasetVersion: string, imageId?: string, selectionGen: number, runId?: string | null }} token
   */
  async function refreshSummaryQuiet(token) {
    const runId = token.runId !== undefined ? token.runId : state.selectedRunId;
    const gen = token.selectionGen;
    try {
      const path =
        `/api/datasets/${encodeURIComponent(token.datasetId)}` +
        `/versions/${encodeURIComponent(token.datasetVersion)}/summary` +
        (runId ? `?run_id=${encodeURIComponent(runId)}` : "");
      const summary = await apiGet(path);
      const identity = currentDatasetIdentity();
      if (!identity) return;
      if (state.selectionGen !== gen) return;
      if (
        identity.datasetId !== token.datasetId ||
        identity.datasetVersion !== token.datasetVersion
      ) {
        return;
      }
      if ((state.selectedRunId || null) !== (runId || null)) return;
      state.summary = summary;
      state.summaryLoaded = true;
      state.summaryStale = false;
      syncSummaryLoadBars();
      renderSummary();
      renderExecutive();
    } catch {
      /* Save already succeeded; summary refresh can retry via selection */
    }
  }

  /** @param {string} imageId */
  function refreshCardFieldsAfterSave(imageId) {
    if (!dom.frameCards) return;
    const image = findImage(imageId);
    if (!image) return;
    if (isIntervalBrowse()) {
      const open = state.openIntervals.find(
        (item) => item.currentImage && item.currentImage.image_id === imageId,
      );
      if (!open) return; // Navigated away — do not move the card back.
      open.currentImage = image;
      updateIntervalCardDom(open);
      return;
    }
    const card = /** @type {HTMLElement | null} */ (
      dom.frameCards.querySelector(`[data-image-id="${cssEscape(imageId)}"]`)
    );
    if (!card) return;
    refreshCardFields(card, image);
  }

  /** @param {string} imageId */
  function resolveConflictKeepDraft(imageId) {
    const identity = currentDatasetIdentity();
    if (!identity) return;
    const key = draftKey(identity.datasetId, identity.datasetVersion, imageId);
    const op = state.saves.get(key);
    if (!op || (op.status !== "conflict" && op.status !== "unconfirmed")) return;
    const draft = state.drafts.get(key);
    const latest = draft ? draft.comments : op.submittedComments;
    state.drafts.set(key, { comments: latest });
    state.saves.delete(key);
    refreshCardFieldsAfterSave(imageId);
    updateDraftNotices();
  }

  /** @param {string} imageId */
  async function retryConflictServerFetch(imageId) {
    await refreshUnconfirmedServerReview(imageId);
  }

  /** @param {string} value */
  function cssEscape(value) {
    if (window.CSS && typeof window.CSS.escape === "function") return window.CSS.escape(value);
    return value.replace(/["\\]/g, "\\$&");
  }

  // ---------------------------------------------------------------------------
  // Tabs
  // ---------------------------------------------------------------------------

  /** @param {"analytical"|"summary"|"executive"} tab */
  function setActiveTab(tab) {
    state.activeTab = tab;
    for (const button of dom.tabs) {
      const name = button.getAttribute("data-tab");
      const selected = name === tab;
      button.classList.toggle("active", selected);
      button.setAttribute("aria-selected", selected ? "true" : "false");
      button.tabIndex = selected ? 0 : -1;
    }
    const panels = {
      analytical: dom.panelAnalytical,
      summary: dom.panelSummary,
      executive: dom.panelExecutive,
    };
    for (const [name, panel] of Object.entries(panels)) {
      if (!panel) continue;
      const active = name === tab;
      panel.classList.toggle("active", active);
      panel.hidden = !active;
    }
    if (tab === "summary") renderSummary();
    if (tab === "executive") renderExecutive();
  }

  // ---------------------------------------------------------------------------
  // Render orchestrators
  // ---------------------------------------------------------------------------

  function renderAll() {
    updateDatasetMeta();
    populateRunSelect();
    renderRunInfo();
    renderAnalytical();
    updateDraftNotices();
    renderSummary();
    renderExecutive();
    renderSelectionBanner();
    dom.addFramesBtn.disabled = !currentDatasetIdentity() || state.loading;
    syncSummaryLoadBars();
  }

  function updateDatasetMeta() {
    if (!dom.datasetMeta) return;
    clearChildren(dom.datasetMeta);
    const d = state.browseMeta || state.datasetDetail;
    if (!d) {
      if (state.loading) {
        dom.datasetMeta.appendChild(document.createTextNode("Loading…"));
      }
      return;
    }
    const imageCount =
      typeof d.image_count === "number"
        ? d.image_count
        : Array.isArray(state.datasetDetail && state.datasetDetail.images)
          ? state.datasetDetail.images.length
          : null;
    const parts = [`${d.display_name}`, `${d.dataset_id} / ${d.dataset_version}`];
    if (typeof d.video_count === "number") {
      parts.push(`${d.video_count} active video(s)`);
    }
    if (typeof imageCount === "number") {
      parts.push(`${imageCount} image(s)`);
    }
    if (isIntervalBrowse() && typeof d.interval_count === "number") {
      parts.push(`${d.interval_count} interval(s)`);
    }
    if (d.description) parts.push(d.description);
    dom.datasetMeta.appendChild(document.createTextNode(parts.join(" · ")));
  }

  function updateDraftNotices() {
    const hasDrafts = draftsForCurrentDataset().length > 0;
    const message =
      "Summary and Executive Summary show persisted API values and exclude unsaved comment drafts.";
    for (const node of [dom.summaryDraftNotice, dom.executiveDraftNotice]) {
      if (!node) continue;
      clearChildren(node);
      if (hasDrafts) {
        node.appendChild(document.createTextNode(message));
        node.dataset.kind = "warning";
        node.hidden = false;
      } else {
        node.hidden = true;
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Run info panel
  // ---------------------------------------------------------------------------

  function renderRunInfo() {
    const panel = dom.runInfoPanel;
    if (!panel) return;
    clearChildren(panel);
    if (!state.selectedRunId) {
      panel.hidden = true;
      return;
    }
    if (state.loading) {
      panel.hidden = false;
      panel.appendChild(el("p", { className: "muted", text: "Loading run details…" }));
      return;
    }
    const run = isIntervalBrowse() ? state.runOverview : state.runDetail;
    if (state.runLoadError || !run) {
      panel.hidden = false;
      panel.appendChild(
        el("p", {
          className: "muted",
          text: state.runLoadError
            ? `Run details unavailable: ${state.runLoadError}`
            : "Run details unavailable.",
        }),
      );
      return;
    }

    panel.hidden = false;
    const grid = el("div", { className: "run-info-grid" });

    /** @type {[string, string][]} */
    const items = [
      ["Run ID", run.run_id],
      [
        "Model",
        [run.model && run.model.model_name, run.model && run.model.model_version]
          .filter(Boolean)
          .join(" "),
      ],
      ["Model ID", (run.model && run.model.model_id) || "—"],
      ["Executed at", run.executed_at || "—"],
      ["Execution", run.execution_description || "—"],
      ["Model description", (run.model && run.model.description) || "—"],
    ];
    for (const [label, value] of items) {
      const item = el("div", { className: "run-info-item" });
      item.appendChild(el("dt", { text: label }));
      item.appendChild(el("dd", { text: value || "—" }));
      grid.appendChild(item);
    }
    panel.appendChild(grid);

    const details = el("details", { className: "meta-details" });
    details.appendChild(el("summary", { text: "Model parameters & preprocessing (JSON)" }));
    const pre = el("pre", { className: "meta-json" });
    pre.textContent = JSON.stringify(
      {
        model_parameters: run.model_parameters || {},
        preprocessing: run.preprocessing || {},
      },
      null,
      2,
    );
    details.appendChild(pre);
    panel.appendChild(details);
  }

  // ---------------------------------------------------------------------------
  // Analytical cards
  // ---------------------------------------------------------------------------

  function renderAnalytical() {
    const cardsRoot = dom.frameCards;
    const empty = dom.analyticalEmpty;
    if (!cardsRoot || !empty) return;
    clearChildren(cardsRoot);
    clearChildren(empty);
    empty.hidden = true;

    if (!currentDatasetIdentity()) {
      if (state.loading) {
        empty.hidden = false;
        empty.appendChild(el("p", { text: "Loading dataset…" }));
      } else if (state.error) {
        empty.hidden = false;
        empty.appendChild(el("p", { text: state.error }));
        const retry = el("button", {
          type: "button",
          className: "btn btn-secondary retry-btn",
          text: "Retry",
        });
        retry.addEventListener("click", () => {
          if (state.selectedDatasetKey) selectDataset(state.selectedDatasetKey, { force: true });
          else bootstrap();
        });
        empty.appendChild(retry);
      }
      if (dom.analyticalHint) {
        clearChildren(dom.analyticalHint);
      }
      return;
    }

    if (isIntervalBrowse()) {
      renderAnalyticalIntervals(cardsRoot, empty);
      return;
    }

    if (!state.datasetDetail) {
      empty.hidden = false;
      empty.appendChild(el("p", { text: "Dataset detail is unavailable." }));
      return;
    }

    const images = Array.isArray(state.datasetDetail.images) ? state.datasetDetail.images : [];
    if (images.length === 0) {
      empty.hidden = false;
      empty.appendChild(el("p", { text: "This dataset version has no images." }));
      if (dom.analyticalHint) {
        clearChildren(dom.analyticalHint);
        dom.analyticalHint.appendChild(
          document.createTextNode("Use catalog publication to add images later."),
        );
      }
      return;
    }

    if (state.openCards.length === 0) {
      empty.hidden = false;
      empty.appendChild(el("p", { text: "No frames open in this view." }));
      empty.appendChild(
        el("p", {
          text: "Use “+ Add frames” to open image cards. Removing a card only hides it from this view.",
        }),
      );
    }

    if (dom.analyticalHint) {
      clearChildren(dom.analyticalHint);
      const hint = state.selectedRunId
        ? `Showing predictions for run ${state.selectedRunId}. Reviews are independent of run selection.`
        : "Dataset-only view — predictions are hidden until a run is selected.";
      dom.analyticalHint.appendChild(document.createTextNode(hint));
    }

    for (const imageId of state.openCards) {
      const image = findImage(imageId);
      if (!image) continue;
      cardsRoot.appendChild(buildFrameCard(image));
    }
  }

  /**
   * @param {HTMLElement} cardsRoot
   * @param {HTMLElement} empty
   */
  function renderAnalyticalIntervals(cardsRoot, empty) {
    if (state.openIntervals.length === 0) {
      empty.hidden = false;
      empty.appendChild(el("p", { text: "No intervals open in this view." }));
      empty.appendChild(
        el("p", {
          text:
            state.datasetLayout === "video_catalog"
              ? "Use “+ Open video” to choose an active video from videos.csv, then open its interval cards. Removing a card only hides it from this view."
              : "Use “+ Add intervals” to search by video or image and open interval cards. Removing a card only hides it from this view.",
        }),
      );
    }

    if (dom.analyticalHint) {
      clearChildren(dom.analyticalHint);
      let hint;
      if (state.datasetLayout === "video_catalog") {
        hint = state.selectedRunId
          ? `Video catalog · open a video before loading intervals. Predictions for run ${state.selectedRunId} load per selected frame.`
          : "Video catalog · open a video from the CSV list before loading its intervals.";
      } else {
        hint = state.selectedRunId
          ? `Interval browse · predictions for run ${state.selectedRunId} load per selected frame. Reviews stay per image.`
          : "Interval browse · dataset-only view — predictions are hidden until a run is selected.";
      }
      dom.analyticalHint.appendChild(document.createTextNode(hint));
    }

    for (const open of state.openIntervals) {
      cardsRoot.appendChild(buildIntervalCard(open));
    }
  }

  function renderCardsPredictionsOnly() {
    if (!dom.frameCards) return;
    if (isIntervalBrowse()) {
      for (const open of state.openIntervals) {
        if (!open.currentImage) continue;
        updateIntervalCardPredictionInPlace(open);
      }
      renderRunInfo();
      return;
    }
    for (const imageId of state.openCards) {
      const card = dom.frameCards.querySelector(`[data-image-id="${cssEscape(imageId)}"]`);
      const image = findImage(imageId);
      if (!card || !image) continue;
      const predHost = card.querySelector("[data-role='prediction-block']");
      if (predHost) {
        clearChildren(predHost);
        predHost.appendChild(buildPredictionBlock(imageId));
      }
    }
    renderRunInfo();
  }

  /**
   * @param {{
   *   cardId: string,
   *   segmentId: string,
   *   title: string,
   *   imageCount: number,
   *   frames: any[] | null,
   *   currentIndex: number,
   *   currentImage: any | null,
   *   displayId: string | null,
   *   prediction: any | null,
   *   loadGen: number,
   *   status: string,
   *   errorMessage: string | null,
   * }} open
   */
  function buildIntervalCard(open) {
    const image = open.currentImage;
    const draft = image ? effectiveDraft(image) : { comments: "", dirty: false };
    const op = image ? saveOpForImage(image.image_id) : null;
    const card = el("article", {
      className: `frame-card${draft.dirty || op ? " is-draft" : ""}`,
      "data-card-id": open.cardId,
      "data-segment-id": open.segmentId,
      "data-image-id": image ? image.image_id : "",
    });

    const header = el("div", { className: "frame-card-header" });
    header.appendChild(el("h3", { text: open.title }));
    header.appendChild(
      el("span", {
        className: "count",
        text: `${open.imageCount} image${open.imageCount === 1 ? "" : "s"}`,
      }),
    );
    card.appendChild(header);

    if (image) {
      const bannerText = cardBannerText(image);
      if (bannerText) {
        card.appendChild(
          el("div", { className: "draft-banner", "data-role": "draft-banner", text: bannerText }),
        );
      }
    }

    const body = el("div", { className: "frame-body" });
    body.appendChild(buildIntervalMediaColumn(open));
    if (image && open.status !== "loading") {
      body.appendChild(buildDetailsColumn(image, draft));
    } else if (open.status === "error") {
      const errCol = el("div", { className: "frame-details" });
      errCol.appendChild(
        el("p", {
          className: "save-error",
          text: open.errorMessage || "Failed to load frame.",
        }),
      );
      const retry = el("button", {
        type: "button",
        className: "btn btn-secondary btn-sm",
        text: "Retry",
      });
      retry.addEventListener("click", () =>
        loadIntervalFrame(open.segmentId, open.currentIndex),
      );
      errCol.appendChild(retry);
      body.appendChild(errCol);
    } else {
      const loadingCol = el("div", { className: "frame-details" });
      loadingCol.appendChild(el("p", { className: "muted", text: "Loading frame…" }));
      body.appendChild(loadingCol);
    }

    const removeRow = el("div", { className: "frame-actions" });
    const remove = el("button", {
      type: "button",
      className: "btn btn-danger-ghost btn-sm",
      text: "Remove from view",
      title:
        "Removes this interval card from the current view only. Does not delete images or reviews.",
    });
    remove.addEventListener("click", () => removeIntervalCard(open.segmentId));
    removeRow.appendChild(remove);
    if (!(image && open.status !== "loading")) {
      body.appendChild(removeRow);
    }
    card.appendChild(body);
    return card;
  }

  /**
   * @param {typeof state.openIntervals[number]} open
   */
  function buildIntervalMediaColumn(open) {
    const identity = currentDatasetIdentity();
    const col = el("div", { className: "frame-media" });
    const wrap = el("div", {
      className: `frame-image-wrap${open.status === "loading" ? " is-meta-loading" : ""}`,
    });
    const status = el("div", {
      className: "image-status",
      "data-role": "image-status",
      text: open.status === "error" ? open.errorMessage || "Failed to load." : "Loading image…",
    });
    if (open.status === "error") status.dataset.kind = "error";
    wrap.appendChild(status);

    const img = el("img", {
      className: "frame-image is-pending",
      alt: open.currentImage
        ? `Original image ${open.currentImage.image_id}`
        : `Interval ${open.segmentId}`,
      decoding: "async",
    });

    const markLoaded = () => {
      status.hidden = true;
      delete status.dataset.kind;
      img.classList.remove("is-pending");
      img.classList.add("is-loaded");
    };
    const markError = () => {
      img.classList.remove("is-loaded");
      img.classList.add("is-pending");
      status.hidden = false;
      status.dataset.kind = "error";
      clearChildren(status);
      status.appendChild(document.createTextNode("Image failed to load."));
    };

    img.addEventListener("load", markLoaded);
    img.addEventListener("error", markError);

    if (open.currentImage && open.status !== "loading" && identity) {
      const imageId = open.currentImage.image_id;
      img.addEventListener("click", () => openViewer(imageId, img));
      img.src = imageContentUrl(
        identity.datasetId,
        identity.datasetVersion,
        imageId,
        open.videoId || null,
      );
      if (img.complete && img.naturalWidth > 0) markLoaded();
      else if (img.complete && img.naturalWidth === 0 && img.getAttribute("src")) markError();
    }

    wrap.appendChild(img);
    col.appendChild(wrap);

    const nav = el("div", { className: "interval-nav" });
    const prev = el("button", {
      type: "button",
      className: "btn btn-secondary btn-sm",
      text: "Previous",
      disabled: open.currentIndex <= 0 || open.status === "loading",
    });
    prev.addEventListener("click", () => navigateInterval(open.segmentId, -1));
    const next = el("button", {
      type: "button",
      className: "btn btn-secondary btn-sm",
      text: "Next",
      disabled:
        !open.frames ||
        open.currentIndex >= open.frames.length - 1 ||
        open.status === "loading",
    });
    next.addEventListener("click", () => navigateInterval(open.segmentId, 1));
    const pos = open.frames
      ? `${open.currentIndex + 1} / ${open.frames.length}`
      : `— / ${open.imageCount}`;
    nav.appendChild(prev);
    nav.appendChild(el("span", { className: "interval-position", text: pos }));
    nav.appendChild(next);
    col.appendChild(nav);

    const ids = el("div", { className: "interval-ids" });
    if (open.displayId) {
      ids.appendChild(el("div", { className: "display-id", text: open.displayId }));
    }
    if (open.currentImage) {
      ids.appendChild(
        el("div", {
          className: "tech-id",
          text: `image_id: ${open.currentImage.image_id}`,
        }),
      );
    }
    col.appendChild(ids);

    if (open.currentImage && open.status !== "loading") {
      const zoomBtn = el("button", {
        type: "button",
        className: "btn btn-secondary btn-sm",
        text: "Zoom / open viewer",
      });
      zoomBtn.addEventListener("click", () =>
        openViewer(open.currentImage.image_id, zoomBtn),
      );
      col.appendChild(zoomBtn);
    }
    return col;
  }

  /**
   * @param {typeof state.openIntervals[number]} open
   */
  function findIntervalCardElement(open) {
    if (!dom.frameCards || !open) return null;
    return /** @type {HTMLElement | null} */ (
      dom.frameCards.querySelector(`[data-card-id="${cssEscape(open.cardId)}"]`)
    );
  }

  /**
   * Replace only the affected interval card DOM node (preserve siblings' textareas).
   * @param {typeof state.openIntervals[number]} open
   */
  function updateIntervalCardDom(open) {
    if (!dom.frameCards) return;
    syncIntervalEmptyState();
    const existing = findIntervalCardElement(open);
    const replacement = buildIntervalCard(open);
    if (existing) {
      existing.replaceWith(replacement);
    } else {
      dom.frameCards.appendChild(replacement);
    }
  }

  /**
   * Update prediction host in place when the current image identity is unchanged.
   * @param {typeof state.openIntervals[number]} open
   */
  function updateIntervalCardPredictionInPlace(open) {
    const card = findIntervalCardElement(open);
    if (!card || !open.currentImage) {
      updateIntervalCardDom(open);
      return;
    }
    card.setAttribute("data-image-id", open.currentImage.image_id);
    const predHost = card.querySelector("[data-role='prediction-block']");
    if (predHost) {
      clearChildren(predHost);
      predHost.appendChild(buildPredictionBlock(open.currentImage.image_id));
    }
  }

  function syncIntervalEmptyState() {
    const empty = dom.analyticalEmpty;
    if (!empty) return;
    if (!isIntervalBrowse()) return;
    if (state.openIntervals.length === 0) {
      clearChildren(empty);
      empty.hidden = false;
      empty.appendChild(el("p", { text: "No intervals open in this view." }));
      empty.appendChild(
        el("p", {
          text: "Use “+ Add intervals” to search by video or image and open interval cards. Removing a card only hides it from this view.",
        }),
      );
    } else {
      empty.hidden = true;
      clearChildren(empty);
    }
  }

  /** @param {string} segmentId @param {number} delta */
  function navigateInterval(segmentId, delta) {
    const open = findOpenInterval(segmentId);
    if (!open || !open.frames) return;
    const next = intervalLogic().nextFrameIndex(open.currentIndex, delta, open.frames.length);
    if (next == null) return;
    void loadIntervalFrame(segmentId, next);
  }

  function intervalBrowseDeps() {
    const logic = intervalLogic();
    return {
      currentIdentity: currentDatasetIdentity,
      selectedRunId: () => state.selectedRunId || null,
      selectionGen: () => state.selectionGen,
      findOpenInterval,
      findOpenIntervalByCardId,
      getCachedImage: (datasetId, datasetVersion, imageId) => {
        const key = logic.imageCacheKey(datasetId, datasetVersion, imageId);
        return state.imageCache.get(key) || null;
      },
      setCachedImage: cacheImageForIdentity,
      fetchFrameView: async ({ datasetId, datasetVersion, imageId, runId, videoId }) => {
        let path =
          `/api/datasets/${encodeURIComponent(datasetId)}` +
          `/versions/${encodeURIComponent(datasetVersion)}` +
          `/images/${encodeURIComponent(imageId)}/view`;
        const params = [];
        if (runId) params.push(`run_id=${encodeURIComponent(runId)}`);
        if (videoId) params.push(`video_id=${encodeURIComponent(videoId)}`);
        if (params.length) path += `?${params.join("&")}`;
        return apiGet(path);
      },
      fetchIntervalFrames: async ({ datasetId, datasetVersion, segmentId, videoId }) => {
        let path =
          `/api/datasets/${encodeURIComponent(datasetId)}` +
          `/versions/${encodeURIComponent(datasetVersion)}` +
          `/intervals/${encodeURIComponent(segmentId)}/frames`;
        if (videoId) path += `?video_id=${encodeURIComponent(videoId)}`;
        return apiGet(path);
      },
      ensureIntervalFrames: (cardId) =>
        logic.executeEnsureIntervalFrames(intervalBrowseDeps(), cardId),
      loadIntervalFrame: (segmentId, frameIndex, options) =>
        loadIntervalFrame(segmentId, frameIndex, options),
      createOpenIntervalCard,
      appendIntervalCard: (card) => {
        state.openIntervals.push(card);
        updateIntervalCardDom(card);
      },
      setActiveTabAnalytical: () => setActiveTab("analytical"),
      focusIntervalCard,
      onCardLoading: (open) => updateIntervalCardDom(open),
      onCardUpdated: (open) => updateIntervalCardDom(open),
      onCardPredictionPending: () => {
        /* keep existing card UI while prediction refresh is in flight */
      },
      onCardPredictionUpdated: (open) => updateIntervalCardPredictionInPlace(open),
      onPredictionError: (err) => {
        const msg = errorMessage(err);
        if (msg) showBanner(`Prediction refresh failed: ${msg}`, "warning");
      },
      errorMessage,
    };
  }

  /**
   * @param {string} segmentId
   * @param {number} frameIndex
   * @param {{ predictionRefresh?: boolean }} [options]
   */
  async function loadIntervalFrame(segmentId, frameIndex, options) {
    return intervalLogic().executeLoadIntervalFrame(
      intervalBrowseDeps(),
      segmentId,
      frameIndex,
      options,
    );
  }

  /** @param {string} cardId */
  async function ensureIntervalFrames(cardId) {
    return intervalLogic().executeEnsureIntervalFrames(intervalBrowseDeps(), cardId);
  }

  /**
   * @param {string} segmentId
   * @param {{ title?: string, imageCount?: number, targetImageId?: string | null, videoId?: string | null }} [meta]
   */
  async function addOrFocusInterval(segmentId, meta) {
    return intervalLogic().executeAddOrFocusInterval(intervalBrowseDeps(), segmentId, meta);
  }

  /** @param {string} segmentId */
  function removeIntervalCard(segmentId) {
    const open = findOpenInterval(segmentId);
    if (!open) return;
    // Drop this card instance so in-flight responses for cardId cannot apply later.
    state.openIntervals = state.openIntervals.filter((item) => item.cardId !== open.cardId);
    const elCard = findIntervalCardElement(open);
    if (elCard) elCard.remove();
    syncIntervalEmptyState();
  }

  /** @param {string} segmentId */
  function focusIntervalCard(segmentId) {
    setActiveTab("analytical");
    const open = findOpenInterval(segmentId);
    const card = open ? findIntervalCardElement(open) : null;
    if (card instanceof HTMLElement) {
      card.scrollIntoView({ behavior: "smooth", block: "center" });
      card.classList.add("is-focused");
      window.setTimeout(() => card.classList.remove("is-focused"), 1600);
      const focusable = card.querySelector("button, select, textarea, input");
      if (focusable instanceof HTMLElement) focusable.focus();
    }
  }

  /** @param {any} image */
  function buildFrameCard(image) {
    const draft = effectiveDraft(image);
    const op = saveOpForImage(image.image_id);
    const card = el("article", {
      className: `frame-card${draft.dirty || op ? " is-draft" : ""}`,
      "data-image-id": image.image_id,
    });

    const bannerText = cardBannerText(image);
    if (bannerText) {
      card.appendChild(el("div", { className: "draft-banner", "data-role": "draft-banner", text: bannerText }));
    }

    const body = el("div", { className: "frame-body" });
    body.appendChild(buildMediaColumn(image));
    body.appendChild(buildDetailsColumn(image, draft));
    card.appendChild(body);
    return card;
  }

  /** @param {any} image */
  function buildMediaColumn(image) {
    const identity = currentDatasetIdentity();
    const col = el("div", { className: "frame-media" });
    const wrap = el("div", { className: "frame-image-wrap" });
    const status = el("div", {
      className: "image-status",
      "data-role": "image-status",
      text: "Loading image…",
    });
    wrap.appendChild(status);

    // Keep the <img> in layout (opacity/overlay) so loading="lazy" can start.
    const img = el("img", {
      className: "frame-image is-pending",
      alt: `Original image ${image.image_id}`,
      loading: "lazy",
      decoding: "async",
    });

    const markLoaded = () => {
      status.hidden = true;
      delete status.dataset.kind;
      img.classList.remove("is-pending");
      img.classList.add("is-loaded");
    };
    const markError = () => {
      img.classList.remove("is-loaded");
      img.classList.add("is-pending");
      status.hidden = false;
      status.dataset.kind = "error";
      clearChildren(status);
      status.appendChild(document.createTextNode("Image failed to load."));
    };

    // Register handlers before assigning src (cached images may fire synchronously).
    img.addEventListener("load", markLoaded);
    img.addEventListener("error", markError);
    img.addEventListener("click", () => openViewer(image.image_id, img));
    wrap.appendChild(img);

    if (identity) {
      img.src = imageContentUrl(
        identity.datasetId,
        identity.datasetVersion,
        image.image_id,
        videoIdForImage(image.image_id),
      );
      if (img.complete && img.naturalWidth > 0) {
        markLoaded();
      } else if (img.complete && img.naturalWidth === 0 && img.getAttribute("src")) {
        markError();
      }
    }

    col.appendChild(wrap);

    col.appendChild(el("div", { className: "image-id", text: image.image_id }));

    const zoomBtn = el("button", {
      type: "button",
      className: "btn btn-secondary btn-sm",
      text: "Zoom / open viewer",
    });
    zoomBtn.addEventListener("click", () => openViewer(image.image_id, zoomBtn));
    col.appendChild(zoomBtn);
    return col;
  }

  /**
   * @param {any} image
   * @param {{comments: string, dirty?: boolean}} draft
   */
  function buildDetailsColumn(image, draft) {
    const col = el("div", { className: "frame-details" });

    // Read-only effective ground truth (and original when different).
    col.appendChild(
      buildDetailRow("Ground truth", () => {
        const host = el("div", { className: "detail-value", "data-role": "gt-host" });
        fillReadOnlyGroundTruth(host, image);
        return host;
      }),
    );

    // Prediction block
    const predRow = buildDetailRow("Prediction", () => {
      const host = el("div", { className: "detail-value", "data-role": "prediction-block" });
      host.appendChild(buildPredictionBlock(image.image_id));
      return host;
    });
    col.appendChild(predRow);

    // Comments (drafts + comments-only Save)
    col.appendChild(
      buildDetailRow("Comments", () => {
        const host = el("div", { className: "detail-value", "data-role": "comments-host" });
        const area = el("textarea", {
          className: "comments-input",
          "data-role": "comments-input",
          "aria-label": `Comments for ${image.image_id}`,
        });
        area.value = draft.comments;
        if (commentsLocked(image.image_id)) {
          area.setAttribute("readonly", "");
        }
        area.addEventListener("input", () => {
          if (commentsLocked(image.image_id)) return;
          setCommentDraft(image, area.value);
        });
        host.appendChild(area);
        const op = saveOpForImage(image.image_id);
        if (
          op &&
          (op.status === "conflict" || op.status === "unconfirmed") &&
          (op.showCompare || op.status === "unconfirmed")
        ) {
          const compare = el("div", { className: "conflict-compare", "data-role": "conflict-compare" });
          compare.appendChild(
            el("div", { className: "muted", text: "Submitted Save (immutable):" }),
          );
          compare.appendChild(el("div", { className: "cell-clamp", text: op.submittedComments }));
          compare.appendChild(el("div", { className: "muted", text: "Your latest draft:" }));
          compare.appendChild(el("div", { className: "cell-clamp", text: draft.comments }));
          if (op.serverReview) {
            compare.appendChild(el("div", { className: "muted", text: "Current server comment:" }));
            compare.appendChild(
              el("div", {
                className: "cell-clamp",
                text:
                  op.serverReview.comments == null || op.serverReview.comments === ""
                    ? "(empty)"
                    : String(op.serverReview.comments),
              }),
            );
          } else if (op.serverFetchFailed) {
            compare.appendChild(
              el("div", {
                className: "save-error",
                text: "Could not load the current server review. Retry the refresh.",
              }),
            );
          }
          const refreshServer = el("button", {
            type: "button",
            className: "btn btn-secondary btn-sm",
            text: "Refresh server comment",
          });
          refreshServer.addEventListener("click", () =>
            refreshUnconfirmedServerReview(image.image_id),
          );
          compare.appendChild(refreshServer);
          if (op.status === "conflict" || op.serverReview) {
            const keep = el("button", {
              type: "button",
              className: "btn btn-secondary btn-sm",
              text: "Resolve & keep editing my draft",
              disabled: Boolean(op.status === "conflict" && op.serverFetchFailed && !op.serverReview),
            });
            keep.addEventListener("click", () => resolveConflictKeepDraft(image.image_id));
            compare.appendChild(keep);
          }
          host.appendChild(compare);
        }
        if (op && op.status === "error" && op.errorMessage) {
          host.appendChild(el("div", { className: "save-error", text: op.errorMessage }));
        }
        return host;
      }),
    );

    const actions = el("div", { className: "frame-actions" });
    const op = saveOpForImage(image.image_id);
    const saveBtn = el("button", {
      type: "button",
      className: "btn btn-primary btn-sm",
      "data-role": "save-btn",
      text: "Save comment",
      disabled: Boolean(
        (op &&
          (op.status === "pending" ||
            op.status === "conflict" ||
            op.status === "unconfirmed")) ||
          !draft.dirty,
      ),
    });
    saveBtn.addEventListener("click", () => {
      const current = saveOpForImage(image.image_id);
      if (
        current &&
        (current.status === "conflict" ||
          current.status === "unconfirmed" ||
          current.status === "pending")
      ) {
        return;
      }
      saveComment(image.image_id);
    });
    actions.appendChild(saveBtn);

    const discard = el("button", {
      type: "button",
      className: "btn btn-ghost btn-sm",
      "data-role": "discard-btn",
      text: "Discard changes",
      hidden: !draft.dirty && !(op && (op.status === "conflict" || op.status === "unconfirmed")),
      disabled: Boolean(op && op.status === "pending"),
    });
    discard.addEventListener("click", () => discardDraft(image.image_id));
    actions.appendChild(discard);

    const remove = el("button", {
      type: "button",
      className: "btn btn-danger-ghost btn-sm",
      text: "Remove from view",
      title: "Removes this card from the current view only. Does not delete the image or review.",
    });
    remove.addEventListener("click", () => removeFromView(image.image_id));
    actions.appendChild(remove);
    col.appendChild(actions);

    return col;
  }

  /**
   * @param {string} label
   * @param {() => Node} valueFactory
   */
  function buildDetailRow(label, valueFactory) {
    const row = el("div", { className: "detail-row" });
    row.appendChild(el("div", { className: "detail-label", text: label }));
    row.appendChild(valueFactory());
    return row;
  }

  /**
   * @param {HTMLElement} host
   * @param {any} image
   */
  function fillReadOnlyGroundTruth(host, image) {
    clearChildren(host);
    const effective = image.effective_ground_truth;
    host.appendChild(
      el("span", {
        className: `label-pill ${effective === 1 ? "present" : "absent"}`,
        text: formatBinaryLabel(effective),
      }),
    );

    if (
      isBinaryLabel(image.original_ground_truth) &&
      image.original_ground_truth !== image.effective_ground_truth
    ) {
      const orig = el("div", { className: "original-gt" });
      orig.appendChild(
        document.createTextNode(
          `Original dataset ground truth: ${formatBinaryLabel(image.original_ground_truth)}`,
        ),
      );
      host.appendChild(orig);
    }
  }

  /** @param {string} imageId */
  function buildPredictionBlock(imageId) {
    const wrap = el("div");
    if (!state.selectedRunId) {
      wrap.appendChild(
        el("span", {
          className: "muted",
          text: "Select a run to view predictions.",
        }),
      );
      return wrap;
    }
    if (state.loading) {
      wrap.appendChild(el("span", { className: "muted", text: "Loading prediction…" }));
      return wrap;
    }
    const runReady = isIntervalBrowse()
      ? Boolean(state.runOverview)
      : Boolean(state.runDetail);
    if (state.runLoadError || !runReady) {
      wrap.appendChild(
        el("span", {
          className: "muted",
          text: "Prediction unavailable — run failed to load.",
        }),
      );
      return wrap;
    }
    const prediction = findPrediction(imageId);
    if (!prediction || prediction.available !== true) {
      wrap.appendChild(el("span", { text: NO_PREDICTION }));
      return wrap;
    }

    const label = el("div");
    label.appendChild(
      el("span", {
        className: `label-pill ${prediction.predicted_label === 1 ? "present" : "absent"}`,
        text: formatBinaryLabel(prediction.predicted_label),
      }),
    );
    wrap.appendChild(label);

    const probText = formatProbability(prediction.positive_class_probability);
    if (probText !== null) {
      const prob = el("div", { className: "muted" });
      prob.appendChild(document.createTextNode(`P(CVS = 1): ${probText}`));
      wrap.appendChild(prob);
    }

    if (prediction.description != null && prediction.description !== "") {
      const desc = el("div", { className: "cell-clamp" });
      desc.appendChild(document.createTextNode(String(prediction.description)));
      wrap.appendChild(desc);
    }
    return wrap;
  }

  /**
   * Update banners/buttons without replacing the textarea DOM node.
   * @param {string} imageId
   */
  function updateCardDraftChromeInPlace(imageId) {
    if (!dom.frameCards) return;
    const card = /** @type {HTMLElement | null} */ (
      dom.frameCards.querySelector(`[data-image-id="${cssEscape(imageId)}"]`)
    );
    if (!card) return;
    const image = findImage(imageId);
    if (!image) return;
    const draft = effectiveDraft(image);
    const op = saveOpForImage(imageId);
    card.classList.toggle("is-draft", Boolean(draft.dirty || op));

    const bannerText = cardBannerText(image);
    let banner = card.querySelector("[data-role='draft-banner']");
    if (bannerText) {
      if (!(banner instanceof HTMLElement)) {
        banner = el("div", {
          className: "draft-banner",
          "data-role": "draft-banner",
          text: bannerText,
        });
        card.insertBefore(banner, card.firstChild);
      } else {
        clearChildren(banner);
        banner.appendChild(document.createTextNode(bannerText));
      }
    } else if (banner) {
      banner.remove();
    }

    const area = card.querySelector("[data-role='comments-input']");
    if (area instanceof HTMLTextAreaElement) {
      const locked = commentsLocked(imageId);
      if (locked) area.setAttribute("readonly", "");
      else area.removeAttribute("readonly");
      // Do not assign area.value here during typing — preserves caret/composition.
    }

    const saveBtn = card.querySelector("[data-role='save-btn']");
    if (saveBtn instanceof HTMLButtonElement) {
      saveBtn.textContent = "Save comment";
      saveBtn.disabled = Boolean(
        (op &&
          (op.status === "pending" ||
            op.status === "conflict" ||
            op.status === "unconfirmed")) ||
          !draft.dirty,
      );
    }
    const discard = card.querySelector("[data-role='discard-btn']");
    if (discard instanceof HTMLButtonElement) {
      discard.hidden =
        !draft.dirty && !(op && (op.status === "conflict" || op.status === "unconfirmed"));
      discard.disabled = Boolean(op && op.status === "pending");
    }
  }

  /** @param {string} imageId */
  function updateCardDraftChrome(imageId) {
    updateCardDraftChromeInPlace(imageId);
  }

  /**
   * Full field refresh (may replace the card). Used after Save outcomes, not per keystroke.
   * @param {HTMLElement} card
   * @param {any} image
   */
  function refreshCardFields(card, image) {
    const replacement = buildFrameCard(image);
    card.replaceWith(replacement);
  }

  /** @param {string} imageId */
  function removeCard(imageId) {
    state.openCards = state.openCards.filter((id) => id !== imageId);
    renderAnalytical();
  }

  /** @param {string} imageId */
  function removeFromView(imageId) {
    if (isIntervalBrowse()) {
      const open = state.openIntervals.find(
        (item) => item.currentImage && item.currentImage.image_id === imageId,
      );
      if (open) removeIntervalCard(open.segmentId);
      return;
    }
    removeCard(imageId);
  }

  /** @param {string[]} imageIds */
  function addCards(imageIds) {
    /** @type {string | null} */
    let focusId = null;
    for (const id of imageIds) {
      if (state.openCards.includes(id)) {
        focusId = focusId || id;
        continue;
      }
      state.openCards.push(id);
      focusId = focusId || id;
    }
    renderAnalytical();
    if (focusId) focusCard(focusId);
  }

  /** @param {string} imageId */
  function focusCard(imageId) {
    setActiveTab("analytical");
    if (!state.openCards.includes(imageId)) {
      state.openCards.push(imageId);
      renderAnalytical();
    }
    const card = dom.frameCards && dom.frameCards.querySelector(`[data-image-id="${cssEscape(imageId)}"]`);
    if (card instanceof HTMLElement) {
      card.scrollIntoView({ behavior: "smooth", block: "center" });
      card.classList.add("is-focused");
      window.setTimeout(() => card.classList.remove("is-focused"), 1600);
      const focusable = card.querySelector("button, select, textarea, input");
      if (focusable instanceof HTMLElement) focusable.focus();
    }
  }

  // ---------------------------------------------------------------------------
  // Picker
  // ---------------------------------------------------------------------------

  function openPicker() {
    if (!currentDatasetIdentity()) return;
    state.pickerSession += 1;
    state.pickerRequestId += 1;
    state.pickerSelected = new Set();
    state.pickerSearch = "";
    state.pickerOffset = 0;
    state.pickerResults = null;
    state.pickerResultsRequestId = 0;
    state.pickerError = null;
    state.pickerLoading = false;
    state.pickerTargetImages = new Map();
    dom.pickerSearch.value = "";
    if (dom.pickerTitle) {
      clearChildren(dom.pickerTitle);
      let title = "Add frames";
      if (isIntervalBrowse()) {
        title = state.datasetLayout === "video_catalog" ? "Open video" : "Add intervals";
      }
      dom.pickerTitle.appendChild(document.createTextNode(title));
    }
    if (dom.pickerSearchLabel) {
      clearChildren(dom.pickerSearchLabel);
      let label = "Search by image ID";
      if (isIntervalBrowse()) {
        label =
          state.datasetLayout === "video_catalog"
            ? "Filter videos or search image ID / display ID"
            : "Search video name, video ID, image ID, or display ID";
      }
      dom.pickerSearchLabel.appendChild(document.createTextNode(label));
    }
    if (dom.pickerAddAllBtn) {
      dom.pickerAddAllBtn.hidden = !isIntervalBrowse() || state.datasetLayout === "video_catalog";
      dom.pickerAddAllBtn.disabled = true;
    }
    if (dom.pickerAddBtn) {
      clearChildren(dom.pickerAddBtn);
      dom.pickerAddBtn.appendChild(
        document.createTextNode(
          state.datasetLayout === "video_catalog" && isIntervalBrowse()
            ? "Open selected video"
            : "Add selected",
        ),
      );
    }
    if (dom.pickerSearchBtn) {
      dom.pickerSearchBtn.hidden = !(
        isIntervalBrowse() && state.datasetLayout === "video_catalog"
      );
    }
    state.pickerExplicitImageSearch = false;
    state.videoCatalogList = null;
    openModal(dom.pickerModal, dom.addFramesBtn);
    dom.pickerSearch.focus();
    if (isIntervalBrowse()) {
      void loadIntervalPickerPage({ trigger: "type" });
    } else {
      renderPicker();
    }
  }

  let pickerSearchTimer = 0;

  function scheduleIntervalPickerSearch() {
    if (pickerSearchTimer) window.clearTimeout(pickerSearchTimer);
    pickerSearchTimer = window.setTimeout(() => {
      state.pickerOffset = 0;
      // Typing never triggers cross-video image search in video_catalog mode.
      state.pickerExplicitImageSearch = false;
      void loadIntervalPickerPage({ trigger: "type" });
    }, 200);
  }

  function runExplicitImageSearch() {
    const started = videoCatalogLogic().beginExplicitImageSearch(
      pickerSearchTimer,
      (handle) => window.clearTimeout(handle),
    );
    pickerSearchTimer = started.timerHandle;
    state.pickerOffset = 0;
    state.pickerExplicitImageSearch = true;
    void loadIntervalPickerPage({ trigger: started.trigger });
  }

  function pickerDeps() {
    return {
      currentIdentity: currentDatasetIdentity,
      pickerSession: () => state.pickerSession,
      pickerRequestId: () => state.pickerRequestId,
      pickerSearch: () => state.pickerSearch,
      pickerOffset: () => state.pickerOffset,
      selectionGen: () => state.selectionGen,
    };
  }

  function pickerResultsAreActionable() {
    return (
      !state.pickerLoading &&
      state.pickerResults != null &&
      state.pickerResultsRequestId === state.pickerRequestId
    );
  }

  /**
   * @param {{ trigger?: "type"|"explicit" }} [options]
   */
  async function loadIntervalPickerPage(options) {
    const identity = currentDatasetIdentity();
    if (!identity || !isIntervalBrowse()) return;
    const trigger = (options && options.trigger) || "type";
    const q = state.pickerSearch.trim();
    const offset = state.pickerOffset;
    state.pickerRequestId += 1;
    const requestId = state.pickerRequestId;
    const token = {
      datasetId: identity.datasetId,
      datasetVersion: identity.datasetVersion,
      pickerSession: state.pickerSession,
      requestId,
      query: q,
      offset,
      selectionGen: state.selectionGen,
    };
    state.pickerLoading = true;
    state.pickerError = null;
    // Stale results must not remain actionable while a newer search is pending.
    state.pickerResults = null;
    state.pickerResultsRequestId = 0;
    state.pickerSelected = new Set();
    renderPicker();
    try {
      /** @type {any} */
      let payload;
      const mode = videoCatalogLogic().pickerSearchMode(state.datasetLayout, trigger);
      if (state.datasetLayout === "video_catalog" && mode === "csv_filter") {
        // Typing / empty browse: CSV list only (client filter; no video JSON scan).
        if (!state.videoCatalogList) {
          const listed = await apiGet(
            `/api/datasets/${encodeURIComponent(identity.datasetId)}` +
              `/versions/${encodeURIComponent(identity.datasetVersion)}/videos`,
          );
          if (!intervalLogic().pickerRequestStillValid(token, pickerDeps())) return;
          state.videoCatalogList = Array.isArray(listed.videos) ? listed.videos : [];
        }
        const filtered = videoCatalogLogic().filterVideosFromCsv(state.videoCatalogList, q);
        const page = filtered.slice(offset, offset + PICKER_PAGE_SIZE);
        payload = {
          query: q,
          match_kind: "video_list",
          hits: page.map((video) => ({ video })),
          total: filtered.length,
          offset,
          limit: PICKER_PAGE_SIZE,
        };
      } else if (q || state.pickerExplicitImageSearch) {
        payload = await apiGet(
          `/api/datasets/${encodeURIComponent(identity.datasetId)}` +
            `/versions/${encodeURIComponent(identity.datasetVersion)}/intervals/search` +
            `?q=${encodeURIComponent(q)}&offset=${offset}&limit=${PICKER_PAGE_SIZE}`,
        );
      } else {
        const listed = await apiGet(
          `/api/datasets/${encodeURIComponent(identity.datasetId)}` +
            `/versions/${encodeURIComponent(identity.datasetVersion)}/intervals` +
            `?offset=${offset}&limit=${PICKER_PAGE_SIZE}`,
        );
        payload = {
          query: "",
          match_kind: "empty",
          hits: (listed.intervals || []).map((interval) => ({
            interval,
            target_image_id: null,
            target_frame_index: null,
          })),
          total: listed.total,
          offset: listed.offset,
          limit: listed.limit,
        };
      }
      if (!intervalLogic().pickerRequestStillValid(token, pickerDeps())) return;
      state.pickerResults = payload;
      state.pickerResultsRequestId = requestId;
      state.pickerTargetImages = new Map();
      for (const hit of payload.hits || []) {
        if (hit.target_image_id && hit.interval) {
          state.pickerTargetImages.set(hit.interval.segment_id, hit.target_image_id);
        }
      }
      state.pickerLoading = false;
      renderPicker();
    } catch (err) {
      if (!intervalLogic().pickerRequestStillValid(token, pickerDeps())) return;
      state.pickerLoading = false;
      state.pickerResults = null;
      state.pickerResultsRequestId = 0;
      state.pickerError = errorMessage(err) || "Picker search failed.";
      renderPicker();
    }
  }

  function renderPicker() {
    if (!dom.pickerGrid) return;
    clearChildren(dom.pickerGrid);
    if (dom.pickerMatchInfo) {
      dom.pickerMatchInfo.hidden = true;
      clearChildren(dom.pickerMatchInfo);
    }
    if (dom.pickerPager) dom.pickerPager.hidden = true;

    if (isIntervalBrowse()) {
      renderIntervalPicker();
      return;
    }
    if (!state.datasetDetail) return;
    const identity = currentDatasetIdentity();
    const q = state.pickerSearch.trim().toLowerCase();
    const images = Array.isArray(state.datasetDetail.images) ? state.datasetDetail.images : [];
    const filtered = images.filter((img) => {
      if (!q) return true;
      return String(img.image_id).toLowerCase().includes(q);
    });

    if (filtered.length === 0) {
      dom.pickerGrid.appendChild(el("p", { className: "muted", text: "No images match." }));
    }

    for (const image of filtered) {
      const already = state.openCards.includes(image.image_id);
      const selected = state.pickerSelected.has(image.image_id);
      const btn = el("button", {
        type: "button",
        className: `picker-item${selected ? " selected" : ""}${already ? " already-open" : ""}`,
        "aria-pressed": selected ? "true" : "false",
      });
      const thumbWrap = el("div", { className: "picker-thumb-wrap" });
      if (identity) {
        const thumb = el("img", {
          className: "picker-thumb",
          alt: "",
          loading: "lazy",
          decoding: "async",
        });
        thumb.src = imageContentUrl(
          identity.datasetId,
          identity.datasetVersion,
          image.image_id,
        );
        thumb.addEventListener("error", () => {
          thumb.remove();
          thumbWrap.appendChild(el("span", { className: "muted", text: "Preview unavailable" }));
        });
        thumbWrap.appendChild(thumb);
      }
      btn.appendChild(thumbWrap);
      btn.appendChild(el("div", { className: "picker-id", text: image.image_id }));
      if (already) {
        btn.appendChild(el("div", { className: "picker-note", text: "Already open" }));
      }
      btn.addEventListener("click", () => {
        if (already) {
          closeModal(dom.pickerModal);
          focusCard(image.image_id);
          return;
        }
        if (state.pickerSelected.has(image.image_id)) state.pickerSelected.delete(image.image_id);
        else state.pickerSelected.add(image.image_id);
        renderPicker();
      });
      dom.pickerGrid.appendChild(btn);
    }

    const count = state.pickerSelected.size;
    clearChildren(dom.pickerSelectionCount);
    dom.pickerSelectionCount.appendChild(
      document.createTextNode(count === 0 ? "No images selected" : `${count} selected`),
    );
    dom.pickerAddBtn.disabled = count === 0;
    if (dom.pickerAddAllBtn) {
      dom.pickerAddAllBtn.hidden = true;
      dom.pickerAddAllBtn.disabled = true;
    }
  }

  function renderIntervalPicker() {
    const identity = currentDatasetIdentity();
    if (!identity || !dom.pickerGrid) return;

    if (state.pickerLoading && !state.pickerResults) {
      dom.pickerGrid.appendChild(
        el("p", {
          className: "muted",
          text:
            state.datasetLayout === "video_catalog"
              ? "Loading videos…"
              : "Loading intervals…",
        }),
      );
    }
    if (state.pickerError) {
      dom.pickerGrid.appendChild(el("p", { className: "save-error", text: state.pickerError }));
    }

    const results = state.pickerResults;
    const hits = results && Array.isArray(results.hits) ? results.hits : [];
    if (results && results.match_kind === "video_list") {
      renderVideoCatalogPicker(identity, results, hits);
      return;
    }
    if (dom.pickerMatchInfo && results) {
      let info = "";
      if (results.match_kind === "video") {
        info = `Video match · ${results.total} interval(s)`;
      } else if (results.match_kind === "image") {
        info = "Image match · opens the owning interval at that frame";
      } else if (results.match_kind === "none") {
        info = "No intervals match.";
      } else if (!state.pickerSearch.trim()) {
        info = `Browsing intervals · ${results.total} total`;
      }
      if (info) {
        clearChildren(dom.pickerMatchInfo);
        dom.pickerMatchInfo.appendChild(document.createTextNode(info));
        dom.pickerMatchInfo.hidden = false;
      }
    }

    if (!state.pickerLoading && hits.length === 0 && !state.pickerError) {
      dom.pickerGrid.appendChild(el("p", { className: "muted", text: "No intervals match." }));
    }

    for (const hit of hits) {
      const interval = hit.interval;
      if (!interval) continue;
      const already = Boolean(findOpenInterval(interval.segment_id));
      const selected = state.pickerSelected.has(interval.segment_id);
      const btn = el("button", {
        type: "button",
        className: `picker-item${selected ? " selected" : ""}${already ? " already-open" : ""}`,
        "aria-pressed": selected ? "true" : "false",
      });
      const thumbWrap = el("div", { className: "picker-thumb-wrap" });
      const thumb = el("img", {
        className: "picker-thumb",
        alt: "",
        loading: "lazy",
        decoding: "async",
      });
      thumb.src = imageContentUrl(
        identity.datasetId,
        identity.datasetVersion,
        interval.first_image_id,
        interval.video_id || null,
      );
      thumb.addEventListener("error", () => {
        thumb.remove();
        thumbWrap.appendChild(el("span", { className: "muted", text: "Preview unavailable" }));
      });
      thumbWrap.appendChild(thumb);
      btn.appendChild(thumbWrap);
      btn.appendChild(el("div", { className: "picker-title-line", text: interval.title }));
      btn.appendChild(
        el("div", {
          className: "picker-note",
          text: `${interval.image_count} images · ${interval.video_filename}`,
        }),
      );
      if (hit.target_image_id) {
        btn.appendChild(
          el("div", { className: "picker-note", text: `Target frame: ${hit.target_image_id}` }),
        );
      }
      if (already) {
        btn.appendChild(el("div", { className: "picker-note", text: "Already open" }));
      }
      btn.addEventListener("click", () => {
        if (already) {
          closeModal(dom.pickerModal);
          void addOrFocusInterval(interval.segment_id, {
            title: interval.title,
            imageCount: interval.image_count,
            targetImageId:
              hit.target_image_id ||
              state.pickerTargetImages.get(interval.segment_id) ||
              null,
            videoId: interval.video_id || null,
          });
          return;
        }
        if (state.pickerSelected.has(interval.segment_id)) {
          state.pickerSelected.delete(interval.segment_id);
        } else {
          state.pickerSelected.add(interval.segment_id);
        }
        renderPicker();
      });
      dom.pickerGrid.appendChild(btn);
    }

    if (results && dom.pickerPager && dom.pickerPageLabel) {
      const total = results.total || 0;
      const limit = results.limit || PICKER_PAGE_SIZE;
      const offset = results.offset || 0;
      const page = Math.floor(offset / limit) + 1;
      const pages = Math.max(1, Math.ceil(total / limit));
      dom.pickerPager.hidden = total <= limit && offset === 0;
      clearChildren(dom.pickerPageLabel);
      dom.pickerPageLabel.appendChild(
        document.createTextNode(`Page ${page} / ${pages} · ${total} result(s)`),
      );
      if (dom.pickerPrevPage) {
        dom.pickerPrevPage.disabled = offset <= 0 || state.pickerLoading;
      }
      if (dom.pickerNextPage) {
        dom.pickerNextPage.disabled = offset + limit >= total || state.pickerLoading;
      }
    }

    const actionable = pickerResultsAreActionable();
    const count = state.pickerSelected.size;
    clearChildren(dom.pickerSelectionCount);
    dom.pickerSelectionCount.appendChild(
      document.createTextNode(
        state.pickerLoading
          ? "Search in progress…"
          : count === 0
            ? "None selected"
            : `${count} selected`,
      ),
    );
    dom.pickerAddBtn.disabled = !actionable || count === 0;
    if (dom.pickerAddAllBtn) {
      const canAddAll =
        actionable &&
        results &&
        results.match_kind === "video" &&
        Array.isArray(results.hits) &&
        results.hits.length > 0;
      dom.pickerAddAllBtn.hidden = state.datasetLayout === "video_catalog";
      dom.pickerAddAllBtn.disabled = !canAddAll || state.datasetLayout === "video_catalog";
    }
  }

  /**
   * Video-catalog picker: CSV rows first; lazy preview per visible tile.
   * @param {{datasetId: string, datasetVersion: string}} identity
   * @param {any} results
   * @param {any[]} hits
   */
  function renderVideoCatalogPicker(identity, results, hits) {
    if (dom.pickerMatchInfo) {
      clearChildren(dom.pickerMatchInfo);
      const q = state.pickerSearch.trim();
      const info = q
        ? `Filtering videos from videos.csv · ${results.total != null ? results.total : 0} match(es). Use “Search image ID” or Enter for image/display ID lookup.`
        : `Active videos from videos.csv · ${results.total != null ? results.total : 0} total`;
      dom.pickerMatchInfo.appendChild(document.createTextNode(info));
      dom.pickerMatchInfo.hidden = false;
    }
    if (!state.pickerLoading && hits.length === 0 && !state.pickerError) {
      dom.pickerGrid.appendChild(el("p", { className: "muted", text: "No active videos." }));
    }
    for (const hit of hits) {
      const video = hit.video;
      if (!video) continue;
      const selected = state.pickerSelected.has(video.video_id);
      const label = videoCatalogLogic().videoLabelFromFilename(video.video_name);
      const btn = el("button", {
        type: "button",
        className: `picker-item${selected ? " selected" : ""}`,
        "aria-pressed": selected ? "true" : "false",
      });
      const thumbWrap = el("div", { className: "picker-thumb-wrap" });
      const thumb = el("img", {
        className: "picker-thumb",
        alt: "",
        loading: "lazy",
        decoding: "async",
      });
      thumbWrap.appendChild(thumb);
      btn.appendChild(thumbWrap);
      btn.appendChild(el("div", { className: "picker-title-line", text: label }));
      btn.appendChild(
        el("div", {
          className: "picker-note",
          text: video.video_name,
        }),
      );
      btn.appendChild(
        el("div", {
          className: "picker-note",
          text: video.video_id,
        }),
      );
      // Lazy preview: load only this video's JSON for the first ordered image.
      void (async () => {
        const session = state.pickerSession;
        const requestId = state.pickerRequestId;
        try {
          const preview = await apiGet(
            `/api/datasets/${encodeURIComponent(identity.datasetId)}` +
              `/versions/${encodeURIComponent(identity.datasetVersion)}` +
              `/videos/${encodeURIComponent(video.video_id)}/preview`,
          );
          if (
            session !== state.pickerSession ||
            requestId !== state.pickerRequestId ||
            !preview.first_image_id
          ) {
            return;
          }
          thumb.src = imageContentUrl(
            identity.datasetId,
            identity.datasetVersion,
            preview.first_image_id,
            video.video_id,
          );
        } catch (_err) {
          if (session !== state.pickerSession || requestId !== state.pickerRequestId) return;
          thumb.remove();
          thumbWrap.appendChild(el("span", { className: "muted", text: "Preview unavailable" }));
        }
      })();
      thumb.addEventListener("error", () => {
        thumb.remove();
        if (!thumbWrap.querySelector(".muted")) {
          thumbWrap.appendChild(el("span", { className: "muted", text: "Preview unavailable" }));
        }
      });
      btn.addEventListener("click", () => {
        // Single-select: opening one video at a time keeps interval load bounded.
        state.pickerSelected = new Set([video.video_id]);
        renderPicker();
      });
      dom.pickerGrid.appendChild(btn);
    }
    if (results && dom.pickerPager && dom.pickerPageLabel) {
      const total = results.total || 0;
      const limit = results.limit || PICKER_PAGE_SIZE;
      const offset = results.offset || 0;
      const page = Math.floor(offset / limit) + 1;
      const pages = Math.max(1, Math.ceil(total / limit));
      dom.pickerPager.hidden = total <= limit && offset === 0;
      clearChildren(dom.pickerPageLabel);
      dom.pickerPageLabel.appendChild(
        document.createTextNode(`Page ${page} / ${pages} · ${total} video(s)`),
      );
      if (dom.pickerPrevPage) {
        dom.pickerPrevPage.disabled = offset <= 0 || state.pickerLoading;
      }
      if (dom.pickerNextPage) {
        dom.pickerNextPage.disabled = offset + limit >= total || state.pickerLoading;
      }
    }
    const actionable = pickerResultsAreActionable();
    const count = state.pickerSelected.size;
    clearChildren(dom.pickerSelectionCount);
    dom.pickerSelectionCount.appendChild(
      document.createTextNode(
        state.pickerLoading
          ? "Loading…"
          : count === 0
            ? "No video selected"
            : "1 video selected",
      ),
    );
    dom.pickerAddBtn.disabled = !actionable || count === 0;
    if (dom.pickerAddAllBtn) {
      dom.pickerAddAllBtn.hidden = true;
      dom.pickerAddAllBtn.disabled = true;
    }
  }

  function batchAddDeps() {
    return {
      currentIdentity: currentDatasetIdentity,
      selectionGen: () => state.selectionGen,
      activeBatchId: () => state.activeBatchId,
    };
  }

  async function addSelectedIntervalsFromPicker() {
    if (!pickerResultsAreActionable()) {
      showBanner("Picker results changed. Search again before adding intervals.", "warning");
      return;
    }
    const identity = currentDatasetIdentity();
    if (!identity) return;
    const results = state.pickerResults;
    if (results && results.match_kind === "video_list") {
      await openSelectedVideoFromPicker();
      return;
    }
    const hits = results && Array.isArray(results.hits) ? results.hits : [];
    const selected = Array.from(state.pickerSelected);
    const targetMap = new Map(state.pickerTargetImages);
    state.activeBatchId += 1;
    const batchId = state.activeBatchId;
    const token = {
      datasetId: identity.datasetId,
      datasetVersion: identity.datasetVersion,
      selectionGen: state.selectionGen,
      batchId,
    };
    closeModal(dom.pickerModal);
    try {
      for (const segmentId of selected) {
        if (!intervalLogic().batchAddStillValid(token, batchAddDeps())) return;
        const hit = hits.find((item) => item.interval && item.interval.segment_id === segmentId);
        const interval = hit && hit.interval;
        const outcome = await addOrFocusInterval(segmentId, {
          title: interval ? interval.title : segmentId,
          imageCount: interval ? interval.image_count : 0,
          targetImageId: (hit && hit.target_image_id) || targetMap.get(segmentId) || null,
          videoId: interval ? interval.video_id : null,
        });
        if (outcome && outcome.outcome === "error") {
          showBanner(
            outcome.errorMessage ||
              errorMessage(outcome.error) ||
              `Failed to open interval ${segmentId}.`,
            "error",
          );
        }
      }
    } catch (err) {
      if (!intervalLogic().batchAddStillValid(token, batchAddDeps())) return;
      showBanner(errorMessage(err) || "Failed to add selected intervals.", "error");
    }
  }

  async function openSelectedVideoFromPicker() {
    const identity = currentDatasetIdentity();
    if (!identity) return;
    const selected = Array.from(state.pickerSelected);
    if (selected.length !== 1) {
      showBanner("Select one video to open its intervals.", "warning");
      return;
    }
    const videoId = selected[0];
    state.activeBatchId += 1;
    const batchId = state.activeBatchId;
    const token = {
      datasetId: identity.datasetId,
      datasetVersion: identity.datasetVersion,
      selectionGen: state.selectionGen,
      batchId,
    };
    closeModal(dom.pickerModal);
    state.selectedVideoId = videoId;
    try {
      let offset = 0;
      const limit = PICKER_PAGE_SIZE;
      /** @type {any[]} */
      const intervals = [];
      let total = Infinity;
      while (offset < total) {
        if (!intervalLogic().batchAddStillValid(token, batchAddDeps())) return;
        const page = await apiGet(
          `/api/datasets/${encodeURIComponent(identity.datasetId)}` +
            `/versions/${encodeURIComponent(identity.datasetVersion)}/intervals` +
            `?video_id=${encodeURIComponent(videoId)}&offset=${offset}&limit=${limit}`,
        );
        if (!intervalLogic().batchAddStillValid(token, batchAddDeps())) return;
        total = typeof page.total === "number" ? page.total : 0;
        const batch = Array.isArray(page.intervals) ? page.intervals : [];
        intervals.push(...batch);
        offset += limit;
        if (batch.length === 0) break;
      }
      for (const interval of intervals) {
        if (!intervalLogic().batchAddStillValid(token, batchAddDeps())) return;
        const outcome = await addOrFocusInterval(interval.segment_id, {
          title: interval.title,
          imageCount: interval.image_count,
          targetImageId: null,
          videoId: interval.video_id || videoId,
        });
        if (outcome && outcome.outcome === "error") {
          showBanner(
            outcome.errorMessage ||
              errorMessage(outcome.error) ||
              `Failed to open interval ${interval.segment_id}.`,
            "error",
          );
        }
      }
      setSelectionStatus(
        `Opened video · ${intervals.length} interval(s) from active catalog.`,
      );
    } catch (err) {
      if (!intervalLogic().batchAddStillValid(token, batchAddDeps())) return;
      showBanner(errorMessage(err) || "Failed to open video intervals.", "error");
    }
  }

  async function addAllMatchingIntervalsFromPicker() {
    if (!pickerResultsAreActionable()) {
      showBanner("Picker results changed. Search again before adding intervals.", "warning");
      return;
    }
    const identity = currentDatasetIdentity();
    const results = state.pickerResults;
    if (!identity || !results || results.match_kind !== "video") return;
    const q = state.pickerSearch.trim();
    state.activeBatchId += 1;
    const batchId = state.activeBatchId;
    const token = {
      datasetId: identity.datasetId,
      datasetVersion: identity.datasetVersion,
      selectionGen: state.selectionGen,
      batchId,
    };
    closeModal(dom.pickerModal);
    try {
      let offset = 0;
      const limit = PICKER_PAGE_SIZE;
      /** @type {any[]} */
      const all = [];
      while (offset < (results.total || 0)) {
        if (!intervalLogic().batchAddStillValid(token, batchAddDeps())) return;
        const page = await apiGet(
          `/api/datasets/${encodeURIComponent(identity.datasetId)}` +
            `/versions/${encodeURIComponent(identity.datasetVersion)}/intervals/search` +
            `?q=${encodeURIComponent(q)}&offset=${offset}&limit=${limit}`,
        );
        if (!intervalLogic().batchAddStillValid(token, batchAddDeps())) return;
        all.push(...(page.hits || []));
        offset += limit;
        if (!page.hits || page.hits.length === 0) break;
      }
      for (const hit of all) {
        if (!intervalLogic().batchAddStillValid(token, batchAddDeps())) return;
        if (!hit.interval) continue;
        const outcome = await addOrFocusInterval(hit.interval.segment_id, {
          title: hit.interval.title,
          imageCount: hit.interval.image_count,
          targetImageId: hit.target_image_id || null,
          videoId: hit.interval.video_id || null,
        });
        if (outcome && outcome.outcome === "error") {
          showBanner(
            outcome.errorMessage ||
              errorMessage(outcome.error) ||
              `Failed to open interval ${hit.interval.segment_id}.`,
            "error",
          );
        }
      }
    } catch (err) {
      if (!intervalLogic().batchAddStillValid(token, batchAddDeps())) return;
      showBanner(errorMessage(err) || "Failed to add matching intervals.", "error");
    }
  }

  // ---------------------------------------------------------------------------
  // Summary
  // ---------------------------------------------------------------------------

  /** Interval-level Summary table (video_catalog / provenance browse). */
  function renderIntervalSummaryTable(summary) {
    const s = summary;
    const allRows = Array.isArray(s.intervals) ? s.intervals : [];
    const q = state.summarySearch.trim();
    const rows = videoCatalogSummaryLogic().filterSummaryIntervals(allRows, q);

    const header = el("div", { className: "summary-interval-header" });
    header.appendChild(
      el("p", {
        text:
          `Effective summary · ${s.total_images} image(s) across ${allRows.length} interval(s). ` +
          `Effective GT — absent (0): ${s.effective_ground_truth.label_0}; ` +
          `present (1): ${s.effective_ground_truth.label_1}.`,
      }),
    );
    header.appendChild(
      el("p", {
        className: "muted",
        text: "One row per active interval. Ground truth is read-only effective GT; Mixed means frames in the interval disagree. Counts use persisted reviews, not unsaved drafts.",
      }),
    );
    dom.summaryTableWrap.appendChild(header);

    if (dom.summaryRowCount) {
      clearChildren(dom.summaryRowCount);
      dom.summaryRowCount.appendChild(
        document.createTextNode(`Showing ${rows.length} of ${allRows.length} interval(s)`),
      );
    }

    if (rows.length === 0) {
      dom.summaryTableWrap.appendChild(
        el("div", {
          className: "empty-state",
          text: allRows.length === 0 ? "No active intervals." : "No rows match the search.",
        }),
      );
      return;
    }

    const table = el("table", { className: "summary-table" });
    const thead = el("thead");
    const headRow = el("tr");
    for (const heading of ["Video", "Time interval", "Ground truth", "Image count"]) {
      headRow.appendChild(el("th", { text: heading, scope: "col" }));
    }
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = el("tbody");
    const fmtGt = videoCatalogSummaryLogic().formatIntervalGroundTruth;
    for (const row of rows) {
      const tr = el("tr");
      tr.appendChild(el("td", { text: row.video_label || "" }));
      tr.appendChild(el("td", { className: "mono", text: row.time_interval || "" }));
      const gtTd = el("td");
      const gtText = fmtGt(row.ground_truth);
      const gtClass =
        gtText === "Mixed" ? "mixed" : gtText === "1" ? "present" : "absent";
      gtTd.appendChild(
        el("span", {
          className: `label-pill ${gtClass}`,
          text: gtText,
        }),
      );
      tr.appendChild(gtTd);
      tr.appendChild(el("td", { text: String(row.image_count ?? 0) }));
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    dom.summaryTableWrap.appendChild(table);
  }

  function renderSummary() {
    if (!dom.summaryTableWrap) return;
    clearChildren(dom.summaryTableWrap);
    updateDraftNotices();
    syncSummaryLoadBars();

    if (!currentDatasetIdentity()) {
      dom.summaryTableWrap.appendChild(
        el("div", { className: "empty-state", text: state.loading ? "Loading…" : "No dataset selected." }),
      );
      if (dom.summaryRowCount) {
        clearChildren(dom.summaryRowCount);
      }
      return;
    }

    if (isIntervalBrowse()) {
      if (state.summaryLoading) {
        dom.summaryTableWrap.appendChild(
          el("div", {
            className: "empty-state",
            text: "Loading effective summary for active videos…",
          }),
        );
        if (dom.summaryRowCount) clearChildren(dom.summaryRowCount);
        return;
      }
      if (state.summaryError && (!state.summaryLoaded || !state.summary)) {
        const errBox = el("div", { className: "empty-state" });
        errBox.appendChild(el("p", { className: "save-error", text: state.summaryError }));
        const retry = el("button", {
          type: "button",
          className: "btn btn-secondary",
          text: "Retry load effective summary",
        });
        retry.addEventListener("click", () => loadSummaryExplicit({ force: true }));
        errBox.appendChild(retry);
        dom.summaryTableWrap.appendChild(errBox);
        if (dom.summaryRowCount) clearChildren(dom.summaryRowCount);
        return;
      }
      if (!state.summaryLoaded || !state.summary) {
        dom.summaryTableWrap.appendChild(
          el("div", {
            className: "empty-state",
            text: "Effective summary is not loaded. Use “Load effective summary” for active-video interval rows and ground-truth counts. Image bytes are not loaded for this table.",
          }),
        );
        if (dom.summaryRowCount) clearChildren(dom.summaryRowCount);
        return;
      }
      renderIntervalSummaryTable(state.summary);
      return;
    }

    if (!state.datasetDetail) {
      dom.summaryTableWrap.appendChild(
        el("div", { className: "empty-state", text: state.loading ? "Loading…" : "No dataset selected." }),
      );
      if (dom.summaryRowCount) {
        clearChildren(dom.summaryRowCount);
      }
      return;
    }

    const images = Array.isArray(state.datasetDetail.images) ? state.datasetDetail.images : [];
    const q = state.summarySearch.trim().toLowerCase();
    const rows = images.filter((image) => summaryRowMatches(image, q));

    if (dom.summaryRowCount) {
      clearChildren(dom.summaryRowCount);
      dom.summaryRowCount.appendChild(
        document.createTextNode(`Showing ${rows.length} of ${images.length}`),
      );
    }

    if (state.runLoadError && state.selectedRunId) {
      const errBox = el("div", { className: "empty-state" });
      errBox.appendChild(
        el("p", {
          text: `Run data failed to load: ${state.runLoadError}`,
        }),
      );
      errBox.appendChild(
        el("p", {
          className: "muted",
          text: "Dataset rows below still show persisted labels/comments. Predictions are not available until retry succeeds.",
        }),
      );
      dom.summaryTableWrap.appendChild(errBox);
    }

    if (rows.length === 0) {
      dom.summaryTableWrap.appendChild(
        el("div", {
          className: "empty-state",
          text: images.length === 0 ? "This dataset has no images." : "No rows match the search.",
        }),
      );
      return;
    }

    const table = el("table", { className: "summary-table" });
    const thead = el("thead");
    const headRow = el("tr");
    for (const heading of [
      "Image ID",
      "Ground truth",
      "Prediction",
      "P(CVS = 1)",
      "Model description",
      "Comments",
      "",
    ]) {
      headRow.appendChild(el("th", { text: heading, scope: "col" }));
    }
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = el("tbody");
    for (const image of rows) {
      const tr = el("tr");
      tr.appendChild(el("td", { className: "mono", text: image.image_id }));

      const gtTd = el("td");
      gtTd.appendChild(
        el("span", {
          className: `label-pill ${image.effective_ground_truth === 1 ? "present" : "absent"}`,
          text: formatBinaryLabel(image.effective_ground_truth),
        }),
      );
      tr.appendChild(gtTd);

      if (!state.selectedRunId) {
        tr.appendChild(el("td", { className: "muted", text: "—" }));
        tr.appendChild(el("td", { className: "muted", text: "—" }));
        tr.appendChild(el("td", { className: "muted", text: "—" }));
      } else if (state.loading) {
        tr.appendChild(el("td", { className: "muted", text: "Loading…" }));
        tr.appendChild(el("td", { className: "muted", text: "…" }));
        tr.appendChild(el("td", { className: "muted", text: "…" }));
      } else if (state.runLoadError || !state.runDetail) {
        tr.appendChild(el("td", { className: "muted", text: "Load failed" }));
        tr.appendChild(el("td", { className: "muted", text: "—" }));
        tr.appendChild(el("td", { className: "muted", text: "—" }));
      } else {
        const pred = findPrediction(image.image_id);
        if (!pred || pred.available !== true) {
          tr.appendChild(el("td", { text: NO_PREDICTION }));
          tr.appendChild(el("td", { text: "—" }));
          tr.appendChild(el("td", { text: "—" }));
        } else {
          tr.appendChild(el("td", { text: formatBinaryLabel(pred.predicted_label) }));
          const prob = formatProbability(pred.positive_class_probability);
          tr.appendChild(el("td", { text: prob === null ? "—" : prob }));
          const descTd = el("td");
          const desc = el("div", { className: "cell-clamp" });
          desc.appendChild(
            document.createTextNode(
              pred.description == null || pred.description === "" ? "—" : String(pred.description),
            ),
          );
          descTd.appendChild(desc);
          tr.appendChild(descTd);
        }
      }

      const commentsTd = el("td");
      const comments = el("div", { className: "cell-clamp" });
      comments.appendChild(
        document.createTextNode(
          image.effective_comments == null || image.effective_comments === ""
            ? "—"
            : String(image.effective_comments),
        ),
      );
      commentsTd.appendChild(comments);
      tr.appendChild(commentsTd);

      const actionTd = el("td");
      const inspect = el("button", {
        type: "button",
        className: "btn btn-secondary btn-sm",
        text: "Inspect",
      });
      inspect.addEventListener("click", () => focusCard(image.image_id));
      actionTd.appendChild(inspect);
      tr.appendChild(actionTd);

      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    dom.summaryTableWrap.appendChild(table);
  }

  /**
   * @param {any} image
   * @param {string} q
   */
  function summaryRowMatches(image, q) {
    if (!q) return true;
    const pred =
      state.selectedRunId && !state.loading && !state.runLoadError && state.runDetail
        ? findPrediction(image.image_id)
        : null;
    const predLabel =
      !state.selectedRunId
        ? ""
        : state.loading
          ? "loading"
          : state.runLoadError || !state.runDetail
            ? "load failed"
            : pred && pred.available === true
              ? formatBinaryLabel(pred.predicted_label)
              : NO_PREDICTION;
    const parts = [
      image.image_id,
      formatBinaryLabel(image.effective_ground_truth),
      image.effective_comments,
      predLabel,
      pred && pred.available === true ? pred.description : "",
      pred && pred.available === true ? formatProbability(pred.positive_class_probability) : "",
    ];
    return parts
      .filter((p) => p != null && p !== "")
      .map((p) => String(p).toLowerCase())
      .some((p) => p.includes(q));
  }

  // ---------------------------------------------------------------------------
  // Executive summary
  // ---------------------------------------------------------------------------

  function renderExecutive() {
    if (!dom.executiveContent) return;
    clearChildren(dom.executiveContent);
    updateDraftNotices();
    syncSummaryLoadBars();

    if (state.loading) {
      dom.executiveContent.appendChild(
        el("div", {
          className: "empty-state",
          text: state.selectedRunId
            ? `Loading summary for run ${state.selectedRunId}…`
            : "Loading dataset summary…",
        }),
      );
      return;
    }

    if (isIntervalBrowse() && state.summaryLoading) {
      dom.executiveContent.appendChild(
        el("div", {
          className: "empty-state",
          text: "Loading executive summary for active videos…",
        }),
      );
      return;
    }
    if (isIntervalBrowse() && state.summaryError && (!state.summaryLoaded || !state.summary)) {
      const errBox = el("div", { className: "empty-state" });
      errBox.appendChild(el("p", { className: "save-error", text: state.summaryError }));
      const retry = el("button", {
        type: "button",
        className: "btn btn-secondary",
        text: "Retry load executive summary",
      });
      retry.addEventListener("click", () => loadSummaryExplicit({ force: true }));
      errBox.appendChild(retry);
      dom.executiveContent.appendChild(errBox);
      return;
    }
    if (isIntervalBrowse() && (!state.summaryLoaded || !state.summary)) {
      dom.executiveContent.appendChild(
        el("div", {
          className: "empty-state",
          text: "Executive summary requires the effective summary scan. Use “Load executive summary” — counts cover active CSV videos only and are not guessed from original dataset labels alone.",
        }),
      );
      return;
    }

    if (state.runLoadError) {
      const box = el("div", { className: "empty-state" });
      box.appendChild(
        el("p", {
          text: state.selectedRunId
            ? `Failed to load run ${state.selectedRunId}: ${state.runLoadError}`
            : `Failed to load dataset-only summary: ${state.runLoadError}`,
        }),
      );
      box.appendChild(
        el("p", {
          className: "muted",
          text: "Previous run metrics are cleared. Use Retry to load the selected run again.",
        }),
      );
      const retry = el("button", {
        type: "button",
        className: "btn btn-secondary retry-btn",
        text: "Retry",
      });
      retry.addEventListener("click", () => selectRun(state.selectedRunId, { force: true }));
      box.appendChild(retry);
      dom.executiveContent.appendChild(box);
      return;
    }

    if (!state.summary) {
      dom.executiveContent.appendChild(
        el("div", {
          className: "empty-state",
          text: "No summary available.",
        }),
      );
      return;
    }

    const summary = state.summary;
    const overview = el("section", { className: "exec-card" });
    overview.appendChild(el("h3", { text: "Dataset overview" }));
    const stats = el("div", { className: "stat-grid" });
    stats.appendChild(statBlock("Total images", String(summary.total_images)));
    stats.appendChild(
      statBlock(
        "Ground truth 0",
        String(summary.effective_ground_truth && summary.effective_ground_truth.label_0),
      ),
    );
    stats.appendChild(
      statBlock(
        "Ground truth 1",
        String(summary.effective_ground_truth && summary.effective_ground_truth.label_1),
      ),
    );
    overview.appendChild(stats);

    const gt0 = summary.effective_ground_truth ? summary.effective_ground_truth.label_0 : 0;
    const gt1 = summary.effective_ground_truth ? summary.effective_ground_truth.label_1 : 0;
    const total = gt0 + gt1;
    const bar = el("div", {
      className: "dist-bar",
      role: "img",
      "aria-label": `Ground-truth distribution: ${gt0} absent, ${gt1} present`,
    });
    if (total === 0) {
      bar.appendChild(el("div", { className: "dist-seg seg-0", style: "width:100%", text: "Empty" }));
    } else {
      if (gt0 > 0) {
        const seg = el("div", { className: "dist-seg seg-0", text: String(gt0) });
        seg.style.width = `${(gt0 / total) * 100}%`;
        bar.appendChild(seg);
      }
      if (gt1 > 0) {
        const seg = el("div", { className: "dist-seg seg-1", text: String(gt1) });
        seg.style.width = `${(gt1 / total) * 100}%`;
        bar.appendChild(seg);
      }
    }
    overview.appendChild(bar);
    const legend = el("div", { className: "dist-legend" });
    legend.appendChild(document.createTextNode(`${LABEL_ABSENT}: ${gt0}`));
    legend.appendChild(document.createTextNode(`${LABEL_PRESENT}: ${gt1}`));
    overview.appendChild(legend);
    dom.executiveContent.appendChild(overview);

    // Prediction coverage / mode
    const predCard = el("section", { className: "exec-card" });
    predCard.appendChild(el("h3", { text: "Selected run & predictions" }));
    if (!summary.run_id) {
      predCard.appendChild(
        el("p", {
          text: "Dataset-only view — no run is selected, so prediction coverage and historical metrics are not shown.",
        }),
      );
    } else {
      predCard.appendChild(el("p", { text: `Run: ${summary.run_id}` }));
      const coverage = summary.prediction_coverage;
      if (!coverage) {
        predCard.appendChild(el("p", { text: "Prediction coverage is unavailable." }));
      } else {
        const grid = el("div", { className: "stat-grid" });
        grid.appendChild(statBlock("With prediction", String(coverage.with_prediction)));
        grid.appendChild(statBlock("Without prediction", String(coverage.without_prediction)));
        grid.appendChild(statBlock("Predicted 0", String(coverage.predicted_label_0)));
        grid.appendChild(statBlock("Predicted 1", String(coverage.predicted_label_1)));
        predCard.appendChild(grid);
        if (coverage.with_prediction === 0) {
          predCard.appendChild(
            el("p", {
              className: "muted",
              text: "This run has no predictions for the dataset images.",
            }),
          );
        }
      }
    }
    dom.executiveContent.appendChild(predCard);

    // Historical metrics
    const metricsCard = el("section", { className: "exec-card" });
    metricsCard.appendChild(el("h3", { text: "Historical evaluation metrics" }));
    const metrics = summary.historical_metrics;

    if (!summary.run_id) {
      metricsCard.appendChild(
        el("p", { text: "Select a run to inspect published evaluation metrics." }),
      );
    } else if (!metrics || metrics.available !== true) {
      metricsCard.appendChild(
        el("p", {
          text: "Predictions may be available, but this run has no published evaluation metrics.",
        }),
      );
    } else {
      const grid = el("div", { className: "metrics-grid" });
      grid.appendChild(statBlock("Accuracy", formatMetric(metrics.accuracy)));
      grid.appendChild(statBlock("Precision", formatMetric(metrics.precision)));
      grid.appendChild(statBlock("Recall", formatMetric(metrics.recall)));
      grid.appendChild(statBlock("F1", formatMetric(metrics.f1)));
      grid.appendChild(
        statBlock(
          "Evaluated images",
          metrics.evaluated_image_count == null ? "N/A" : String(metrics.evaluated_image_count),
        ),
      );
      metricsCard.appendChild(grid);
      metricsCard.appendChild(el("p", { className: "metrics-footnote", text: METRICS_SNAPSHOT_NOTE }));

      if (metrics.confusion_matrix && Array.isArray(metrics.confusion_matrix.labels)) {
        metricsCard.appendChild(el("h3", { text: "Confusion matrix" }));
        metricsCard.appendChild(
          el("p", {
            className: "muted",
            text: "Rows: ground truth. Columns: predictions.",
          }),
        );
        metricsCard.appendChild(buildConfusionMatrix(metrics.confusion_matrix));
      }

      const drift = currentLabelsDifferFromSnapshot(metrics);
      if (drift) {
        const notice = el("div", { className: "notice", "data-kind": "warning" });
        notice.appendChild(
          document.createTextNode(
            "Current persisted ground-truth labels differ from this run’s evaluation snapshot. Historical metrics are unchanged.",
          ),
        );
        metricsCard.appendChild(notice);
      }
    }
    dom.executiveContent.appendChild(metricsCard);
  }

  /** @param {string} label @param {string} value */
  function statBlock(label, value) {
    const node = el("div", { className: "stat" });
    node.appendChild(el("span", { className: "stat-label", text: label }));
    node.appendChild(el("span", { className: "stat-value", text: value }));
    return node;
  }

  /** @param {any} cm */
  function buildConfusionMatrix(cm) {
    const table = el("table", { className: "cm-table" });
    const labels = cm.labels;
    const matrix = cm.matrix;
    const thead = el("thead");
    const head = el("tr");
    head.appendChild(el("th", { text: "GT \\ Pred" }));
    for (const label of labels) {
      head.appendChild(el("th", { text: formatBinaryLabel(label) }));
    }
    thead.appendChild(head);
    table.appendChild(thead);
    const tbody = el("tbody");
    for (let r = 0; r < labels.length; r += 1) {
      const tr = el("tr");
      tr.appendChild(el("th", { text: formatBinaryLabel(labels[r]), scope: "row" }));
      const row = Array.isArray(matrix[r]) ? matrix[r] : [];
      for (let c = 0; c < labels.length; c += 1) {
        tr.appendChild(el("td", { text: String(row[c]) }));
      }
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    return table;
  }

  /** @param {any} metrics */
  function currentLabelsDifferFromSnapshot(metrics) {
    if (!metrics || !metrics.evaluation_snapshot || !state.datasetDetail) return false;
    const evaluated = metrics.evaluation_snapshot.evaluated_images;
    if (!Array.isArray(evaluated)) return false;
    for (const item of evaluated) {
      const image = findImage(item.image_id);
      if (!image) continue;
      if (image.effective_ground_truth !== item.ground_truth) return true;
    }
    return false;
  }

  // ---------------------------------------------------------------------------
  // Image viewer (zoom / pan)
  // ---------------------------------------------------------------------------

  /**
   * @param {string} imageId
   * @param {HTMLElement} [trigger]
   */
  function openViewer(imageId, trigger) {
    const identity = currentDatasetIdentity();
    if (!identity) return;
    state.viewer.open = true;
    state.viewer.imageId = imageId;
    clearChildren(dom.viewerTitle);
    dom.viewerTitle.appendChild(document.createTextNode(`Image: ${imageId}`));
    dom.viewerError.hidden = true;
    dom.viewerImage.hidden = true;
    dom.viewerImage.removeAttribute("src");
    openModal(dom.viewerModal, trigger || null);

    const url = imageContentUrl(
      identity.datasetId,
      identity.datasetVersion,
      imageId,
      videoIdForImage(imageId),
    );
    dom.viewerImage.onload = () => {
      state.viewer.naturalWidth = dom.viewerImage.naturalWidth;
      state.viewer.naturalHeight = dom.viewerImage.naturalHeight;
      dom.viewerImage.hidden = false;
      dom.viewerError.hidden = true;
      fitViewer();
    };
    dom.viewerImage.onerror = () => {
      dom.viewerImage.hidden = true;
      dom.viewerError.hidden = false;
    };
    dom.viewerImage.src = url;
    dom.viewerStage.focus();
  }

  function closeViewer() {
    state.viewer.open = false;
    state.viewer.panning = false;
    dom.viewerImage.removeAttribute("src");
    closeModal(dom.viewerModal);
  }

  function fitViewer() {
    const stage = dom.viewerStage;
    const nw = state.viewer.naturalWidth;
    const nh = state.viewer.naturalHeight;
    if (!nw || !nh) return;
    const fit = Math.min(stage.clientWidth / nw, stage.clientHeight / nh);
    state.viewer.fitScale = fit > 0 ? fit : 1;
    state.viewer.scale = state.viewer.fitScale;
    centerViewer();
    applyViewerTransform();
  }

  function setViewerScale(scale, anchorX, anchorY) {
    const stage = dom.viewerStage;
    const prev = state.viewer.scale;
    const next = Math.min(32, Math.max(0.05, scale));
    if (!Number.isFinite(next) || next === prev) {
      applyViewerTransform();
      return;
    }
    const rect = stage.getBoundingClientRect();
    const ax = anchorX == null ? rect.width / 2 : anchorX;
    const ay = anchorY == null ? rect.height / 2 : anchorY;
    const imageX = (ax - state.viewer.offsetX) / prev;
    const imageY = (ay - state.viewer.offsetY) / prev;
    state.viewer.scale = next;
    state.viewer.offsetX = ax - imageX * next;
    state.viewer.offsetY = ay - imageY * next;
    applyViewerTransform();
  }

  function centerViewer() {
    const stage = dom.viewerStage;
    const w = state.viewer.naturalWidth * state.viewer.scale;
    const h = state.viewer.naturalHeight * state.viewer.scale;
    state.viewer.offsetX = (stage.clientWidth - w) / 2;
    state.viewer.offsetY = (stage.clientHeight - h) / 2;
  }

  function applyViewerTransform() {
    const { scale, offsetX, offsetY } = state.viewer;
    dom.viewerImage.style.transform = `translate(${offsetX}px, ${offsetY}px) scale(${scale})`;
    clearChildren(dom.viewerZoomLabel);
    const pct = Math.round(scale * 100);
    dom.viewerZoomLabel.appendChild(document.createTextNode(`${pct}%`));
  }

  // ---------------------------------------------------------------------------
  // Modal focus management
  // ---------------------------------------------------------------------------

  /**
   * @param {HTMLElement | null} modal
   * @param {HTMLElement | null} trigger
   */
  function openModal(modal, trigger) {
    if (!modal) return;
    state.lastFocus = trigger || /** @type {HTMLElement | null} */ (document.activeElement);
    modal.hidden = false;
    document.body.style.overflow = "hidden";
  }

  /** @param {HTMLElement | null} modal */
  function closeModal(modal) {
    if (!modal) return;
    modal.hidden = true;
    if (
      dom.pickerModal &&
      dom.pickerModal.hidden &&
      dom.viewerModal &&
      dom.viewerModal.hidden
    ) {
      document.body.style.overflow = "";
    }
    if (state.lastFocus && typeof state.lastFocus.focus === "function") {
      state.lastFocus.focus();
    }
    state.lastFocus = null;
  }

  /** @param {HTMLElement} modal */
  function focusables(modal) {
    return Array.from(
      modal.querySelectorAll(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
    ).filter((node) => node instanceof HTMLElement && !node.closest("[hidden]"));
  }

  // ---------------------------------------------------------------------------
  // Events
  // ---------------------------------------------------------------------------

  function bindEvents() {
    dom.datasetSelect.addEventListener("change", () => {
      selectDataset(dom.datasetSelect.value);
    });
    dom.runSelect.addEventListener("change", () => {
      const value = dom.runSelect.value;
      selectRun(value === "" ? null : value);
    });

    for (const tab of dom.tabs) {
      tab.addEventListener("click", () => {
        const name = tab.getAttribute("data-tab");
        if (name === "analytical" || name === "summary" || name === "executive") {
          setActiveTab(name);
        }
      });
      tab.addEventListener("keydown", (event) => {
        const keys = ["ArrowLeft", "ArrowRight", "Home", "End"];
        if (!keys.includes(event.key)) return;
        event.preventDefault();
        const order = /** @type {const} */ (["analytical", "summary", "executive"]);
        let idx = order.indexOf(state.activeTab);
        if (event.key === "ArrowLeft") idx = (idx + order.length - 1) % order.length;
        if (event.key === "ArrowRight") idx = (idx + 1) % order.length;
        if (event.key === "Home") idx = 0;
        if (event.key === "End") idx = order.length - 1;
        setActiveTab(order[idx]);
        const next = document.getElementById(`tab-${order[idx]}`);
        if (next) next.focus();
      });
    }

    dom.addFramesBtn.addEventListener("click", openPicker);
    dom.pickerSearch.addEventListener("input", () => {
      state.pickerSearch = dom.pickerSearch.value;
      if (isIntervalBrowse()) {
        scheduleIntervalPickerSearch();
      } else {
        renderPicker();
      }
    });
    dom.pickerSearch.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      if (!(isIntervalBrowse() && state.datasetLayout === "video_catalog")) return;
      event.preventDefault();
      runExplicitImageSearch();
    });
    if (dom.pickerSearchBtn) {
      dom.pickerSearchBtn.addEventListener("click", () => {
        runExplicitImageSearch();
      });
    }
    dom.pickerAddBtn.addEventListener("click", () => {
      if (isIntervalBrowse()) {
        void addSelectedIntervalsFromPicker();
        return;
      }
      addCards(Array.from(state.pickerSelected));
      closeModal(dom.pickerModal);
    });
    if (dom.pickerAddAllBtn) {
      dom.pickerAddAllBtn.addEventListener("click", () => {
        void addAllMatchingIntervalsFromPicker();
      });
    }
    if (dom.pickerPrevPage) {
      dom.pickerPrevPage.addEventListener("click", () => {
        state.pickerOffset = Math.max(0, state.pickerOffset - PICKER_PAGE_SIZE);
        const trigger =
          state.datasetLayout === "video_catalog" && state.pickerExplicitImageSearch
            ? "explicit"
            : "type";
        void loadIntervalPickerPage({ trigger });
      });
    }
    if (dom.pickerNextPage) {
      dom.pickerNextPage.addEventListener("click", () => {
        state.pickerOffset += PICKER_PAGE_SIZE;
        const trigger =
          state.datasetLayout === "video_catalog" && state.pickerExplicitImageSearch
            ? "explicit"
            : "type";
        void loadIntervalPickerPage({ trigger });
      });
    }

    document.querySelectorAll("[data-close='picker']").forEach((node) => {
      node.addEventListener("click", () => closeModal(dom.pickerModal));
    });
    document.querySelectorAll("[data-close='viewer']").forEach((node) => {
      node.addEventListener("click", () => closeViewer());
    });

    dom.summarySearch.addEventListener("input", () => {
      state.summarySearch = dom.summarySearch.value;
      renderSummary();
    });
    if (dom.summaryLoadBtn) {
      dom.summaryLoadBtn.addEventListener("click", () => loadSummaryExplicit({ force: true }));
    }
    if (dom.executiveLoadBtn) {
      dom.executiveLoadBtn.addEventListener("click", () => loadSummaryExplicit({ force: true }));
    }

    dom.viewerFit.addEventListener("click", () => fitViewer());
    dom.viewer100.addEventListener("click", () => {
      state.viewer.scale = 1;
      centerViewer();
      applyViewerTransform();
    });
    dom.viewerZoomIn.addEventListener("click", () => setViewerScale(state.viewer.scale * 1.25));
    dom.viewerZoomOut.addEventListener("click", () => setViewerScale(state.viewer.scale / 1.25));
    dom.viewerReset.addEventListener("click", () => fitViewer());

    dom.viewerStage.addEventListener(
      "wheel",
      (event) => {
        if (!state.viewer.open) return;
        event.preventDefault();
        const rect = dom.viewerStage.getBoundingClientRect();
        const factor = event.deltaY < 0 ? 1.1 : 1 / 1.1;
        setViewerScale(
          state.viewer.scale * factor,
          event.clientX - rect.left,
          event.clientY - rect.top,
        );
      },
      { passive: false },
    );

    dom.viewerStage.addEventListener("pointerdown", (event) => {
      if (!state.viewer.open) return;
      state.viewer.panning = true;
      state.viewer.panStartX = event.clientX;
      state.viewer.panStartY = event.clientY;
      state.viewer.originOffsetX = state.viewer.offsetX;
      state.viewer.originOffsetY = state.viewer.offsetY;
      dom.viewerStage.classList.add("is-panning");
      dom.viewerStage.setPointerCapture(event.pointerId);
    });
    dom.viewerStage.addEventListener("pointermove", (event) => {
      if (!state.viewer.panning) return;
      state.viewer.offsetX = state.viewer.originOffsetX + (event.clientX - state.viewer.panStartX);
      state.viewer.offsetY = state.viewer.originOffsetY + (event.clientY - state.viewer.panStartY);
      applyViewerTransform();
    });
    const endPan = (event) => {
      if (!state.viewer.panning) return;
      state.viewer.panning = false;
      dom.viewerStage.classList.remove("is-panning");
      try {
        dom.viewerStage.releasePointerCapture(event.pointerId);
      } catch {
        /* ignore */
      }
    };
    dom.viewerStage.addEventListener("pointerup", endPan);
    dom.viewerStage.addEventListener("pointercancel", endPan);

    window.addEventListener("resize", () => {
      if (state.viewer.open && !dom.viewerImage.hidden) fitViewer();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (state.viewer.open) {
        event.preventDefault();
        closeViewer();
        return;
      }
      if (dom.pickerModal && !dom.pickerModal.hidden) {
        event.preventDefault();
        closeModal(dom.pickerModal);
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Tab") return;
      const open =
        (dom.viewerModal && !dom.viewerModal.hidden && dom.viewerModal) ||
        (dom.pickerModal && !dom.pickerModal.hidden && dom.pickerModal);
      if (!open) return;
      const nodes = focusables(open);
      if (nodes.length === 0) return;
      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });

    window.addEventListener("beforeunload", (event) => {
      if (!hasAnyUnresolvedWork()) return;
      event.preventDefault();
      event.returnValue = "";
    });

  }

  // ---------------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------------

  bindEvents();
  setActiveTab("analytical");
  bootstrap();
})();
