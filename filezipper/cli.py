"""Command line interface for the FileZipper utility."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .zipper import copy_to_locations, create_archive


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create ZIP archives and copy them to destinations.")
    parser.add_argument("sources", nargs="+", help="Files or directories to include in the archive.")
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path or directory. Defaults to the current directory with a timestamped name.",
    )
    parser.add_argument(
        "-c",
        "--cloud-destination",
        action="append",
        dest="cloud_destinations",
        help="Directory (or file path) to copy the archive to. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files when traversing directories.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    sources = [Path(src) for src in args.sources]
    output_path = create_archive(
        sources=sources,
        output=Path(args.output) if args.output else None,
        include_hidden=args.include_hidden,
    )

    print(f"Archive created at: {output_path}")

    if args.cloud_destinations:
        destinations = [Path(dest) for dest in args.cloud_destinations]
        copies = copy_to_locations(output_path, destinations)
        for directory, copied_file in copies:
            print(f"Copied archive to {copied_file} (destination: {directory})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
