#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Safely delete files and empty directories based on a list of paths.

This script reads a file containing paths (one per line) and deletes the files
and empty directories after confirmation. It includes safety checks and detailed logging.

Features:
- Safety confirmation before deletion
- Detailed logging of operations
- Progress reporting
- Error handling and recovery
- Dry run mode for testing
- Handles both files and empty directories
- Checks for hidden files in directories
- Path sanitization and restricted root scope

Usage:
    python delete_files_from_list.py file_list.txt [options]

Options:
    --dry-run     Don't actually delete items, just show what would be deleted
    --no-confirm  Skip confirmation prompt
    --log-file    Specify log file location
    --verbose     Enable verbose logging
    --safe-root   Add an additional safe root directory (can be used multiple times)
"""

import os
import argparse
import logging
import sys
from pathlib import Path
from typing import List
from tqdm import tqdm

# Restrict operations to safe root directories
SAFE_ROOTS = [
    os.path.abspath("/home/digital-archivist"),
    os.path.abspath("/media/digital-archivist/")
]


def setup_logging(log_file: str = "delete_files.log") -> None:
    """Configure logging for the script."""
    log_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(log_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def read_file_list(file_path: str) -> List[str]:
    if not os.path.exists(file_path):
        logging.error(f"File list not found: {file_path}")
        raise FileNotFoundError(f"File list not found: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return [os.path.abspath(line.strip()) for line in f
                    if line.strip() and not line.strip().startswith('#')]
    except Exception as e:
        logging.error(f"Error reading file list: {e}")
        raise


def is_directory_empty(directory: str) -> bool:
    try:
        return not any(os.scandir(directory))
    except Exception as e:
        logging.error(f"Error checking directory {directory}: {e}")
        return False


def is_path_within_safe_root(path: str) -> bool:
    """Check if the given path is within any of the safe root directories."""
    abs_path = os.path.abspath(path)
    return any(abs_path.startswith(root) for root in SAFE_ROOTS)


def delete_files(file_paths: List[str], dry_run: bool = False) -> None:
    success_count = 0
    error_count = 0

    for file_path in tqdm(file_paths, desc="Processing items", unit="item"):
        try:
            if not is_path_within_safe_root(file_path):
                logging.warning(f"Path outside safe root: {file_path}")
                error_count += 1
                continue

            if not os.path.exists(file_path):
                logging.warning(f"Path not found: {file_path}")
                error_count += 1
                continue

            if os.path.islink(file_path):
                logging.warning(f"Skipping symbolic link: {file_path}")
                error_count += 1
                continue

            if os.path.isfile(file_path):
                if dry_run:
                    logging.info(f"[DRY RUN] Would delete file: {file_path}")
                else:
                    os.remove(file_path)
                    logging.info(f"Deleted file: {file_path}")
                success_count += 1

            elif os.path.isdir(file_path):
                if not is_directory_empty(file_path):
                    logging.warning(f"Directory not empty: {file_path}")
                    error_count += 1
                    continue

                if dry_run:
                    logging.info(
                        f"[DRY RUN] Would delete empty directory: {file_path}")
                else:
                    os.rmdir(file_path)
                    logging.info(f"Deleted empty directory: {file_path}")
                success_count += 1

            else:
                logging.warning(f"Not a file or directory: {file_path}")
                error_count += 1

        except PermissionError:
            logging.error(f"Permission denied: {file_path}")
            error_count += 1
        except Exception as e:
            logging.error(f"Error deleting {file_path}: {e}")
            error_count += 1

    logging.info(
        f"Operation complete: {success_count} items {'would be ' if dry_run else ''}deleted, {error_count} errors")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delete files and empty directories based on a list of paths."
    )
    parser.add_argument(
        "file_list", help="Path to file containing list of files and directories to delete (one per line)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't actually delete items, just show what would be deleted")
    parser.add_argument("--no-confirm", action="store_true",
                        help="Skip confirmation prompt")
    parser.add_argument("--log-file", metavar="FILE", default="delete_files.log",
                        help="Path to log file (default: delete_files.log)")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose logging")
    parser.add_argument("--safe-root", action="append", dest="safe_roots",
                        help="Add an additional safe root directory (can be used multiple times)")

    args = parser.parse_args()

    setup_logging(args.log_file)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Update SAFE_ROOTS with any additional roots from command line
    global SAFE_ROOTS
    if args.safe_roots:
        SAFE_ROOTS.extend(os.path.abspath(root) for root in args.safe_roots)
        logging.info(f"Safe root directories: {SAFE_ROOTS}")

    try:
        logging.info(f"Reading list from: {args.file_list}")
        file_paths = read_file_list(args.file_list)
        logging.info(f"Found {len(file_paths)} items to process")

        if not file_paths:
            logging.warning("No items found in the list")
            return

        logging.info(
            f"Found {len(file_paths)} items to {'delete' if not args.dry_run else 'process'}")
        if args.verbose:
            for path in file_paths:
                logging.debug(f"Item: {path}")

        if not args.no_confirm and not args.dry_run:
            confirm = input(
                f"Are you sure you want to delete {len(file_paths)} items (files and empty directories)? Type YES to confirm: ")
            if confirm != "YES":
                logging.info("Operation cancelled by user")
                return

        delete_files(file_paths, args.dry_run)

    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
