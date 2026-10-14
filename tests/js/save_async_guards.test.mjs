/**
 * Production Save-state regressions against review_save_logic.mjs.
 */
import assert from "node:assert/strict";
import test from "node:test";

import {
  classifySaveFailure,
  executeSaveComment,
  refreshServerReview,
  saveContinuationValid,
} from "../../src/cvs_review_portal/web/review_save_logic.mjs";

function draftKey(datasetId, version, imageId) {
  return `${datasetId}\0${version}\0${imageId}`;
}

function makeHarness(options = {}) {
  const datasetId = options.datasetId || "ds-a";
  const datasetVersion = options.datasetVersion || "v1";
  const imageId = options.imageId || "img-shared";
  const image = {
    image_id: imageId,
    persisted_revision: options.persistedRevision ?? 0,
    effective_comments: options.comments ?? "",
    original_comments: "",
    review: null,
  };
  const state = {
    datasetId,
    datasetVersion,
    selectionGen: 1,
    selectedRunId: options.runId ?? "run-a",
    images: new Map([[imageId, image]]),
    drafts: new Map(),
    saves: new Map(),
  };
  const putQueue = [];
  const getReviewQueue = [];

  const deps = {
    saves: state.saves,
    drafts: state.drafts,
    currentIdentity: () =>
      state.datasetId
        ? { datasetId: state.datasetId, datasetVersion: state.datasetVersion }
        : null,
    draftKey,
    findImage: (id) => state.images.get(id) || null,
    effectiveDraft: (img) => {
      const key = draftKey(state.datasetId, state.datasetVersion, img.image_id);
      const d = state.drafts.get(key);
      return { comments: d ? d.comments : img.effective_comments || "" };
    },
    baseRevision: (img) => img.persisted_revision || 0,
    putReview: async (url, body) => {
      const next = putQueue.shift();
      if (!next) throw Object.assign(new Error("unexpected put"), { status: 500 });
      return next(url, body);
    },
    getReview: async (url) => {
      const next = getReviewQueue.shift();
      if (!next) throw Object.assign(new Error("unexpected get review"), { status: 500 });
      return next(url);
    },
    reviewUrl: (d, v, i) => `/api/datasets/${d}/versions/${v}/images/${i}/review`,
    errorMessage: (err) => (err && err.message) || "error",
    applyPersistedReview: (args) => {
      if (args.datasetId !== state.datasetId || args.datasetVersion !== state.datasetVersion) {
        return false;
      }
      const img = state.images.get(args.imageId);
      if (!img || !args.review) return false;
      if (args.persistedRevision < img.persisted_revision) return false;
      img.review = args.review;
      img.persisted_revision = args.persistedRevision;
      img.effective_comments = args.review.comments;
      return true;
    },
    refreshSummary: async () => {},
    onOpChanged: () => {},
    maxCommentLength: 8000,
  };

  return {
    state,
    deps,
    putQueue,
    getReviewQueue,
    key: () => draftKey(state.datasetId, state.datasetVersion, imageId),
    imageId,
    switchRun(runId) {
      state.selectionGen += 1;
      state.selectedRunId = runId;
    },
    setDraft(comments) {
      state.drafts.set(draftKey(state.datasetId, state.datasetVersion, imageId), {
        comments,
      });
    },
  };
}

test("pending Save then switch run then success clears pending", async () => {
  const h = makeHarness();
  h.setDraft("hello");
  let resolvePut;
  h.putQueue.push(
    () =>
      new Promise((resolve) => {
        resolvePut = resolve;
      }),
  );
  const pending = executeSaveComment(h.deps, h.imageId);
  assert.equal(h.state.saves.get(h.key()).status, "pending");
  h.switchRun("run-b");
  resolvePut({
    current: { comments: "hello", revision: 1 },
    persisted_revision: 1,
  });
  const result = await pending;
  assert.equal(result.outcome, "saved");
  assert.equal(h.state.saves.has(h.key()), false);
  assert.equal(h.state.images.get(h.imageId).effective_comments, "hello");
});

