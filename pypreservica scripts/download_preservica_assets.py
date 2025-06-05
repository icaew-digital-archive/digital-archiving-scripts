#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Download assets from Preservica with various options for specifying what to download.

This script can download assets in several ways:
- From a single folder (--folder)
- From multiple folders (--folders-file)
- A single asset (--asset)
- Multiple assets (--assets-file)

All downloads verify fixity values to ensure file integrity.

Examples:
    # Download from a single folder
    python download_preservica_assets.py --folder "bb45f999-7c07-4471-9c30-54b057c500ff" ./downloads

    # Download from multiple folders listed in a file
    python download_preservica_assets.py --folders-file "folder_list.txt" ./downloads

    # Download a single asset
    python download_preservica_assets.py --asset "cc56e888-8d18-5582-0d41-65c168d611ee" ./downloads

    # Download multiple assets listed in a file
    python download_preservica_assets.py --assets-file "asset_list.txt" ./downloads

    # Download from root folder
    python download_preservica_assets.py --folder "root" ./downloads

    # Use asset reference numbers in filenames
    python download_preservica_assets.py --folder "folder-id" --use-asset-ref ./downloads
"""

import argparse
import os
from pathlib import Path
import hashlib
import logging
import sys
from datetime import datetime

from dotenv import load_dotenv
from pyPreservica import *

# Load configuration from environment variables
load_dotenv(override=True)
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TENANT = os.getenv('TENANT')
SERVER = os.getenv('SERVER')


def calculate_file_hash(file_path, hash_algorithm):
    hash_obj = hashlib.new(hash_algorithm)
    with open(file_path, 'rb') as file:
        for byte_block in iter(lambda: file.read(4096), b""):
            hash_obj.update(byte_block)
    return hash_obj.hexdigest()


def download_bitstream(client, bitstream, download_path):
    try:
        client.bitstream_content(bitstream, download_path)
        return True
    except Exception as e:
        # Log the error
        logging.error(
            f"Error downloading {bitstream.filename}: {e}", exc_info=True)
        return False


def check_fixity(downloaded_path, preservica_hash, algorithm, bitstream_filename):
    if preservica_hash:
        downloaded_hash = calculate_file_hash(downloaded_path, algorithm)
        if downloaded_hash == preservica_hash:
            logging.info(
                f"Fixity values match ({algorithm.upper()}: {preservica_hash})")
            return True
        else:
            logging.error(
                f"Fixity values did not match for - {bitstream_filename}.")
            return False
    return True


def read_asset_list(file_path):
    """Read asset IDs from a file, one per line."""
    try:
        with open(file_path, 'r') as f:
            # Strip whitespace and filter out empty lines
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logging.error(f"Error reading asset list file: {e}", exc_info=True)
        raise


def get_download_path(download_folder, bitstream, asset_ref, use_asset_ref):
    """Determine the download path for a bitstream based on naming preferences."""
    if use_asset_ref:
        # Get the file extension from the original filename
        ext = Path(bitstream.filename).suffix
        # Create new filename using asset reference
        new_filename = f"{asset_ref}{ext}"
        return Path(download_folder) / new_filename
    else:
        return Path(download_folder) / bitstream.filename


def download_asset(client, asset_ref, download_folder, use_asset_ref=False):
    """Download a single asset and return True if successful, False if there were errors."""
    error_count = 0
    try:
        asset = client.asset(asset_ref)
        for representation in client.representations(asset):
            for content_object in client.content_objects(representation):
                for generation in client.generations(content_object):
                    for bitstream in generation.bitstreams:
                        for algorithm, value in bitstream.fixity.items():
                            algorithm = algorithm.lower()
                            value = value.lower()

                        download_path = get_download_path(
                            download_folder, bitstream, asset_ref, use_asset_ref)

                        if download_path.exists():
                            if value == calculate_file_hash(download_path, algorithm):
                                logging.info(
                                    f"{download_path.name} already exists locally with matching {algorithm}.")
                            else:
                                logging.info(
                                    f"{download_path.name} already exists locally but the {algorithm} does not match.")
                                logging.info(
                                    f'Re-downloading {download_path.name} ({asset_ref})')
                                if download_bitstream(client, bitstream, download_path):
                                    if not check_fixity(download_path, value, algorithm, download_path.name):
                                        error_count += 1
                        else:
                            logging.info(
                                f'Downloading {download_path.name} ({asset_ref})')
                            if download_bitstream(client, bitstream, download_path):
                                if not check_fixity(download_path, value, algorithm, download_path.name):
                                    error_count += 1
        return error_count == 0
    except Exception as e:
        logging.error(
            f"Error processing asset {asset_ref}: {e}", exc_info=True)
        return False


def read_id_list(file_path):
    """Read IDs from a file, one per line."""
    try:
        with open(file_path, 'r') as f:
            # Strip whitespace and filter out empty lines
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logging.error(f"Error reading ID list file: {e}", exc_info=True)
        raise


def process_folder(client, folder_ref, download_folder, use_asset_ref=False):
    """Process a single folder and return True if successful, False if there were errors."""
    error_count = 0
    try:
        # Deal with special root case
        if folder_ref == 'root':
            folder_ref = None

        for asset in filter(only_assets, client.all_descendants(folder_ref)):
            if not download_asset(client, asset.reference, download_folder, use_asset_ref):
                error_count += 1
        return error_count == 0
    except Exception as e:
        logging.error(
            f"Error processing folder {folder_ref}: {e}", exc_info=True)
        return False


def setup_logging(log_dir=None):
    """Configure logging to both console and file."""
    # Create logs directory if it doesn't exist
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f'preservica_download_{timestamp}.log'
    else:
        log_file = 'error_log.txt'

    # Configure logging to console (INFO level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'))

    # Configure logging to file (ERROR level and above)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return log_file


def main(args):
    # Setup logging first
    log_file = setup_logging(args.log_dir)
    logging.info(f"Starting download process. Log file: {log_file}")
    if args.use_asset_ref:
        logging.info("Using asset reference numbers in filenames")

    # Create download directory if it doesn't exist
    download_path = Path(args.download_folder)
    download_path.mkdir(parents=True, exist_ok=True)
    logging.info(f"Download directory: {download_path.absolute()}")

    # Verify environment variables
    required_env_vars = ['USERNAME', 'PASSWORD', 'TENANT', 'SERVER']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logging.error(
            f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    client = EntityAPI(username=USERNAME, password=PASSWORD,
                       tenant=TENANT, server=SERVER)

    error_count = 0
    start_time = datetime.now()

    try:
        if args.folder:
            if not process_folder(client, args.folder, download_path, args.use_asset_ref):
                error_count += 1

        elif args.asset:
            if not download_asset(client, args.asset, download_path, args.use_asset_ref):
                error_count += 1

        elif args.assets_file:
            asset_ids = read_id_list(args.assets_file)
            total_assets = len(asset_ids)
            successful_downloads = 0

            logging.info(f"Found {total_assets} assets to process")
            for i, asset_id in enumerate(asset_ids, 1):
                logging.info(
                    f"Processing asset {i}/{total_assets}: {asset_id}")
                if download_asset(client, asset_id, download_path, args.use_asset_ref):
                    successful_downloads += 1
                else:
                    error_count += 1

            logging.info(
                f"Downloaded {successful_downloads} out of {total_assets} assets successfully")

        elif args.folders_file:
            folder_ids = read_id_list(args.folders_file)
            total_folders = len(folder_ids)
            successful_folders = 0

            logging.info(f"Found {total_folders} folders to process")
            for i, folder_id in enumerate(folder_ids, 1):
                logging.info(
                    f"Processing folder {i}/{total_folders}: {folder_id}")
                if process_folder(client, folder_id, download_path, args.use_asset_ref):
                    successful_folders += 1
                else:
                    error_count += 1

            logging.info(
                f"Successfully processed {successful_folders} out of {total_folders} folders")

    except KeyboardInterrupt:
        logging.warning("\nDownload process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        duration = datetime.now() - start_time
        logging.info(f"Download process completed in {duration}")
        if error_count != 0:
            logging.error(
                f"Encountered {error_count} errors. Please check the log file: {log_file}")
            sys.exit(1)
        else:
            logging.info("Download process completed successfully")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download assets from Preservica with various options for specifying what to download.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)

    parser.add_argument("download_folder",
                        help="Directory where downloaded assets will be saved")

    # Create a group for the mutually exclusive download source options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--folder',
                       help='Single Preservica folder ID to download from. Use "root" for the root folder')
    group.add_argument('--folders-file',
                       help='Path to a text file containing Preservica folder IDs (one per line)')
    group.add_argument('--asset',
                       help='Single Preservica asset ID to download')
    group.add_argument('--assets-file',
                       help='Path to a text file containing Preservica asset IDs (one per line)')

    # Optional arguments
    parser.add_argument('--log-dir',
                        help='Directory to store log files (default: current directory)')
    parser.add_argument('--use-asset-ref',
                        action='store_true',
                        help='Use asset reference numbers in filenames instead of original filenames')

    args = parser.parse_args()
    main(args)
