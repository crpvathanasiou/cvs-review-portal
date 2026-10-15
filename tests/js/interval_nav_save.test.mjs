/**
 * Delayed-response / navigation regressions against production interval_browse_logic.mjs
 * (the same module wired into app.js).
 */
import assert from "node:assert/strict";
import test from "node:test";

import {
  batchAddStillValid,
  executeAddOrFocusInterval,
  executeEnsureIntervalFrames,
  executeLoadIntervalFrame,
  imageCacheKey,
  intervalFrameLoadStillValid,
  nextFrameIndex,
  pickerRequestStillValid,
  reconcileFrameImage,
} from "../../src/cvs_review_portal/web/interval_browse_logic.mjs";
import {
  executeSaveComment,
  saveContinuationValid,
} from "../../src/cvs_review_portal/web/review_save_logic.mjs";

function draftKey(datasetId, version, imageId) {
  return `${datasetId}\0${version}\0${imageId}`;
}

function makeImage(imageId, revision, comments) {
  return {
    image_id: imageId,
    persisted_revision: revision,
    effective_comments: comments,
    original_comments: comments,
    effective_ground_truth: 0,
    original_ground_truth: 0,
    review:
      revision > 0
        ? {
            comments,
            revision,
            actor: "tester",
            updated_at: "2026-01-01T00:00:00+00:00",
            ground_truth_override: null,
          }
        : null,
  };
}

function makeHarness(options = {}) {
  const datasetId = options.datasetId || "ds-a";
  const datasetVersion = options.datasetVersion || "v1";
  let selectionGen = 1;
  let selectedRunId = options.runId ?? null;
  let cardSeq = 0;
  const openIntervals = [];
  const imageCache = new Map();
  const frameResolvers = [];
  const framesBySegment = options.framesBySegment || {
    "seg-shared": [
      { image_id: "img-1", frame_index: 1, display_id: "disp-1", position: 1 },
      { image_id: "img-2", frame_index: 2, display_id: "disp-2", position: 2 },
    ],
  };
  const viewByImage = options.viewByImage || {
    "img-1": {
      image: makeImage("img-1", 0, ""),
      display_id: "disp-1",
      prediction: null,
    },
    "img-2": {
      image: makeImage("img-2", 0, "b"),
      display_id: "disp-2",
      prediction: null,
    },
  };

  const updatedCards = [];
  const predictionUpdatedCards = [];

  const state = {
    get datasetId() {
      return datasetIdRef.value;
    },
    set datasetId(v) {
      datasetIdRef.value = v;
    },
    datasetVersion,
    get selectionGen() {
      return selectionGen;
    },
    bumpSelectionGen() {
      selectionGen += 1;
    },
    get selectedRunId() {
      return selectedRunId;
    },
    set selectedRunId(v) {
      selectedRunId = v;
    },
    openIntervals,
    imageCache,
    drafts: new Map(),
    saves: new Map(),
    updatedCards,
    predictionUpdatedCards,
  };

  const datasetIdRef = { value: datasetId };

  function findOpenInterval(segmentId) {
    return openIntervals.find((item) => item.segmentId === segmentId) || null;
  }
  function findOpenIntervalByCardId(cardId) {
    return openIntervals.find((item) => item.cardId === cardId) || null;
  }

  const deps = {
    currentIdentity: () =>
      datasetIdRef.value
        ? { datasetId: datasetIdRef.value, datasetVersion: state.datasetVersion }
        : null,
    selectedRunId: () => selectedRunId,
    selectionGen: () => selectionGen,
    findOpenInterval,
    findOpenIntervalByCardId,
    getCachedImage: (d, v, imageId) => imageCache.get(imageCacheKey(d, v, imageId)) || null,
    setCachedImage: (d, v, imageId, image) => {
      imageCache.set(imageCacheKey(d, v, imageId), image);
    },
    fetchFrameView: ({ imageId, runId }) =>
      new Promise((resolve, reject) => {
        frameResolvers.push({ imageId, runId, resolve, reject });
      }),
    fetchIntervalFrames: async ({ segmentId }) => ({
      frames: framesBySegment[segmentId] || [],
      title: `Title ${segmentId}`,
      image_count: (framesBySegment[segmentId] || []).length,
    }),
    ensureIntervalFrames: (cardId) => executeEnsureIntervalFrames(deps, cardId),
    loadIntervalFrame: (segmentId, frameIndex, opts) =>
      executeLoadIntervalFrame(deps, segmentId, frameIndex, opts),
    createOpenIntervalCard: ({ segmentId, title, imageCount }) => {
      cardSeq += 1;
      return {
        cardId: `card-${cardSeq}`,
        segmentId,
        title,
        imageCount,
        frames: null,
        currentIndex: 0,
        currentImage: null,
        displayId: null,
        prediction: null,
        loadGen: 0,
        status: "loading",
        errorMessage: null,
      };
    },
    appendIntervalCard: (card) => {
      openIntervals.push(card);
    },
    setActiveTabAnalytical: () => {},
    focusIntervalCard: () => {},
    onCardLoading: (open) => updatedCards.push({ type: "loading", cardId: open.cardId }),
    onCardUpdated: (open) => updatedCards.push({ type: "updated", cardId: open.cardId, open }),
    onCardPredictionPending: () => {},
    onCardPredictionUpdated: (open) =>
      predictionUpdatedCards.push({ cardId: open.cardId, imageId: open.currentImage.image_id }),
    onPredictionError: () => {},
    errorMessage: (err) => (err && err.message) || "error",
  };

  function resolveNextView(mutator) {
    const next = frameResolvers.shift();
    if (!next) throw new Error("no pending frame request");
    const source = viewByImage[next.imageId];
    const base = {
      image: { ...source.image, review: source.image.review ? { ...source.image.review } : null },
      display_id: source.display_id,
      prediction: source.prediction,
    };
    if (next.runId) {
      base.prediction = {
        available: true,
        predicted_label: 1,
        positive_class_probability: 0.9,
        description: `run:${next.runId}`,
      };
    }
    if (mutator) mutator(base, next);
    next.resolve(base);
    return next;
  }

  async function flushMicrotasks() {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  }

  return {
    state,
    deps,
    resolveNextView,
    frameResolvers,
    findOpenInterval,
    findOpenIntervalByCardId,
    flushMicrotasks,
  };
}

