"""Resolve images/intervals against the active video CSV without building a full dataset."""

from __future__ import annotations

from dataclasses import dataclass

from cvs_review_portal.application.interval_index import (
    IntervalRecord,
    build_interval_index,
    find_frame_by_display_id,
    find_frame_by_image_id,
    find_interval,
    normalize_video_query,
    video_filename_matches,
)
from cvs_review_portal.application.ports import PortalDataStore
from cvs_review_portal.domain.errors import ResourceNotFoundError
from cvs_review_portal.domain.models import DatasetImage, VideoArtifact, VideoCatalog


@dataclass(frozen=True, slots=True)
class ResolvedImage:
    video: VideoArtifact
    image: DatasetImage


def require_published_video_catalog(
    store: PortalDataStore,
    dataset_id: str,
    dataset_version: str,
) -> VideoCatalog:
    """Load videos.csv for a published dataset (always re-reads the small CSV)."""
    return store.load_video_catalog(dataset_id, dataset_version)


def load_active_video(
    store: PortalDataStore,
    dataset_id: str,
    dataset_version: str,
    video_id: str,
) -> VideoArtifact:
    """Load one active video; CSV membership is re-checked inside the store."""
    return store.load_video(dataset_id, dataset_version, video_id)


def resolve_image(
    store: PortalDataStore,
    dataset_id: str,
    dataset_version: str,
    image_id: str,
    *,
    video_id: str | None = None,
) -> ResolvedImage:
    """Resolve an image within one active video, or discover via sequential scan.

    When ``video_id`` is provided, only that video's JSON is loaded (after CSV
    membership check). Ownership of ``image_id`` is validated server-side.
    Sequential scanning is used only when ``video_id`` is omitted (explicit
    image_id/display_id discovery without a known owner).
    """
    if video_id is not None:
        video = load_active_video(store, dataset_id, dataset_version, video_id)
        image = video.get_image(image_id)
        if image is None:
            raise ResourceNotFoundError(
                "Image not found in the requested active video.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"video_id={video_id} image_id={image_id}"
                ),
            )
        return ResolvedImage(video=video, image=image)
    return find_image_in_active_videos(store, dataset_id, dataset_version, image_id)


def find_image_in_active_videos(
    store: PortalDataStore,
    dataset_id: str,
    dataset_version: str,
    image_id: str,
) -> ResolvedImage:
    """Sequential discovery across active videos (no known owning video_id)."""
    catalog = require_published_video_catalog(store, dataset_id, dataset_version)
    for entry in catalog.entries:
        video = load_active_video(store, dataset_id, dataset_version, entry.video_id)
        image = video.get_image(image_id)
        if image is not None:
            return ResolvedImage(video=video, image=image)
    raise ResourceNotFoundError(
        "Image not found in an active video.",
        safe_context=(
            f"dataset_id={dataset_id} dataset_version={dataset_version} image_id={image_id}"
        ),
    )


def intervals_for_active_video(
    store: PortalDataStore,
    dataset_id: str,
    dataset_version: str,
    video_id: str,
) -> tuple[VideoArtifact, list[IntervalRecord]]:
    video = load_active_video(store, dataset_id, dataset_version, video_id)
    return video, build_interval_index(video.as_dataset_version())


def resolve_interval(
    store: PortalDataStore,
    dataset_id: str,
    dataset_version: str,
    segment_id: str,
    *,
    video_id: str | None = None,
) -> tuple[VideoArtifact, IntervalRecord]:
    """Resolve an interval within one active video, or discover via sequential scan."""
    if video_id is not None:
        video = load_active_video(store, dataset_id, dataset_version, video_id)
        record = find_interval(build_interval_index(video.as_dataset_version()), segment_id)
        if record is None:
            raise ResourceNotFoundError(
                "Interval not found in the requested active video.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"video_id={video_id} segment_id={segment_id}"
                ),
            )
        return video, record
    return find_interval_in_active_videos(store, dataset_id, dataset_version, segment_id)


def find_interval_in_active_videos(
    store: PortalDataStore,
    dataset_id: str,
    dataset_version: str,
    segment_id: str,
) -> tuple[VideoArtifact, IntervalRecord]:
    """Sequential discovery across active videos (no known owning video_id)."""
    catalog = require_published_video_catalog(store, dataset_id, dataset_version)
    for entry in catalog.entries:
        video = load_active_video(store, dataset_id, dataset_version, entry.video_id)
        record = find_interval(build_interval_index(video.as_dataset_version()), segment_id)
        if record is not None:
            return video, record
    raise ResourceNotFoundError(
        "Interval not found in an active video.",
        safe_context=(
            f"dataset_id={dataset_id} dataset_version={dataset_version} " f"segment_id={segment_id}"
        ),
    )


def search_active_videos(
    store: PortalDataStore,
    dataset_id: str,
    dataset_version: str,
    query: str,
) -> tuple[
    str,
    list[tuple[VideoArtifact, IntervalRecord]],
    tuple[VideoArtifact, IntervalRecord, int] | None,
]:
    """Search active videos using CSV for video matches; scan video JSON only for image IDs.

    Returns ``(match_kind, interval_hits, image_hit)`` where ``image_hit`` is
    ``(video, interval, frame_index)`` when match_kind is ``image``.
    """
    raw = query.strip()
    catalog = require_published_video_catalog(store, dataset_id, dataset_version)
    if not raw:
        return "empty", [], None

    # Exact video_id from CSV (no video JSON).
    for entry in catalog.entries:
        if entry.video_id == raw:
            video, records = intervals_for_active_video(
                store, dataset_id, dataset_version, entry.video_id
            )
            hits = [(video, record) for record in records]
            return "video", hits, None

    # Case-insensitive video filename / stem from CSV.
    matched_entries = [
        entry
        for entry in catalog.entries
        if video_filename_matches(entry.video_name, raw)
        or normalize_video_query(entry.video_name) == normalize_video_query(raw)
    ]
    if matched_entries:
        hits: list[tuple[VideoArtifact, IntervalRecord]] = []
        for entry in matched_entries:
            video, records = intervals_for_active_video(
                store, dataset_id, dataset_version, entry.video_id
            )
            hits.extend((video, record) for record in records)
        return "video", hits, None

    # Exact image_id / display_id — sequential active video JSON search only.
    for entry in catalog.entries:
        video = load_active_video(store, dataset_id, dataset_version, entry.video_id)
        records = build_interval_index(video.as_dataset_version())
        image_hit = find_frame_by_image_id(records, raw)
        if image_hit is None:
            image_hit = find_frame_by_display_id(records, raw)
        if image_hit is not None:
            record, frame_index = image_hit
            return "image", [(video, record)], (video, record, frame_index)

    return "none", [], None


def iter_active_images(
    store: PortalDataStore,
    dataset_id: str,
    dataset_version: str,
) -> list[tuple[VideoArtifact, DatasetImage]]:
    """Load every active video's images (explicit summary / full-detail paths only)."""
    catalog = require_published_video_catalog(store, dataset_id, dataset_version)
    out: list[tuple[VideoArtifact, DatasetImage]] = []
    for entry in catalog.entries:
        video = load_active_video(store, dataset_id, dataset_version, entry.video_id)
        for image in video.images:
            out.append((video, image))
    return out


__all__ = (
    "ResolvedImage",
    "find_image_in_active_videos",
    "find_interval_in_active_videos",
    "intervals_for_active_video",
    "iter_active_images",
    "load_active_video",
    "require_published_video_catalog",
    "resolve_image",
    "resolve_interval",
    "search_active_videos",
)
