#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cron job: walk all Preservica folders and refresh thumbnails on any not yet processed.

Processed folder references are tracked in a plain text file (one ref per line).
Each run skips folders already in that file and processes any new ones.

For each unprocessed folder:
  1. Removes the existing thumbnail (if any)
  2. Waits 30 seconds
  3. Adds a new thumbnail
  4. Records the reference in the tracking file

Examples:
    # Normal run
    python thumbnail_refresh.py

    # Use a specific thumbnail image
    python thumbnail_refresh.py --thumbnail /path/to/image.jpg

    # Dry run — detect unprocessed folders without modifying anything
    python thumbnail_refresh.py --dry-run

    # Process a specific folder and all its descendants
    python thumbnail_refresh.py --folder "38284948-923c-4666-88a7-b60f381e2523"

    # Process the entire repository from root
    python thumbnail_refresh.py --folder root
"""

import argparse
import logging
import sys
import time
from pathlib import Path

from dotenv import dotenv_values
from pyPreservica import EntityAPI, Folder

SCRIPT_DIR = Path(__file__).parent
DEFAULT_TRACKING_FILE = SCRIPT_DIR / "processed_folders.txt"
DEFAULT_THUMBNAIL = SCRIPT_DIR / "folder_10x7.png"
THUMBNAIL_WAIT_SECONDS = 30  # pause between remove and add API calls

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def load_processed(tracking_file: Path) -> set:
    if not tracking_file.exists():
        return set()
    return {line.strip() for line in tracking_file.read_text().splitlines() if line.strip()}


def mark_processed(tracking_file: Path, reference: str):
    with open(tracking_file, 'a') as f:
        f.write(reference + '\n')


def refresh_thumbnail(client, folder, thumbnail_path: str, dry_run: bool = False):
    logger.info(f"Processing: {folder.title} ({folder.reference})")
    if dry_run:
        logger.info(f"  [DRY RUN] Would remove thumbnail, wait {THUMBNAIL_WAIT_SECONDS}s, add thumbnail")
        return

    try:
        client.remove_thumbnail(folder)
        logger.info("  Removed thumbnail")
    except Exception as e:
        logger.info(f"  No thumbnail to remove ({e})")

    logger.info(f"  Waiting {THUMBNAIL_WAIT_SECONDS}s before re-adding...")
    time.sleep(THUMBNAIL_WAIT_SECONDS)

    try:
        client.add_thumbnail(folder, thumbnail_path)
        logger.info("  Added thumbnail")
    except Exception as e:
        logger.error(f"  Failed to add thumbnail: {e}")
        raise


def iter_folders(client, start):
    """Yield all Folder entities under start (a Folder object, or None for repository root)."""
    if start is not None:
        yield start
    for e in client.all_descendants(start):
        if isinstance(e, Folder):
            yield e


def process_entities(client, entities, tracking_file, thumbnail, dry_run):
    processed = load_processed(tracking_file)
    logger.info(f"Tracking file: {tracking_file} ({len(processed)} folders already processed)")

    found, skipped, errors = 0, 0, 0
    for entity in entities:
        if entity.reference in processed:
            skipped += 1
            continue
        try:
            folder = client.folder(entity.reference)
            refresh_thumbnail(client, folder, thumbnail, dry_run=dry_run)
            if not dry_run:
                mark_processed(tracking_file, folder.reference)
                processed.add(folder.reference)
            found += 1
        except Exception as e:
            logger.error(f"  Failed to process {entity.reference}: {e}")
            errors += 1

    logger.info(f"Done — {found} processed, {skipped} skipped, {errors} errors")


def main(args):
    env = dotenv_values()
    missing = [v for v in ('USERNAME', 'PASSWORD', 'TENANT', 'SERVER') if not env.get(v)]
    if missing:
        logger.error(f"Missing variables in .env: {', '.join(missing)}")
        sys.exit(1)

    client = EntityAPI(username=env['USERNAME'], password=env['PASSWORD'],
                       tenant=env['TENANT'], server=env['SERVER'])

    if args.folder and args.folder.lower() != 'root':
        root = client.folder(args.folder)
        logger.info(f"Walking from: {root.title} ({root.reference})")
    else:
        root = None
        logger.info("Walking from repository root...")

    process_entities(
        client,
        iter_folders(client, root),
        Path(args.tracking_file),
        args.thumbnail,
        args.dry_run,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Refresh thumbnails on unprocessed Preservica folders.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)

    parser.add_argument('--thumbnail', default=str(DEFAULT_THUMBNAIL),
                        help='Path to thumbnail image (default: unnamed.jpg alongside this script)')
    parser.add_argument('--tracking-file', default=str(DEFAULT_TRACKING_FILE),
                        help='Path to processed folders tracking file (default: processed_folders.txt)')
    parser.add_argument('--folder',
                        help='Folder reference to walk (use "root" for the full repository)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Detect unprocessed folders without modifying thumbnails')

    main(parser.parse_args())