test("pending Save then switch run then failure preserves draft as unconfirmed", async () => {
  const h = makeHarness();
  h.setDraft("hello");
  let rejectPut;
  h.putQueue.push(
    () =>
      new Promise((_, reject) => {
        rejectPut = reject;
      }),
  );
  const pending = executeSaveComment(h.deps, h.imageId);
  h.switchRun("run-b");
  rejectPut(Object.assign(new Error("timeout"), { status: 0 }));
  const result = await pending;
  assert.equal(result.outcome, "unconfirmed");
  const op = h.state.saves.get(h.key());
  assert.equal(op.status, "unconfirmed");
  assert.equal(op.errorMessage, "Save could not be confirmed");
  assert.equal(h.state.drafts.get(h.key()).comments, "hello");
});

test("first definite 422 leaves draft editable", async () => {
  const h = makeHarness();
  h.setDraft("too-large");
  h.putQueue.push(async () => {
    throw Object.assign(new Error("too large"), { status: 422 });
  });
  const result = await executeSaveComment(h.deps, h.imageId);
  assert.equal(result.outcome, "error");
  assert.equal(h.state.saves.get(h.key()).status, "error");
  h.state.saves.delete(h.key());
  h.setDraft("shorter");
  assert.equal(h.state.drafts.get(h.key()).comments, "shorter");
});

test("unconfirmed refresh loads server comment without resending write", async () => {
  const h = makeHarness();
  h.setDraft("maybe");
  h.putQueue.push(async () => {
    throw Object.assign(new Error("lost"), { status: 0 });
  });
  await executeSaveComment(h.deps, h.imageId);
  assert.equal(h.state.saves.get(h.key()).status, "unconfirmed");
  h.getReviewQueue.push(async () => ({
    review: { comments: "server-now", revision: 1 },
    persisted_revision: 1,
  }));
  const refreshed = await refreshServerReview(h.deps, h.imageId);
  assert.equal(refreshed.outcome, "refreshed");
  assert.equal(h.state.saves.get(h.key()).status, "unconfirmed");
  assert.equal(h.state.saves.get(h.key()).serverReview.comments, "server-now");
  assert.equal(h.state.drafts.get(h.key()).comments, "maybe");
  assert.equal(h.putQueue.length, 0);
});

test("stale writers surface conflict and preserve draft", async () => {
  const h = makeHarness({ persistedRevision: 1 });
  h.setDraft("my-edit");
  h.putQueue.push(async () => {
    throw Object.assign(new Error("revision conflict"), { status: 409 });
  });
  h.getReviewQueue.push(async () => ({
    review: { comments: "server-wins", revision: 2 },
    persisted_revision: 2,
  }));
  const conflicted = await executeSaveComment(h.deps, h.imageId);
  assert.equal(conflicted.outcome, "conflict");
  assert.equal(h.state.saves.get(h.key()).status, "conflict");
  assert.equal(h.state.drafts.get(h.key()).comments, "my-edit");
});

test("classifySaveFailure maps lost response to unconfirmed", () => {
  assert.equal(classifySaveFailure({ status: 0 }), "unconfirmed");
  assert.equal(classifySaveFailure({ status: 409 }), "conflict");
  assert.equal(classifySaveFailure({ status: 422 }), "error");
});

test("saveContinuationValid ignores selection generation", () => {
  const op = {
    status: "pending",
    submittedComments: "x",
    expected_revision: 0,
    datasetId: "ds-a",
    datasetVersion: "v1",
    imageId: "img",
    errorMessage: null,
    serverReview: null,
    serverPersistedRevision: null,
    showCompare: false,
    serverFetchFailed: false,
  };
  assert.ok(
    saveContinuationValid(op, { datasetId: "ds-a", datasetVersion: "v1", imageId: "img" }, {
      datasetId: "ds-a",
      datasetVersion: "v1",
    }),
  );
});
