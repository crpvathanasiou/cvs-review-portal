"""Pure interval grouping, ordering, titles, and metadata search helpers.

Built from dataset image provenance only — never reads reviews or image bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from cvs_review_portal.domain.models import DatasetImage, DatasetVersion, ImageProvenance

SearchMatchKind = Literal["empty", "video", "image", "none"]


@dataclass(frozen=True, slots=True)
class IntervalFrameRef:
    image_id: str
    frame_index: int
    display_id: str
    timestamp: float


@dataclass(frozen=True, slots=True)
class IntervalRecord:
    segment_id: str
    video_id: str
    video_filename: str
    start_seconds: int
    end_seconds: int
    frames: tuple[IntervalFrameRef, ...]

    @property
    def image_count(self) -> int:
        return len(self.frames)

    @property
    def first_image_id(self) -> str:
        return self.frames[0].image_id


def dataset_has_provenance(dataset: DatasetVersion) -> bool:
    return any(image.provenance is not None for image in dataset.images)


def format_clock(seconds: int) -> str:
    """Format non-negative whole seconds as M:SS or H:MM:SS."""
    if seconds < 0:
        seconds = 0
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_summary_clock(seconds: int) -> str:
    """Format non-negative whole seconds as MM:SS or HH:MM:SS for Summary rows."""
    if seconds < 0:
        seconds = 0
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def video_label_from_filename(filename: str) -> str:
    """Derive a short video label such as ``Video 02`` from ``video02.mp4``."""
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    lower = stem.lower()
    if lower.startswith("video"):
        suffix = stem[5:]
        digits = "".join(ch for ch in suffix if ch.isdigit())
        if digits:
            return f"Video {digits.zfill(2) if len(digits) <= 2 else digits}"
    return stem


def interval_title(display_name: str, record: IntervalRecord) -> str:
    video = video_label_from_filename(record.video_filename)
    start = format_clock(record.start_seconds)
    end = format_clock(record.end_seconds)
    return f"{display_name} · {video} · {start}–{end}"


def _frame_sort_key(image: DatasetImage, provenance: ImageProvenance) -> tuple[int, str]:
    return (provenance.frame_index, image.image_id)


def _interval_sort_key(record: IntervalRecord) -> tuple[int, int, str]:
    return (record.start_seconds, record.end_seconds, record.segment_id)


def build_interval_index(dataset: DatasetVersion) -> list[IntervalRecord]:
    """Group provenance-backed images into ordered intervals.

    Images without provenance are omitted. Overlapping intervals remain separate
    records even when they share a source frame under distinct image IDs.
    """
    buckets: dict[str, list[tuple[DatasetImage, ImageProvenance]]] = {}
    for image in dataset.images:
        provenance = image.provenance
        if provenance is None:
            continue
        buckets.setdefault(provenance.segment_id, []).append((image, provenance))

    records: list[IntervalRecord] = []
    for segment_id, members in buckets.items():
        members.sort(key=lambda item: _frame_sort_key(item[0], item[1]))
        first_prov = members[0][1]
        frames = tuple(
            IntervalFrameRef(
                image_id=image.image_id,
                frame_index=prov.frame_index,
                display_id=prov.display_id,
                timestamp=prov.timestamp,
            )
            for image, prov in members
        )
        records.append(
            IntervalRecord(
                segment_id=segment_id,
                video_id=first_prov.video_id,
                video_filename=first_prov.video_filename,
                start_seconds=first_prov.start_seconds,
                end_seconds=first_prov.end_seconds,
                frames=frames,
            )
        )
    records.sort(key=_interval_sort_key)
    return records


def intervals_for_video(records: list[IntervalRecord], video_id: str) -> list[IntervalRecord]:
    return [record for record in records if record.video_id == video_id]


def find_interval(records: list[IntervalRecord], segment_id: str) -> IntervalRecord | None:
    for record in records:
        if record.segment_id == segment_id:
            return record
    return None


def find_frame_by_image_id(
    records: list[IntervalRecord], image_id: str
) -> tuple[IntervalRecord, int] | None:
    for record in records:
        for index, frame in enumerate(record.frames):
            if frame.image_id == image_id:
                return record, index
    return None


def find_frame_by_display_id(
    records: list[IntervalRecord], display_id: str
) -> tuple[IntervalRecord, int] | None:
    for record in records:
        for index, frame in enumerate(record.frames):
            if frame.display_id == display_id:
                return record, index
    return None


def normalize_video_query(query: str) -> str:
    cleaned = query.strip().lower()
    if cleaned.endswith(".mp4"):
        cleaned = cleaned[: -len(".mp4")]
    return cleaned


def video_filename_matches(filename: str, query: str) -> bool:
    """Case-insensitive match on filename or stem (``video02`` / ``video02.mp4``)."""
    q = normalize_video_query(query)
    if not q:
        return False
    name = filename.strip().lower()
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return q == name or q == stem


def search_intervals(
    records: list[IntervalRecord],
    query: str,
) -> tuple[SearchMatchKind, list[IntervalRecord], tuple[IntervalRecord, int] | None]:
    """Resolve a picker search query.

    Returns ``(match_kind, intervals, image_hit)`` where ``match_kind`` is one of
    ``empty``, ``video``, ``image``, or ``none``. An image hit includes the
    owning interval and zero-based frame index.
    """
    raw = query.strip()
    if not raw:
        return "empty", [], None

    # Exact technical video_id
    for record in records:
        if record.video_id == raw:
            return "video", intervals_for_video(records, record.video_id), None

    # Exact technical image_id
    image_hit = find_frame_by_image_id(records, raw)
    if image_hit is not None:
        return "image", [image_hit[0]], image_hit

    # Exact human-readable display_id
    display_hit = find_frame_by_display_id(records, raw)
    if display_hit is not None:
        return "image", [display_hit[0]], display_hit

    # Case-insensitive video filename / stem
    matched_video_ids: list[str] = []
    seen: set[str] = set()
    for record in records:
        if video_filename_matches(record.video_filename, raw) and record.video_id not in seen:
            seen.add(record.video_id)
            matched_video_ids.append(record.video_id)

    if matched_video_ids:
        # Prefer a single video match; if multiple filenames collide, union chronologically.
        collected: list[IntervalRecord] = []
        for video_id in matched_video_ids:
            collected.extend(intervals_for_video(records, video_id))
        return "video", collected, None

    return "none", [], None