test("nextFrameIndex refuses wraparound (production)", () => {
  assert.equal(nextFrameIndex(0, -1, 3), null);
  assert.equal(nextFrameIndex(2, 1, 3), null);
  assert.equal(nextFrameIndex(1, 1, 3), 2);
});

test("dataset A then B with same segment ID drops delayed A response", async () => {
  const a = makeHarness({ datasetId: "ds-a" });
  const addA = executeAddOrFocusInterval(a.deps, "seg-shared", { title: "A" });
  await a.flushMicrotasks();
  assert.equal(a.frameResolvers.length, 1);
  const pendingA = a.frameResolvers[0];

  // Switch dataset identity (same segment id exists conceptually on B).
  a.state.datasetId = "ds-b";
  a.state.bumpSelectionGen();
  a.state.openIntervals.length = 0;
  a.state.imageCache.clear();

  const b = makeHarness({ datasetId: "ds-b" });
  const addB = executeAddOrFocusInterval(b.deps, "seg-shared", { title: "B" });
  await b.flushMicrotasks();
  b.resolveNextView();
  await addB;
  const bCard = b.findOpenInterval("seg-shared");
  assert.ok(bCard);
  assert.equal(bCard.currentImage.image_id, "img-1");

  // Late A response must not apply (identity / card gone).
  pendingA.resolve({
    image: makeImage("img-1", 0, "from-A"),
    display_id: "disp-1",
    prediction: null,
  });
  const outcomeA = await addA;
  assert.equal(outcomeA.outcome, "stale");
  assert.equal(bCard.currentImage.effective_comments, "");
});

test("remove/reopen while earlier request pending isolates card instances", async () => {
  const h = makeHarness();
  const first = executeAddOrFocusInterval(h.deps, "seg-shared", {});
  await h.flushMicrotasks();
  assert.equal(h.frameResolvers.length, 1);
  const oldReq = h.frameResolvers[0];
  const oldCardId = h.findOpenInterval("seg-shared").cardId;

  // Remove card instance (production drops the cardId from openIntervals).
  h.state.openIntervals.length = 0;

  const second = executeAddOrFocusInterval(h.deps, "seg-shared", {});
  await h.flushMicrotasks();
  const newCard = h.findOpenInterval("seg-shared");
  assert.ok(newCard);
  assert.notEqual(newCard.cardId, oldCardId);
  assert.equal(h.frameResolvers.length, 2);
  // Resolve only the new card's pending fetch (last queued).
  const newReq = h.frameResolvers[1];
  newReq.resolve({
    image: makeImage("img-1", 0, ""),
    display_id: "disp-1",
    prediction: null,
  });
  await second;
  assert.equal(newCard.currentImage.image_id, "img-1");
  assert.equal(newCard.currentImage.effective_comments, "");

  oldReq.resolve({
    image: makeImage("img-1", 0, "stale-old-card"),
    display_id: "disp-1",
    prediction: null,
  });
  const firstOutcome = await first;
  assert.equal(firstOutcome.outcome, "stale");
  assert.equal(newCard.currentImage.effective_comments, "");
});

