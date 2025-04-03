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

Usage:
    python delete_files_from_list.py file_list.txt [options]

Options:
    --dry-run     Don't actually delete items, just show what would be deleted
    --no-confirm  Skip confirmation prompt
    --log-file    Specify log file location
    --verbose     Enable verbose logging
"""

import os
import argparse
import logging
import sys
from pathlib import Path
from typing import List
from tqdm import tqdm


def setup_logging(log_file: str = "delete_files.log") -> None:
    """Configure logging for the script."""
    log_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(log_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def read_file_list(file_path: str) -> List[str]:
    """
    Read a list of file and directory paths from a file.

    Args:
        file_path: Path to the file containing the list

    Returns:
        List of file and directory paths

    Raises:
        FileNotFoundError: If the input file doesn't exist
    """
    if not os.path.exists(file_path):
        logging.error(f"File list not found: {file_path}")
        raise FileNotFoundError(f"File list not found: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logging.error(f"Error reading file list: {e}")
        raise


def is_directory_empty(directory: str) -> bool:
    """
    Check if a directory is empty, including hidden files.

    Args:
        directory: Path to the directory to check

    Returns:
        True if directory is empty, False otherwise
    """
    try:
        return not any(os.scandir(directory))
    except Exception as e:
        logging.error(f"Error checking directory {directory}: {e}")
        return False


def delete_files(file_paths: List[str], dry_run: bool = False) -> None:
    """
    Delete files and empty directories from the list.

    Args:
        file_paths: List of file and directory paths to delete
        dry_run: If True, only show what would be deleted without making changes

    The function will:
    - Delete files directly
    - Delete directories only if they are empty (including hidden files)
    - Skip non-empty directories with a warning
    - Log all operations and errors
    """
    success_count = 0
    error_count = 0

    for file_path in tqdm(file_paths, desc="Deleting files", unit="file"):
        try:
            if not os.path.exists(file_path):
                logging.warning(f"Path not found: {file_path}")
                error_count += 1
                continue

            if os.path.isfile(file_path):
                if dry_run:
                    logging.info(f"[DRY RUN] Would delete file: {file_path}")
                    success_count += 1
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
                    success_count += 1
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
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Delete files and empty directories based on a list of paths."
    )
    parser.add_argument(
        "file_list",
        help="Path to file containing list of files and directories to delete (one per line)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Don't actually delete items, just show what would be deleted"
    )
    parser.add_argument(
        "--no-confirm", action="store_true",
        help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--log-file", metavar="FILE", default="delete_files.log",
        help="Path to log file (default: delete_files.log)"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_file)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Read the file list
        logging.info(f"Reading file list from: {args.file_list}")
        file_paths = read_file_list(args.file_list)
        logging.info(f"Found {len(file_paths)} files to process")

        if not file_paths:
            logging.warning("No files found in the list")
            return

        # Show summary
        logging.info(
            f"Found {len(file_paths)} files to {'delete' if not args.dry_run else 'process'}")
        if args.verbose:
            for path in file_paths:
                logging.debug(f"File: {path}")

        # Confirm deletion
        if not args.no_confirm and not args.dry_run:
            confirm = input(
                f"Are you sure you want to delete {len(file_paths)} files? Type YES to confirm: ")
            if confirm != "YES":
                logging.info("Operation cancelled by user")
                return

        # Delete files
        delete_files(file_paths, args.dry_run)

    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
