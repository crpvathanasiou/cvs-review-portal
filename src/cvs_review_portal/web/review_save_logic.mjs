/**
 * MVP comments-only Save continuation (no audit history / request-receipt machine).
 *
 * Review persistence is independent of run_id. Dataset/version/image identity
 * remains authoritative after awaits; selection-generation bumps from run changes
 * must not orphan an in-flight Save.
 */

/**
 * @typedef {{
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
 * }} SaveOperation
 */

/**
 * @param {SaveOperation | null | undefined} op
 * @param {{ datasetId: string, datasetVersion: string, imageId: string }} token
 * @param {{ datasetId: string, datasetVersion: string } | null} currentIdentity
 * @returns {SaveOperation | null}
 */
export function saveContinuationValid(op, token, currentIdentity) {
  if (!op) return null;
  if (
    op.datasetId !== token.datasetId ||
    op.datasetVersion !== token.datasetVersion ||
    op.imageId !== token.imageId
  ) {
    return null;
  }
  if (
    !currentIdentity ||
    currentIdentity.datasetId !== token.datasetId ||
    currentIdentity.datasetVersion !== token.datasetVersion
  ) {
    return null;
  }
  return op;
}

/**
 * @param {{ status: number | null | undefined }} args
 * @returns {"conflict"|"unconfirmed"|"error"}
 */
export function classifySaveFailure(args) {
  const status = args.status;
  if (status === 409) return "conflict";
  if (status == null || status === 0 || status >= 500) return "unconfirmed";
  return "error";
}

/**
 * @param {object} args
 * @returns {SaveOperation}
 */
export function buildPendingSaveOp(args) {
  return {
    status: "pending",
    submittedComments: args.comments,
    expected_revision: args.expectedRevision,
    datasetId: args.datasetId,
    datasetVersion: args.datasetVersion,
    imageId: args.imageId,
    errorMessage: null,
    serverReview: null,
    serverPersistedRevision: null,
    showCompare: false,
    serverFetchFailed: false,
  };
}

/**
 * Orchestrate one Save attempt using injected transport and mutable maps.
 *
 * @param {object} deps
 * @param {string} imageId
 */
export async function executeSaveComment(deps, imageId) {
  const identity = deps.currentIdentity();
  const image = deps.findImage(imageId);
  if (!identity || !image) return { outcome: "noop" };

  const key = deps.draftKey(identity.datasetId, identity.datasetVersion, imageId);
  const existing = deps.saves.get(key) || null;
  if (existing && existing.status === "pending") return { outcome: "noop" };
  if (existing && existing.status === "conflict") return { outcome: "noop" };
  if (existing && existing.status === "unconfirmed") return { outcome: "noop" };

  const draft = deps.effectiveDraft(image);
  const token = {
    datasetId: identity.datasetId,
    datasetVersion: identity.datasetVersion,
    imageId,
  };
  const comments = draft.comments;
  const expectedRevision = deps.baseRevision(image);
  const maxLen = deps.maxCommentLength ?? 8000;

  if (comments.length > maxLen) {
    deps.saves.set(key, {
      ...buildPendingSaveOp({
        comments,
        expectedRevision,
        datasetId: identity.datasetId,
        datasetVersion: identity.datasetVersion,
        imageId,
      }),
      status: "error",
      errorMessage: `Comments exceed the maximum length of ${maxLen} characters.`,
    });
    deps.onOpChanged?.(imageId);
    return { outcome: "error" };
  }

  deps.drafts.set(key, { comments: draft.comments });
  deps.saves.set(
    key,
    buildPendingSaveOp({
      comments,
      expectedRevision,
      datasetId: identity.datasetId,
      datasetVersion: identity.datasetVersion,
      imageId,
    }),
  );
  deps.onOpChanged?.(imageId);

  try {
    const body = await deps.putReview(
      deps.reviewUrl(identity.datasetId, identity.datasetVersion, imageId),
      {
        comments,
        expected_revision: expectedRevision,
      },
    );
    const still = saveContinuationValid(deps.saves.get(key), token, deps.currentIdentity());
    if (!still) return { outcome: "stale" };

    const current = body.current;
    const persistedRevision =
      typeof body.persisted_revision === "number"
        ? body.persisted_revision
        : current.revision;
    deps.applyPersistedReview({
      datasetId: token.datasetId,
      datasetVersion: token.datasetVersion,
      imageId: token.imageId,
      review: current,
      persistedRevision,
    });
    deps.drafts.delete(key);
    deps.saves.delete(key);
    deps.onOpChanged?.(imageId);
    await deps.refreshSummary?.(token);
    return { outcome: "saved", body };
  } catch (err) {
    const stillBefore = saveContinuationValid(
      deps.saves.get(key),
      token,
      deps.currentIdentity(),
    );
    if (!stillBefore) return { outcome: "stale" };

    const status = /** @type {any} */ (err).status;
    const kind = classifySaveFailure({ status });

    if (kind === "conflict") {
      return await _applyConflict(deps, {
        key,
        token,
        still: stillBefore,
        err,
        identity,
        imageId,
      });
    }

    if (kind === "unconfirmed") {
      deps.saves.set(key, {
        ...stillBefore,
        status: "unconfirmed",
        errorMessage: "Save could not be confirmed",
        showCompare: false,
      });
      deps.onOpChanged?.(imageId);
      return { outcome: "unconfirmed" };
    }

    deps.saves.set(key, {
      ...stillBefore,
      status: "error",
      errorMessage: deps.errorMessage(err) || "Save failed.",
    });
    deps.onOpChanged?.(imageId);
    return { outcome: "error" };
  }
}

