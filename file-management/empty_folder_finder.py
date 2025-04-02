#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A tool for finding and optionally deleting completely empty folders.

This script recursively scans a directory tree to identify folders that contain no files
or subdirectories (including hidden ones). It can either list these folders or delete them.

Features:
- Recursive scanning of directory trees
- Option to delete empty folders
- Support for hidden files/folders
- Progress reporting
- Detailed logging
- Dry run mode
- Exclusion patterns
- Safety confirmation for deletion

Usage:
    python empty_folder.py /path/to/directory [options]

Options:
    --delete          Delete empty folders instead of just listing them
    --exclude PATTERN Exclude folders matching the pattern (can be used multiple times)
    --verbose         Show detailed progress information
    --log FILE        Write detailed log to specified file
    --no-confirm      Skip confirmation prompt when deleting
"""

import os
import argparse
import logging
import sys
from pathlib import Path
from typing import List, Set
import fnmatch


def setup_logging(log_file: str = None, verbose: bool = False) -> None:
    """Configure logging for the script."""
    log_level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def is_folder_empty(path: str, exclude_patterns: List[str] = None) -> bool:
    """
    Check if a folder is completely empty, optionally excluding certain patterns.

    Args:
        path: Path to the folder to check
        exclude_patterns: List of patterns to exclude from the check

    Returns:
        bool: True if the folder is empty, False otherwise
    """
    try:
        with os.scandir(path) as it:
            for entry in it:
                # Skip excluded patterns
                if exclude_patterns and any(fnmatch.fnmatch(entry.name, pattern) for pattern in exclude_patterns):
                    continue
                return False
        return True
    except PermissionError:
        logging.warning(f"Permission denied when scanning {path}")
        return False
    except Exception as e:
        logging.error(f"Error scanning {path}: {str(e)}")
        return False


def find_completely_empty_folders(root_dir: str, exclude_patterns: List[str] = None) -> List[str]:
    """
    Recursively find all empty folders in a directory tree.

    Args:
        root_dir: Root directory to start scanning from
        exclude_patterns: List of patterns to exclude from the check

    Returns:
        List of paths to empty folders
    """
    empty_folders = []
    try:
        for foldername, subfolders, filenames in os.walk(root_dir, topdown=False):
            # Skip excluded patterns
            if exclude_patterns and any(fnmatch.fnmatch(Path(foldername).name, pattern) for pattern in exclude_patterns):
                continue

            if is_folder_empty(foldername, exclude_patterns):
                empty_folders.append(foldername)
                logging.debug(f"Found empty folder: {foldername}")
    except Exception as e:
        logging.error(f"Error walking directory {root_dir}: {str(e)}")

    return empty_folders


def delete_empty_folders(folders: List[str], no_confirm: bool = False) -> None:
    """
    Delete a list of empty folders with optional confirmation.

    Args:
        folders: List of folder paths to delete
        no_confirm: Skip confirmation prompt if True
    """
    if not folders:
        logging.info("No empty folders to delete.")
        return

    if not no_confirm:
        print(f"\nFound {len(folders)} empty folders to delete:")
        for folder in folders:
            print(f"  {folder}")
        confirm = input(
            "\nAre you sure you want to delete these folders? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Operation cancelled.")
            return

    deleted_count = 0
    failed_count = 0

    for folder in folders:
        try:
            os.rmdir(folder)
            logging.info(f"Deleted: {folder}")
            deleted_count += 1
        except Exception as e:
            logging.error(f"Failed to delete {folder}: {str(e)}")
            failed_count += 1

    logging.info(
        f"Deleted {deleted_count} folders. Failed to delete {failed_count} folders.")


def main():
    parser = argparse.ArgumentParser(
        description="Find and optionally delete completely empty folders.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # List empty folders
    python empty_folder.py /path/to/directory
    
    # Delete empty folders
    python empty_folder.py /path/to/directory --delete
    
    # Exclude certain patterns
    python empty_folder.py /path/to/directory --exclude "*.git" --exclude "*.svn"
    
    # Enable verbose logging
    python empty_folder.py /path/to/directory --verbose --log empty_folders.log
    """
    )

    parser.add_argument("directory", help="Root directory to scan")
    parser.add_argument("--delete", action="store_true",
                        help="Delete empty folders instead of just listing them")
    parser.add_argument("--exclude", action="append",
                        help="Exclude folders matching this pattern (can be used multiple times)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show detailed progress information")
    parser.add_argument("--log", help="Write detailed log to specified file")
    parser.add_argument("--no-confirm", action="store_true",
                        help="Skip confirmation prompt when deleting")

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log, args.verbose)

    # Validate directory
    if not os.path.isdir(args.directory):
        logging.error(f"Directory not found: {args.directory}")
        sys.exit(1)

    # Find empty folders
    logging.info(f"Scanning directory: {args.directory}")
    empty_dirs = find_completely_empty_folders(args.directory, args.exclude)

    if not empty_dirs:
        logging.info("No completely empty folders found.")
        return

    if args.delete:
        delete_empty_folders(empty_dirs, args.no_confirm)
    else:
        print("\nDry run: Empty folders found (not deleted):")
        for folder in empty_dirs:
            print(folder)
        print(f"\nTotal empty folders found: {len(empty_dirs)}")


if __name__ == "__main__":
    main()
