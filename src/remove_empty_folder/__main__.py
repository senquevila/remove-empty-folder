"""Command-line entry point."""

from __future__ import annotations

import argparse

from .app import RemoveEmptyFolderApp


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="remove-empty-folder",
        description="Interactively find and remove directories with no real files.",
    )
    parser.add_argument("path", nargs="?", default=".", help="directory to scan (default: .)")
    parser.add_argument(
        "--dry-run", action="store_true", help="show what would be deleted without deleting"
    )
    args = parser.parse_args()
    RemoveEmptyFolderApp(args.path, dry_run=args.dry_run).run()


if __name__ == "__main__":
    main()