/**
 * Refresh the current server review into an unconfirmed or conflict op (read-only).
 * Does not resend the write.
 *
 * @param {object} deps
 * @param {string} imageId
 */
export async function refreshServerReview(deps, imageId) {
  const identity = deps.currentIdentity();
  if (!identity) return { outcome: "noop" };
  const key = deps.draftKey(identity.datasetId, identity.datasetVersion, imageId);
  const op = deps.saves.get(key);
  if (!op || (op.status !== "unconfirmed" && op.status !== "conflict")) {
    return { outcome: "noop" };
  }
  const token = {
    datasetId: op.datasetId,
    datasetVersion: op.datasetVersion,
    imageId: op.imageId,
  };
  try {
    const current = await deps.getReview(
      deps.reviewUrl(identity.datasetId, identity.datasetVersion, imageId),
    );
    const still = saveContinuationValid(deps.saves.get(key), token, deps.currentIdentity());
    if (!still) return { outcome: "stale" };
    if (current.review) {
      deps.applyPersistedReview({
        datasetId: token.datasetId,
        datasetVersion: token.datasetVersion,
        imageId: token.imageId,
        review: current.review,
        persistedRevision: current.persisted_revision,
      });
    }
    deps.saves.set(key, {
      ...still,
      serverReview: current.review,
      serverPersistedRevision: current.persisted_revision,
      serverFetchFailed: false,
      showCompare: true,
    });
    deps.onOpChanged?.(imageId);
    return { outcome: "refreshed" };
  } catch {
    const still = saveContinuationValid(deps.saves.get(key), token, deps.currentIdentity());
    if (!still) return { outcome: "stale" };
    deps.saves.set(key, { ...still, serverFetchFailed: true, showCompare: true });
    deps.onOpChanged?.(imageId);
    return { outcome: "fetch_failed" };
  }
}

/**
 * @param {any} deps
 * @param {object} ctx
 */
async function _applyConflict(deps, ctx) {
  const { key, token, still, err, identity, imageId } = ctx;
  let serverReview = null;
  let serverRevision = null;
  let serverFetchFailed = false;
  try {
    const current = await deps.getReview(
      deps.reviewUrl(identity.datasetId, identity.datasetVersion, imageId),
    );
    const stillAfter = saveContinuationValid(
      deps.saves.get(key),
      token,
      deps.currentIdentity(),
    );
    if (!stillAfter) return { outcome: "stale" };
    serverReview = current.review;
    serverRevision = current.persisted_revision;
    if (serverReview) {
      deps.applyPersistedReview({
        datasetId: token.datasetId,
        datasetVersion: token.datasetVersion,
        imageId: token.imageId,
        review: serverReview,
        persistedRevision: serverRevision,
      });
    }
  } catch {
    serverFetchFailed = true;
    if (!saveContinuationValid(deps.saves.get(key), token, deps.currentIdentity())) {
      return { outcome: "stale" };
    }
  }

  const cont = saveContinuationValid(deps.saves.get(key), token, deps.currentIdentity());
  if (!cont) return { outcome: "stale" };
  if (!deps.drafts.get(key)) {
    deps.drafts.set(key, { comments: cont.submittedComments });
  }
  deps.saves.set(key, {
    ...cont,
    status: "conflict",
    errorMessage: deps.errorMessage(err) || "Revision conflict.",
    serverReview,
    serverPersistedRevision: serverRevision,
    showCompare: true,
    serverFetchFailed,
  });
  deps.onOpChanged?.(imageId);
  return { outcome: "conflict" };
}
