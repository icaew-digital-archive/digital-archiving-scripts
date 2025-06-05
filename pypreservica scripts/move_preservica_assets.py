#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Move assets in Preservica to a specified folder (e.g., a "recycle bin" folder).

This script can move assets in two ways:
- A single asset (--asset)
- Multiple assets (--assets-file)

The script will move assets to the specified destination folder instead of deleting them,
allowing for review before permanent deletion.

Examples:
    # Move a single asset to a recycle bin folder
    python move_preservica_assets.py --asset "cc56e888-8d18-5582-0d41-65c168d611ee" --destination "recycle-bin-folder-id"

    # Move multiple assets listed in a file
    python move_preservica_assets.py --assets-file "asset_list.txt" --destination "recycle-bin-folder-id"

    # Skip confirmation prompts (use with caution!)
    python move_preservica_assets.py --asset "asset-id" --destination "folder-id" --force
"""

import argparse
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from pyPreservica import *

# Load configuration from environment variables
load_dotenv(override=True)
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TENANT = os.getenv('TENANT')
SERVER = os.getenv('SERVER')


def setup_logging(log_dir=None):
    """Configure logging to both console and file."""
    # Create logs directory if it doesn't exist
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f'preservica_move_{timestamp}.log'
    else:
        log_file = 'move_log.txt'

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


def read_asset_list(file_path):
    """Read asset IDs from a file, one per line."""
    try:
        with open(file_path, 'r') as f:
            # Strip whitespace and filter out empty lines
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logging.error(f"Error reading asset list file: {e}", exc_info=True)
        raise


def get_asset_info(client, asset_ref):
    """Get basic information about an asset for confirmation."""
    try:
        asset = client.asset(asset_ref)
        return {
            'reference': asset.reference,
            'title': getattr(asset, 'title', 'No title available'),
            'security_tag': getattr(asset, 'security_tag', 'No security tag available'),
            'parent': getattr(asset, 'parent', 'No parent folder available'),
            'asset': asset  # Include the full asset object for the move operation
        }
    except Exception as e:
        logging.error(f"Error getting asset info for {asset_ref}: {e}")
        return None


def get_folder_info(client, folder_ref):
    """Get basic information about a folder for confirmation."""
    try:
        folder = client.folder(folder_ref)
        return {
            'reference': folder.reference,
            'title': getattr(folder, 'title', 'No title available'),
            'path': getattr(folder, 'path', 'No path available')
        }
    except Exception as e:
        logging.error(f"Error getting folder info for {folder_ref}: {e}")
        return None


def confirm_move(asset_info, destination_info):
    """Prompt for confirmation before moving an asset."""
    print("\nAsset to be moved:")
    print(f"Reference: {asset_info['reference']}")
    print(f"Title: {asset_info['title']}")
    print(f"Security Tag: {asset_info['security_tag']}")
    print(f"Current Location: {asset_info['parent']}")
    print(f"\nDestination folder:")
    print(f"Reference: {destination_info['reference']}")
    print(f"Title: {destination_info['title']}")
    print(f"Path: {destination_info['path']}")

    response = input(
        "\nAre you sure you want to move this asset? (yes/no): ").lower()
    return response == 'yes'


def move_asset(client, asset_ref, destination_ref, force=False, skip_confirmation=False):
    """Move a single asset to the destination folder and return True if successful."""
    try:
        # Get asset and destination folder info for confirmation
        asset_info = get_asset_info(client, asset_ref)
        destination_info = get_folder_info(client, destination_ref)
        
        if not asset_info:
            logging.error(f"Could not get information for asset {asset_ref}")
            return False
        if not destination_info:
            logging.error(f"Could not get information for destination folder {destination_ref}")
            return False

        # Confirm move unless force is True or skip_confirmation is True
        if not force and not skip_confirmation and not confirm_move(asset_info, destination_info):
            logging.info(f"Skipping move of asset {asset_ref}")
            return True

        # Proceed with move
        logging.info(f"Moving asset {asset_ref} to folder {destination_ref}")
        try:
            # Use the asset object we already retrieved
            asset = asset_info['asset']
            dest_folder = client.folder(destination_ref)
            client.move(asset, dest_folder)
            logging.info(f"Successfully moved asset {asset_ref} to folder {destination_ref}")
            return True
        except Exception as move_error:
            error_msg = str(move_error)
            logging.error(f"Error moving asset {asset_ref}: {error_msg}")
            return False

    except Exception as e:
        logging.error(f"Error processing asset {asset_ref}: {e}", exc_info=True)
        return False


def main(args):
    # Setup logging first
    log_file = setup_logging(args.log_dir)
    logging.info(f"Starting move process. Log file: {log_file}")

    if args.force:
        logging.warning("Force mode enabled - skipping confirmation prompts!")

    # Verify environment variables
    required_env_vars = ['USERNAME', 'PASSWORD', 'TENANT', 'SERVER']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logging.error(
            f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    # Verify destination folder exists
    client = EntityAPI(username=USERNAME, password=PASSWORD,
                       tenant=TENANT, server=SERVER)

    destination_info = get_folder_info(client, args.destination)
    if not destination_info:
        logging.error(
            f"Destination folder {args.destination} not found or not accessible")
        sys.exit(1)

    logging.info(
        f"Moving assets to folder: {destination_info['title']} ({destination_info['path']})")

    error_count = 0
    start_time = datetime.now()

    try:
        if args.asset:
            if not move_asset(client, args.asset, args.destination, args.force):
                error_count += 1

        elif args.assets_file:
            asset_ids = read_asset_list(args.assets_file)
            total_assets = len(asset_ids)
            successful_moves = 0
            
            logging.info(f"Found {total_assets} assets to process")
            
            # If not in force mode, show summary and get confirmation
            if not args.force:
                print(f"\nFound {total_assets} assets to move to folder: {destination_info['title']}")
                for asset_id in asset_ids:
                    asset_info = get_asset_info(client, asset_id)
                    if asset_info:
                        print(f"- {asset_info['reference']}: {asset_info['title']} (from {asset_info['parent']})")
                
                response = input(f"\nAre you sure you want to move these {total_assets} assets? (yes/no): ").lower()
                if response != 'yes':
                    logging.info("Bulk move cancelled by user")
                    sys.exit(0)
            
            for i, asset_id in enumerate(asset_ids, 1):
                logging.info(f"Processing asset {i}/{total_assets}: {asset_id}")
                # Skip individual confirmations when using assets-file
                if move_asset(client, asset_id, args.destination, args.force, skip_confirmation=True):
                    successful_moves += 1
                else:
                    error_count += 1
            
            logging.info(f"Successfully moved {successful_moves} out of {total_assets} assets")

    except KeyboardInterrupt:
        logging.warning("\nMove process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        duration = datetime.now() - start_time
        logging.info(f"Move process completed in {duration}")
        if error_count != 0:
            logging.error(
                f"Encountered {error_count} errors. Please check the log file: {log_file}")
            sys.exit(1)
        else:
            logging.info("Move process completed successfully")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Move assets in Preservica to a specified folder (e.g., a recycle bin).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)

    # Create a group for the mutually exclusive asset specification options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--asset',
                       help='Single Preservica asset ID to move')
    group.add_argument('--assets-file',
                       help='Path to a text file containing Preservica asset IDs to move (one per line)')

    # Required arguments
    parser.add_argument('--destination',
                        required=True,
                        help='Preservica folder ID where assets will be moved to')

    # Optional arguments
    parser.add_argument('--log-dir',
                        help='Directory to store log files (default: current directory)')
    parser.add_argument('--force',
                        action='store_true',
                        help='Skip confirmation prompts (use with caution!)')

    args = parser.parse_args()
    main(args)
