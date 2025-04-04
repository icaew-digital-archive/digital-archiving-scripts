#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A tool for finding completely empty folders.

This script recursively scans a directory tree to identify folders that contain no files
or subdirectories (including hidden ones).

Features:
- Recursive scanning of directory trees
- Support for hidden files/folders
- Progress reporting
- Detailed logging
- Exclusion patterns
- Comprehensive error handling

Usage:
    python empty_folder_finder.py /path/to/directory [options]

Options:
    --exclude PATTERN Exclude folders matching the pattern (can be used multiple times)
    --verbose         Show detailed progress information
    --log FILE        Write detailed log to specified file
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
    Check if a folder is completely empty, including hidden files and directories.

    Args:
        path: Path to the folder to check
        exclude_patterns: List of patterns to exclude from checking

    Returns:
        True if the folder is empty, False otherwise
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
    Recursively find all completely empty folders in a directory tree.

    Args:
        root_dir: Root directory to start searching from
        exclude_patterns: List of patterns to exclude from checking

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


def main():
    parser = argparse.ArgumentParser(
        description="Find completely empty folders.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # List empty folders
    python empty_folder_finder.py /path/to/directory
    
    # Exclude certain patterns
    python empty_folder_finder.py /path/to/directory --exclude "*.git" --exclude "*.svn"
    
    # Enable verbose logging
    python empty_folder_finder.py /path/to/directory --verbose --log empty_folders.log
    """
    )

    parser.add_argument("directory", help="Root directory to scan")
    parser.add_argument("--exclude", action="append",
                        help="Exclude folders matching this pattern (can be used multiple times)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show detailed progress information")
    parser.add_argument("--log", help="Write detailed log to specified file")

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

    # Write to output file
    output_file = "emptyfolders.txt"
    try:
        with open(output_file, 'w') as f:
            for folder in empty_dirs:
                f.write(f"{folder}\n")
        print(f"\nFound {len(empty_dirs)} empty folders.")
        print(f"Results have been saved to: {os.path.abspath(output_file)}")
    except Exception as e:
        logging.error(f"Failed to write to output file: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
