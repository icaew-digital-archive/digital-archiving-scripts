#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Checksum-based duplicate file finder.

This script identifies duplicate files by comparing their checksums against a known set of checksums.
It supports multiple checksum algorithms and can process files in parallel for improved performance.

Features:
- Support for multiple checksum algorithms (SHA1, MD5, SHA256)
- CSV and plain text checksum file support
- Progress reporting with estimated completion time
- Detailed logging to both console and file
- Folder exclusion patterns
- Output file for duplicate paths
- Parallel processing for improved performance
- Configurable number of worker processes
- Comprehensive error handling and reporting

Usage:
    python checksum_duplicate_checker.py checksum_report path [options]

Options:
    --algo ALGORITHM    Checksum algorithm to use (default: sha1)
    --output-duplicates FILE    Write duplicate paths to this file
    --exclude FOLDER    Folders to exclude from scanning (can be used multiple times)
    --workers N         Number of worker processes to use (default: number of CPU cores)
    --log-file FILE     Path to log file (default: checksum_duplicate_checker.log)
    --verbose           Enable verbose logging
"""

import os
import hashlib
import argparse
import csv
import tempfile
import shutil
from tqdm import tqdm
import logging
from pathlib import Path
from typing import Set, List, Optional, Tuple, Dict, Any
import sys
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
from datetime import timedelta
from dataclasses import dataclass
from enum import Enum, auto


class LogLevel(Enum):
    """Enumeration for log levels."""
    INFO = auto()
    DEBUG = auto()
    WARNING = auto()
    ERROR = auto()


@dataclass
class ProcessingStats:
    """Statistics about the file processing operation."""
    total_files: int = 0
    processed_files: int = 0
    duplicate_files: int = 0
    start_time: float = 0.0
    last_update_time: float = 0.0


def setup_logging(log_file: str = "checksum_duplicate_checker.log", verbose: bool = False) -> None:
    """
    Configure logging for the script.

    Args:
        log_file: Path to the log file
        verbose: Whether to enable debug logging
    """
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
    root_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def log_message(message: str, level: LogLevel = LogLevel.INFO) -> None:
    """
    Log a message with the specified level.

    Args:
        message: The message to log
        level: The log level to use
    """
    logger = logging.getLogger()
    if level == LogLevel.DEBUG:
        logger.debug(message)
    elif level == LogLevel.INFO:
        logger.info(message)
    elif level == LogLevel.WARNING:
        logger.warning(message)
    elif level == LogLevel.ERROR:
        logger.error(message)


def load_known_checksums(checksum_file: str, algo: str = "sha1") -> Set[str]:
    """
    Load known checksums from a file (CSV or plain text).

    Args:
        checksum_file: Path to the checksum file
        algo: Checksum algorithm to look for in CSV headers

    Returns:
        Set of known checksums

    Raises:
        FileNotFoundError: If checksum_file doesn't exist
        ValueError: If the file format is invalid or no matching algorithm column found
    """
    known_checksums: Set[str] = set()
    _, ext = os.path.splitext(checksum_file.lower())
    algo = algo.lower()

    if not os.path.exists(checksum_file):
        log_message(
            f"Checksum file not found: {checksum_file}", LogLevel.ERROR)
        raise FileNotFoundError(f"Checksum file not found: {checksum_file}")

    try_csv = ext == ".csv"

    try:
        with open(checksum_file, 'r', encoding='utf-8') as f:
            if try_csv:
                try:
                    reader = csv.DictReader(f)
                    # Find the column whose header includes the algorithm name
                    target_column = next(
                        (field for field in reader.fieldnames if algo in field.lower()),
                        None
                    )

                    if not target_column:
                        raise ValueError(
                            f"No column found matching algorithm '{algo}' in CSV headers.")

                    for row in reader:
                        if checksum := row.get(target_column, '').strip():
                            known_checksums.add(checksum.lower())
                except Exception as e:
                    log_message(
                        f"Falling back to plain text mode: {e}", LogLevel.WARNING)
                    f.seek(0)
                    for line in f:
                        if line := line.strip():
                            known_checksums.add(line.lower())
            else:
                for line in f:
                    if line := line.strip():
                        known_checksums.add(line.lower())
    except Exception as e:
        log_message(f"Error reading checksum file: {e}", LogLevel.ERROR)
        raise

    if not known_checksums:
        log_message(
            f"No valid checksums found in {checksum_file}", LogLevel.WARNING)
    else:
        log_message(
            f"Loaded {len(known_checksums)} known checksums from {checksum_file}")
    return known_checksums


def compute_checksum(filepath: str, algo: str = 'sha1', chunk_size: int = 1024*1024) -> str:
    """
    Compute the checksum of a file using the specified algorithm.
    Uses a larger chunk size (1MB) for better performance on external drives.

    Args:
        filepath: Path to the file
        algo: Checksum algorithm to use (default: sha1)
        chunk_size: Size of chunks to read (default: 1MB)

    Returns:
        Hex digest of the file's checksum

    Raises:
        FileNotFoundError: If filepath doesn't exist
        PermissionError: If file cannot be read
        ValueError: If algorithm is not supported
    """
    if not os.path.exists(filepath):
        log_message(f"File not found: {filepath}", LogLevel.ERROR)
        raise FileNotFoundError(f"File not found: {filepath}")

    if not os.access(filepath, os.R_OK):
        log_message(f"Permission denied: {filepath}", LogLevel.ERROR)
        raise PermissionError(f"Permission denied: {filepath}")

    try:
        h = hashlib.new(algo)
    except ValueError as e:
        log_message(f"Unsupported algorithm: {algo}", LogLevel.ERROR)
        raise ValueError(f"Unsupported algorithm: {algo}") from e

    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        log_message(
            f"Error computing checksum for {filepath}: {e}", LogLevel.ERROR)
        raise


def process_file(args: Tuple[str, str, Set[str]]) -> Optional[str]:
    """
    Process a single file and return its path if it's a duplicate.
    This function is designed to be used with multiprocessing.

    Args:
        args: Tuple containing (filepath, algorithm, known_checksums)

    Returns:
        Path of the file if it's a duplicate, None otherwise
    """
    filepath, algo, known_checksums = args
    try:
        if os.path.islink(filepath):
            return None

        checksum = compute_checksum(filepath, algo=algo)
        return filepath if checksum in known_checksums else None
    except Exception as e:
        log_message(f"Error processing {filepath}: {e}", LogLevel.ERROR)
        return None


def update_progress(stats: ProcessingStats) -> None:
    """
    Update and log the progress of file processing.

    Args:
        stats: Current processing statistics
    """
    current_time = time.time()
    elapsed = current_time - stats.start_time
    rate = stats.processed_files / elapsed if elapsed > 0 else 0
    remaining = (stats.total_files - stats.processed_files) / \
        rate if rate > 0 else 0

    log_message(
        f"Progress: {stats.processed_files}/{stats.total_files} files processed "
        f"({rate:.1f} files/sec, {stats.duplicate_files} duplicates found, "
        f"ETA: {timedelta(seconds=int(remaining))})"
    )
    stats.last_update_time = current_time


def find_duplicates(
    scan_path: str,
    known_checksums: Set[str],
    algo: str = 'sha1',
    output_file: str = "duplicates.txt",
    exclude_folders: Optional[List[str]] = None,
    num_workers: Optional[int] = None
) -> None:
    """
    Find duplicate files based on checksums.
    Uses multiprocessing for better performance.

    Args:
        scan_path: Path to scan for duplicates
        known_checksums: Set of known checksums to compare against
        algo: Checksum algorithm to use
        output_file: Path to write duplicate file paths
        exclude_folders: List of folders to exclude from scanning
        num_workers: Number of worker processes to use (default: number of CPU cores)
    """
    stats = ProcessingStats(start_time=time.time())

    if not os.path.exists(scan_path):
        log_message(f"Scan path not found: {scan_path}", LogLevel.ERROR)
        raise FileNotFoundError(f"Scan path not found: {scan_path}")

    if not os.access(scan_path, os.R_OK):
        log_message(f"Permission denied: {scan_path}", LogLevel.ERROR)
        raise PermissionError(f"Permission denied: {scan_path}")

    if exclude_folders is None:
        exclude_folders = []

    # Convert exclude folders to absolute paths for comparison
    exclude_folders = [os.path.abspath(os.path.join(
        scan_path, folder)) for folder in exclude_folders]

    # Collect all files to process
    all_files = []
    log_message(f"Scanning directory: {scan_path}")

    # Use tqdm for directory scanning progress
    for root, _, files in tqdm(os.walk(scan_path), desc="Scanning directories"):
        # Skip excluded folders
        if any(root.startswith(exclude) for exclude in exclude_folders):
            log_message(f"Skipping excluded folder: {root}", LogLevel.DEBUG)
            continue

        for name in files:
            filepath = os.path.join(root, name)
            all_files.append(filepath)

    stats.total_files = len(all_files)
    scan_time = time.time() - stats.start_time
    log_message(
        f"Found {stats.total_files} files to process in {timedelta(seconds=int(scan_time))}")

    # Create temporary file for output
    tmp_output = tempfile.NamedTemporaryFile(
        delete=False, mode='w', encoding='utf-8')
    tmp_path = tmp_output.name

    try:
        # Determine number of workers
        if num_workers is None:
            num_workers = multiprocessing.cpu_count()

        log_message(f"Using {num_workers} worker processes")

        # Prepare arguments for parallel processing
        process_args = [(f, algo, known_checksums) for f in all_files]

        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(process_file, args): args[0]
                for args in process_args
            }

            # Process results as they complete
            stats.last_update_time = time.time()
            update_interval = 60  # Update progress every minute

            for future in as_completed(future_to_file):
                result = future.result()
                if result:
                    stats.duplicate_files += 1
                    tmp_output.write(result + "\n")

                stats.processed_files += 1
                current_time = time.time()

                # Update progress every minute or when we're done
                if (current_time - stats.last_update_time >= update_interval or
                        stats.processed_files == stats.total_files):
                    update_progress(stats)
    finally:
        tmp_output.close()

    total_time = time.time() - stats.start_time
    if stats.duplicate_files == 0:
        os.remove(tmp_path)
        log_message(
            f"No duplicates found. Total time: {timedelta(seconds=int(total_time))}")
    else:
        shutil.move(tmp_path, output_file)
        log_message(
            f"Scan complete: {stats.duplicate_files} duplicate(s) found. "
            f"Total time: {timedelta(seconds=int(total_time))}")
        log_message(f"Duplicate file paths written to: {output_file}")


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Find duplicate files from a folder based on checksums."
    )
    parser.add_argument("checksum_report",
                        help="Path to checksum report (CSV or TXT)")
    parser.add_argument("path", help="Path to folder to scan")
    parser.add_argument(
        "--algo", default="sha1", choices=[a.lower() for a in hashlib.algorithms_available],
        help="Checksum algorithm to use for matching (default: sha1)"
    )
    parser.add_argument(
        "--output-duplicates", metavar="FILE", default="duplicates.txt",
        help="Write full paths of duplicate files to this file (default: duplicates.txt)"
    )
    parser.add_argument(
        "--exclude", nargs="+", metavar="FOLDER",
        help="List of folders to exclude from scanning (relative to scan path)"
    )
    parser.add_argument(
        "--log-file", metavar="FILE", default="checksum_duplicate_checker.log",
        help="Path to log file (default: checksum_duplicate_checker.log)"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--workers", type=int, metavar="N",
        help="Number of worker processes to use (default: number of CPU cores)"
    )

    args = parser.parse_args()
    args.algo = args.algo.lower()

    # Setup logging
    setup_logging(args.log_file, args.verbose)

    log_message("Starting checksum duplicate checker")
    log_message(f"Using checksum algorithm: {args.algo}")
    log_message(f"Scan path: {args.path}")
    if args.exclude:
        log_message(f"Excluding folders: {', '.join(args.exclude)}")

    try:
        log_message("Loading known checksums...")
        known = load_known_checksums(args.checksum_report, algo=args.algo)
        log_message(f"{len(known)} known checksums loaded.")

        find_duplicates(
            scan_path=args.path,
            known_checksums=known,
            algo=args.algo,
            output_file=args.output_duplicates,
            exclude_folders=args.exclude,
            num_workers=args.workers
        )

    except Exception as e:
        log_message(f"Fatal error: {e}", LogLevel.ERROR)
        sys.exit(1)


if __name__ == "__main__":
    main()
