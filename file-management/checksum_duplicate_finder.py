#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Checksum-based duplicate file finder and remover.

This script identifies duplicate files by comparing their checksums against a known set of checksums.
It can optionally delete the duplicate files after confirmation.

Features:
- Support for multiple checksum algorithms (SHA1, MD5, SHA256)
- CSV and plain text checksum file support
- Progress reporting
- Detailed logging
- Safety confirmation for deletion
- Folder exclusion patterns
- Output file for duplicate paths
- Parallel processing for improved performance
- Configurable number of worker processes

Usage:
    python checksum_duplicate_checker.py checksum_report path [options]

Options:
    --algo ALGORITHM    Checksum algorithm to use (default: sha1)
    --delete            Delete matching files after confirmation
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
from typing import Set, List, Optional, Tuple
import sys
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
from datetime import timedelta

# Configure logging


def setup_logging(log_file: str = "checksum_duplicate_checker.log") -> None:
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


# Global error counter
error_count = 0


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
    global error_count
    known_checksums: Set[str] = set()
    _, ext = os.path.splitext(checksum_file.lower())
    algo = algo.lower()

    if not os.path.exists(checksum_file):
        logging.error(f"Checksum file not found: {checksum_file}")
        raise FileNotFoundError(f"Checksum file not found: {checksum_file}")

    try_csv = ext == ".csv"

    try:
        with open(checksum_file, 'r', encoding='utf-8') as f:
            if try_csv:
                try:
                    reader = csv.DictReader(f)
                    # Find the column whose header includes the algorithm name (e.g., "SHA1 checksum")
                    target_column = None
                    for field in reader.fieldnames:
                        if algo in field.lower():
                            target_column = field
                            break

                    if not target_column:
                        raise ValueError(
                            f"No column found matching algorithm '{algo}' in CSV headers.")

                    for row in reader:
                        checksum = row.get(target_column)
                        if checksum and checksum.strip():  # Check for non-empty checksum
                            known_checksums.add(checksum.strip().lower())
                except Exception as e:
                    logging.warning(f"Falling back to plain text mode: {e}")
                    f.seek(0)
                    for line in f:
                        line = line.strip()
                        if line and algo in line.lower():  # Skip empty lines
                            known_checksums.add(line.lower())
            else:
                for line in f:
                    line = line.strip()
                    if line:  # Skip empty lines
                        known_checksums.add(line.lower())
    except Exception as e:
        logging.error(f"Error reading checksum file: {e}")
        error_count += 1
        raise

    if not known_checksums:
        logging.warning(f"No valid checksums found in {checksum_file}")
    else:
        logging.info(
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
    global error_count

    if not os.path.exists(filepath):
        logging.error(f"File not found: {filepath}")
        raise FileNotFoundError(f"File not found: {filepath}")

    if not os.access(filepath, os.R_OK):
        logging.error(f"Permission denied: {filepath}")
        raise PermissionError(f"Permission denied: {filepath}")

    try:
        h = hashlib.new(algo)
    except ValueError as e:
        logging.error(f"Unsupported algorithm: {algo}")
        raise ValueError(f"Unsupported algorithm: {algo}") from e

    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logging.error(f"Error computing checksum for {filepath}: {e}")
        error_count += 1
        raise


def process_file(args: Tuple[str, str, Set[str], bool]) -> Optional[Tuple[str, bool]]:
    """
    Process a single file and return its path if it's a duplicate.
    This function is designed to be used with multiprocessing.
    """
    filepath, algo, known_checksums, delete = args
    try:
        if os.path.islink(filepath):
            return None

        checksum = compute_checksum(filepath, algo=algo)
        if checksum in known_checksums:
            if delete:
                try:
                    os.remove(filepath)
                    return (filepath, True)
                except Exception as e:
                    logging.error(f"Failed to delete {filepath}: {e}")
                    return (filepath, False)
            return (filepath, False)
        return None
    except Exception as e:
        logging.error(f"Error processing {filepath}: {e}")
        return None


def find_duplicates(
    scan_path: str,
    known_checksums: Set[str],
    algo: str = 'sha1',
    delete: bool = False,
    output_file: str = "duplicates.txt",
    exclude_folders: Optional[List[str]] = None,
    num_workers: Optional[int] = None
) -> None:
    """
    Find and optionally delete duplicate files based on checksums.
    Uses multiprocessing for better performance.

    Args:
        scan_path: Path to scan for duplicates
        known_checksums: Set of known checksums to compare against
        algo: Checksum algorithm to use
        delete: Whether to delete duplicate files
        output_file: Path to write duplicate file paths
        exclude_folders: List of folders to exclude from scanning
        num_workers: Number of worker processes to use (default: number of CPU cores)
    """
    global error_count
    start_time = time.time()

    if not os.path.exists(scan_path):
        logging.error(f"Scan path not found: {scan_path}")
        raise FileNotFoundError(f"Scan path not found: {scan_path}")

    if not os.access(scan_path, os.R_OK):
        logging.error(f"Permission denied: {scan_path}")
        raise PermissionError(f"Permission denied: {scan_path}")

    if exclude_folders is None:
        exclude_folders = []

    # Convert exclude folders to absolute paths for comparison
    exclude_folders = [os.path.abspath(os.path.join(
        scan_path, folder)) for folder in exclude_folders]

    # Collect all files to process
    all_files = []
    logging.info(f"Scanning directory: {scan_path}")

    # Use tqdm for directory scanning progress
    for root, _, files in tqdm(os.walk(scan_path), desc="Scanning directories"):
        # Skip excluded folders
        if any(root.startswith(exclude) for exclude in exclude_folders):
            logging.debug(f"Skipping excluded folder: {root}")
            continue

        for name in files:
            filepath = os.path.join(root, name)
            all_files.append(filepath)

    scan_time = time.time() - start_time
    logging.info(
        f"Found {len(all_files)} files to process in {timedelta(seconds=int(scan_time))}")
    duplicate_count = 0
    deleted_count = 0

    # Create temporary file for output
    tmp_output = tempfile.NamedTemporaryFile(
        delete=False, mode='w', encoding='utf-8')
    tmp_path = tmp_output.name

    try:
        # Determine number of workers
        if num_workers is None:
            num_workers = multiprocessing.cpu_count()

        logging.info(f"Using {num_workers} worker processes")

        # Prepare arguments for parallel processing
        process_args = [(f, algo, known_checksums, delete) for f in all_files]

        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(process_file, args): args[0]
                for args in process_args
            }

            # Process results as they complete
            processed = 0
            last_update = time.time()
            update_interval = 60  # Update progress every minute

            for future in as_completed(future_to_file):
                result = future.result()
                if result:
                    filepath, was_deleted = result
                    duplicate_count += 1
                    if not was_deleted:
                        tmp_output.write(filepath + "\n")
                    else:
                        deleted_count += 1
                        logging.info(f"Deleted: {filepath}")

                processed += 1
                current_time = time.time()

                # Update progress every minute or when we're done
                if current_time - last_update >= update_interval or processed == len(all_files):
                    elapsed = current_time - start_time
                    rate = processed / elapsed if elapsed > 0 else 0
                    remaining = (len(all_files) - processed) / \
                        rate if rate > 0 else 0

                    logging.info(
                        f"Progress: {processed}/{len(all_files)} files processed "
                        f"({rate:.1f} files/sec, {duplicate_count} duplicates found, "
                        f"ETA: {timedelta(seconds=int(remaining))})"
                    )
                    last_update = current_time
    finally:
        tmp_output.close()

    total_time = time.time() - start_time
    if duplicate_count == 0:
        os.remove(tmp_path)
        logging.info(
            f"No duplicates found. Total time: {timedelta(seconds=int(total_time))}")
    else:
        shutil.move(tmp_path, output_file)
        logging.info(
            f"Scan complete: {duplicate_count} duplicate(s) found, {deleted_count} deleted. "
            f"Total time: {timedelta(seconds=int(total_time))}")
        logging.info(f"Duplicate file paths written to: {output_file}")


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Find and optionally delete duplicate files from a folder based on checksums."
    )
    parser.add_argument("checksum_report",
                        help="Path to checksum report (CSV or TXT)")
    parser.add_argument("path", help="Path to folder to scan")
    parser.add_argument(
        "--algo", default="sha1", choices=[a.lower() for a in hashlib.algorithms_available],
        help="Checksum algorithm to use for matching (default: sha1)"
    )
    parser.add_argument(
        "--delete", action="store_true",
        help="Delete matching files after confirmation"
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
    setup_logging(args.log_file)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logging.info("Starting checksum duplicate checker")
    logging.info(f"Using checksum algorithm: {args.algo}")
    logging.info(f"Scan path: {args.path}")
    if args.exclude:
        logging.info(f"Excluding folders: {', '.join(args.exclude)}")

    try:
        logging.info("Loading known checksums...")
        known = load_known_checksums(args.checksum_report, algo=args.algo)
        logging.info(f"{len(known)} known checksums loaded.")

        if args.delete:
            confirm = input(
                "Are you sure you want to delete duplicate files? Type YES to confirm: ")
            if confirm != "YES":
                logging.info("Deletion cancelled by user")
                return

        find_duplicates(
            scan_path=args.path,
            known_checksums=known,
            algo=args.algo,
            delete=args.delete,
            output_file=args.output_duplicates,
            exclude_folders=args.exclude,
            num_workers=args.workers
        )

    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if error_count > 0:
            logging.warning(f"Script completed with {error_count} errors")
        else:
            logging.info("Script completed successfully")


if __name__ == "__main__":
    main()
