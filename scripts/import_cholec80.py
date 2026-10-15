"""Import a Cholec80 frame-extraction export into a new portal data root.

Example (owner dry-run):

    poetry run python scripts/import_cholec80.py --dry-run `
      --export-root "<export-root>" `
      --ground-truth-xlsx "<cholec80-CVS.xlsx>" `
      --destination "<new-empty-data-root>" `
      --dataset-id cholec80 `
      --dataset-version v1

The extraction run.json is provenance for the export only. It is never registered
as a portal inference RunManifest.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cvs_review_portal.importers.cholec80 import (
    Cholec80ImportError,
    format_report,
    prepare_cholec80_dataset,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare a Cholec80 frame export as a portal dataset root "
            "(dataset.json + catalog.json + raw image copies)."
        )
    )
    parser.add_argument(
        "--export-root",
        type=Path,
        required=True,
        help="Export directory containing run.json, manifest.jsonl, and images/.",
    )
    parser.add_argument(
        "--ground-truth-xlsx",
        type=Path,
        required=True,
        help="Cholec80 CVS ground-truth workbook (critical_view column).",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        required=True,
        help="New empty portal data root to create (refuses a nonempty target).",
    )
    parser.add_argument(
        "--dataset-id",
        required=True,
        help="Portal dataset_id (for example cholec80).",
    )
    parser.add_argument(
        "--dataset-version",
        required=True,
        help="Portal dataset_version (for example v1).",
    )
    parser.add_argument(
        "--display-name",
        default=None,
        help="Optional dataset display_name (defaults to '<dataset-id> <dataset-version>').",
    )
    parser.add_argument(
        "--description",
        default=None,
        help="Optional dataset description.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print counts without creating output or copying images.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = prepare_cholec80_dataset(
            export_root=args.export_root,
            ground_truth_xlsx=args.ground_truth_xlsx,
            destination=args.destination,
            dataset_id=args.dataset_id,
            dataset_version=args.dataset_version,
            dry_run=args.dry_run,
            display_name=args.display_name,
            description=args.description,
        )
    except Cholec80ImportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