test("run switch invalidates outdated prediction-bearing frame request", async () => {
  const h = makeHarness({ runId: "run-1" });
  const opened = executeAddOrFocusInterval(h.deps, "seg-shared", {});
  await h.flushMicrotasks();
  h.resolveNextView();
  await opened;

  const open = h.findOpenInterval("seg-shared");
  const pending = executeLoadIntervalFrame(h.deps, "seg-shared", 0, {
    predictionRefresh: true,
  });
  await h.flushMicrotasks();
  assert.equal(h.frameResolvers.length, 1);
  assert.equal(h.frameResolvers[0].runId, "run-1");

  h.state.selectedRunId = "run-2";
  h.frameResolvers[0].resolve({
    image: makeImage("img-1", 0, ""),
    display_id: "disp-1",
    prediction: {
      available: true,
      predicted_label: 0,
      description: "stale-run-1",
    },
  });
  const priorPrediction = open.prediction;
  assert.ok(priorPrediction);
  assert.equal(priorPrediction.description, "run:run-1");
  const outcome = await pending;
  assert.equal(outcome.outcome, "stale");
  // Stale response must not overwrite; prior prediction remains until a valid refresh.
  assert.equal(open.prediction, priorPrediction);
  assert.equal(open.prediction.description, "run:run-1");
});

test("Save revision 2 is not rolled back by older frame GET revision 1", async () => {
  const h = makeHarness();
  const add = executeAddOrFocusInterval(h.deps, "seg-shared", {});
  await h.flushMicrotasks();
  h.resolveNextView((view) => {
    view.image = makeImage("img-1", 0, "");
  });
  await add;
  const open = h.findOpenInterval("seg-shared");
  assert.equal(open.currentImage.persisted_revision, 0);

  // Successful Save → revision 2 in cache + card.
  const key = draftKey("ds-a", "v1", "img-1");
  h.state.drafts.set(key, { comments: "saved-v2" });
  const saveDeps = {
    saves: h.state.saves,
    drafts: h.state.drafts,
    currentIdentity: h.deps.currentIdentity,
    draftKey,
    findImage: (id) => {
      const identity = h.deps.currentIdentity();
      return h.deps.getCachedImage(identity.datasetId, identity.datasetVersion, id);
    },
    effectiveDraft: (img) => {
      const d = h.state.drafts.get(draftKey("ds-a", "v1", img.image_id));
      return { comments: d ? d.comments : img.effective_comments || "" };
    },
    baseRevision: (img) => img.persisted_revision || 0,
    putReview: async () => ({
      current: {
        comments: "saved-v2",
        revision: 2,
        actor: "tester",
        updated_at: "2026-01-01T00:00:00+00:00",
        ground_truth_override: null,
      },
      persisted_revision: 2,
    }),
    getReview: async () => {
      throw new Error("unexpected");
    },
    reviewUrl: (d, v, i) => `/api/datasets/${d}/versions/${v}/images/${i}/review`,
    errorMessage: (err) => err.message,
    applyPersistedReview: (args) => {
      const img = makeImage(args.imageId, args.persistedRevision, args.review.comments);
      h.deps.setCachedImage(args.datasetId, args.datasetVersion, args.imageId, img);
      open.currentImage = img;
      return true;
    },
    refreshSummary: async () => {},
    onOpChanged: () => {},
    maxCommentLength: 8000,
  };
  const saved = await executeSaveComment(saveDeps, "img-1");
  assert.equal(saved.outcome, "saved");
  assert.equal(open.currentImage.persisted_revision, 2);
  assert.equal(open.currentImage.effective_comments, "saved-v2");

  // Older in-flight frame GET (revision 1) must not overwrite.
  const late = executeLoadIntervalFrame(h.deps, "seg-shared", 0, {});
  await h.flushMicrotasks();
  h.resolveNextView((view) => {
    view.image = makeImage("img-1", 1, "older-server");
  });
  const lateOutcome = await late;
  assert.equal(lateOutcome.outcome, "loaded");
  assert.equal(lateOutcome.rolledBackReview, true);
  assert.equal(open.currentImage.persisted_revision, 2);
  assert.equal(open.currentImage.effective_comments, "saved-v2");
  // Draft map remains independent (cleared on successful Save).
  assert.equal(h.state.drafts.has(key), false);
});

test("dataset switch during batch add stops further card additions", async () => {
  const h = makeHarness();
  let activeBatchId = 1;
  const token = {
    datasetId: "ds-a",
    datasetVersion: "v1",
    selectionGen: 1,
    batchId: 1,
  };
  const deps = {
    currentIdentity: () =>
      h.state.datasetId
        ? { datasetId: h.state.datasetId, datasetVersion: "v1" }
        : null,
    selectionGen: () => h.state.selectionGen,
    activeBatchId: () => activeBatchId,
  };
  assert.equal(batchAddStillValid(token, deps), true);
  h.state.datasetId = "ds-b";
  h.state.bumpSelectionGen();
  activeBatchId = 2;
  assert.equal(batchAddStillValid(token, deps), false);
});

