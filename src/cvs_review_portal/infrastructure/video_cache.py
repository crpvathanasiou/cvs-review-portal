"""Bounded fingerprint-checked cache for per-video metadata artifacts."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from cvs_review_portal.domain.models import VideoArtifact

# Keep a small number of videos in memory; fingerprint invalidates on file change.
_DEFAULT_MAX_ENTRIES = 8


@dataclass(frozen=True, slots=True)
class CachedVideo:
    fingerprint: str
    artifact: VideoArtifact


class VideoArtifactCache:
    """LRU cache keyed by (dataset_id, dataset_version, video_id)."""

    def __init__(self, *, max_entries: int = _DEFAULT_MAX_ENTRIES) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        self._max_entries = max_entries
        self._entries: OrderedDict[tuple[str, str, str], CachedVideo] = OrderedDict()

    def get(
        self,
        dataset_id: str,
        dataset_version: str,
        video_id: str,
        *,
        fingerprint: str,
    ) -> VideoArtifact | None:
        key = (dataset_id, dataset_version, video_id)
        cached = self._entries.get(key)
        if cached is None:
            return None
        if cached.fingerprint != fingerprint:
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return cached.artifact

    def put(
        self,
        dataset_id: str,
        dataset_version: str,
        video_id: str,
        *,
        fingerprint: str,
        artifact: VideoArtifact,
    ) -> None:
        key = (dataset_id, dataset_version, video_id)
        self._entries[key] = CachedVideo(fingerprint=fingerprint, artifact=artifact)
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()
