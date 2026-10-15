"""Parse and validate the active-video CSV catalog (sole activation list)."""

from __future__ import annotations

import csv
import io
from typing import Literal

from cvs_review_portal.domain.errors import InvalidArtifactError, InvalidIdentifierError
from cvs_review_portal.domain.identifiers import validate_identifier, validate_relative_storage_key
from cvs_review_portal.domain.models import VideoCatalog, VideoCatalogEntry

DatasetLayout = Literal["legacy", "video_catalog"]

_CSV_COLUMNS = ("video_id", "video_name", "metadata_path")


def videos_csv_storage_key(dataset_id: str, dataset_version: str) -> str:
    return f"runs-output/datasets/{dataset_id}/{dataset_version}/videos.csv"


def expected_video_metadata_key(dataset_id: str, dataset_version: str, video_id: str) -> str:
    return f"runs-output/datasets/{dataset_id}/{dataset_version}/videos/{video_id}.json"


def parse_videos_csv(
    text: str,
    *,
    dataset_id: str,
    dataset_version: str,
) -> VideoCatalog:
    """Parse ``videos.csv`` text into a VideoCatalog.

    A valid header-only file means zero active videos. Malformed CSV, duplicate
    ``video_id``, or unsafe ``metadata_path`` values raise ``InvalidArtifactError``.
    """
    dataset_id = validate_identifier(dataset_id, field="dataset_id")
    dataset_version = validate_identifier(dataset_version, field="dataset_version")

    # utf-8-sig strips a BOM if present (common from spreadsheet tools).
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if reader.fieldnames is None:
        raise InvalidArtifactError(
            "videos.csv is missing a header row.",
            safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
        )
    normalized = tuple(name.strip() for name in reader.fieldnames)
    if normalized != _CSV_COLUMNS:
        raise InvalidArtifactError(
            "videos.csv header must be exactly video_id,video_name,metadata_path.",
            safe_context=f"dataset_id={dataset_id} dataset_version={dataset_version}",
        )

    entries: list[VideoCatalogEntry] = []
    seen_ids: set[str] = set()
    for row_number, raw_row in enumerate(reader, start=2):
        # Skip completely empty lines produced by trailing newlines.
        if all((raw_row.get(col) or "").strip() == "" for col in _CSV_COLUMNS):
            continue
        try:
            video_id = validate_identifier(
                (raw_row.get("video_id") or "").strip(), field="video_id"
            )
            video_name = (raw_row.get("video_name") or "").strip()
            if not video_name:
                raise InvalidIdentifierError(
                    "Invalid video_name.",
                    safe_context="field=video_name",
                )
            metadata_path = validate_relative_storage_key(
                (raw_row.get("metadata_path") or "").strip(),
                field="metadata_path",
            )
        except InvalidIdentifierError as exc:
            raise InvalidArtifactError(
                "videos.csv contains an invalid row.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"row={row_number}"
                ),
            ) from exc

        if video_id in seen_ids:
            raise InvalidArtifactError(
                "videos.csv contains a duplicate video_id.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"video_id={video_id}"
                ),
            )
        seen_ids.add(video_id)

        expected = expected_video_metadata_key(dataset_id, dataset_version, video_id)
        if metadata_path != expected:
            raise InvalidArtifactError(
                "videos.csv metadata_path does not match the expected video JSON key.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"video_id={video_id}"
                ),
            )

        try:
            entries.append(
                VideoCatalogEntry(
                    video_id=video_id,
                    video_name=video_name,
                    metadata_path=metadata_path,
                )
            )
        except ValueError as exc:
            raise InvalidArtifactError(
                "videos.csv contains an invalid row.",
                safe_context=(
                    f"dataset_id={dataset_id} dataset_version={dataset_version} "
                    f"row={row_number}"
                ),
            ) from exc

    return VideoCatalog(
        dataset_id=dataset_id,
        dataset_version=dataset_version,
        entries=entries,
    )


def format_videos_csv(entries: list[VideoCatalogEntry]) -> str:
    """Serialize catalog entries to CSV text (including header)."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(_CSV_COLUMNS), lineterminator="\n")
    writer.writeheader()
    for entry in entries:
        writer.writerow(
            {
                "video_id": entry.video_id,
                "video_name": entry.video_name,
                "metadata_path": entry.metadata_path,
            }
        )
    return buffer.getvalue()