test("picker pending search is not actionable for stale results", () => {
  let session = 1;
  let requestId = 2;
  let search = "video02";
  let offset = 0;
  let selectionGen = 1;
  let datasetId = "ds-a";
  const token = {
    datasetId: "ds-a",
    datasetVersion: "v1",
    pickerSession: 1,
    requestId: 1,
    query: "video02",
    offset: 0,
    selectionGen: 1,
  };
  const deps = {
    currentIdentity: () => ({ datasetId, datasetVersion: "v1" }),
    pickerSession: () => session,
    pickerRequestId: () => requestId,
    pickerSearch: () => search,
    pickerOffset: () => offset,
    selectionGen: () => selectionGen,
  };
  assert.equal(pickerRequestStillValid(token, deps), false);
  requestId = 1;
  assert.equal(pickerRequestStillValid(token, deps), true);
  search = "other";
  assert.equal(pickerRequestStillValid(token, deps), false);
});

test("loading another card while typing preserves unaffected textarea node and focus", async () => {
  // Mirrors production targeted replace: only the affected card node is swapped.
  const cards = new Map();
  function mountCard(cardId, comments) {
    const textarea = {
      value: comments,
      selectionStart: 0,
      selectionEnd: 0,
      focus() {
        active = textarea;
      },
      setSelectionRange(start, end) {
        this.selectionStart = start;
        this.selectionEnd = end;
      },
    };
    const article = { cardId, textarea };
    cards.set(cardId, article);
    return article;
  }
  let active = null;
  const left = mountCard("card-1", "typing here");
  left.textarea.focus();
  left.textarea.setSelectionRange(2, 2);
  const leftNode = left.textarea;

  mountCard("card-2", "");
  // Targeted update of card-2 only.
  const replacementTextarea = { value: "loaded" };
  cards.set("card-2", { cardId: "card-2", textarea: replacementTextarea });

  assert.equal(active, leftNode);
  assert.equal(leftNode.value, "typing here");
  assert.equal(leftNode.selectionStart, 2);
  assert.equal(cards.get("card-1").textarea, leftNode);
  assert.notEqual(cards.get("card-2").textarea, leftNode);
});

test("duplicate add focuses existing card rather than creating a second instance", async () => {
  const h = makeHarness();
  const first = executeAddOrFocusInterval(h.deps, "seg-shared", {});
  await h.flushMicrotasks();
  h.resolveNextView();
  await first;
  assert.equal(h.state.openIntervals.length, 1);
  const cardId = h.findOpenInterval("seg-shared").cardId;

  const second = executeAddOrFocusInterval(h.deps, "seg-shared", {
    targetImageId: "img-2",
  });
  await h.flushMicrotasks();
  h.resolveNextView();
  await second;
  assert.equal(h.state.openIntervals.length, 1);
  assert.equal(h.findOpenInterval("seg-shared").cardId, cardId);
  assert.equal(h.findOpenInterval("seg-shared").currentImage.image_id, "img-2");
});

test("Save continuation ignores run selection changes", () => {
  const op = {
    status: "pending",
    datasetId: "ds-a",
    datasetVersion: "v1",
    imageId: "img-1",
  };
  assert.ok(
    saveContinuationValid(op, op, { datasetId: "ds-a", datasetVersion: "v1" }),
  );
});

test("reconcileFrameImage keeps newer persisted review", () => {
  const existing = makeImage("img-1", 2, "new");
  const incoming = makeImage("img-1", 1, "old");
  const result = reconcileFrameImage(existing, incoming);
  assert.equal(result.rolledBackReview, true);
  assert.equal(result.image.persisted_revision, 2);
  assert.equal(result.image.effective_comments, "new");
});

test("intervalFrameLoadStillValid requires matching cardId and dataset", () => {
  const open = {
    cardId: "card-1",
    segmentId: "seg",
    loadGen: 3,
  };
  const token = {
    datasetId: "ds-a",
    datasetVersion: "v1",
    segmentId: "seg",
    cardId: "card-1",
    loadGen: 3,
    frameIndex: 0,
    imageId: "img-1",
    selectedRunId: null,
    selectionGen: 1,
  };
  const deps = {
    currentIdentity: () => ({ datasetId: "ds-a", datasetVersion: "v1" }),
    findOpenIntervalByCardId: (id) => (id === "card-1" ? open : null),
    selectedRunId: () => null,
    selectionGen: () => 1,
  };
  assert.equal(intervalFrameLoadStillValid(token, deps), true);
  deps.currentIdentity = () => ({ datasetId: "ds-b", datasetVersion: "v1" });
  assert.equal(intervalFrameLoadStillValid(token, deps), false);
});
