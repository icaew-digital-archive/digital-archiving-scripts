#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Delete metadata for Preservica assets and folders, either from a CSV file or all descendants of a given folder.

Usage:
    # Delete from CSV
    python b_delete_metadata.py --csv-file path/to/entities.csv

    # Delete all descendants from a folder
    python b_delete_metadata.py --preservica_folder_ref FOLDER_ID
"""
import argparse
import os
import csv
import logging
from datetime import datetime
from pathlib import Path
from enum import Enum

from dotenv import load_dotenv
from pyPreservica import EntityAPI

# Load environment variables from .env file
load_dotenv(override=True)
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TENANT = os.getenv('TENANT')
SERVER = os.getenv('SERVER')

class EntityTypeEnum(Enum):
    ASSET = 'asset'
    FOLDER = 'folder'

def setup_logging(log_dir=None):
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f'preservica_metadata_deletion_{timestamp}.log'
    else:
        log_file = 'metadata_deletion_log.txt'
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    return log_file

def read_entities_from_csv(csv_file):
    """Read asset IDs from the CSV file. Only requires 'assetId' column."""
    asset_ids = []
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            if 'assetId' not in reader.fieldnames:
                raise ValueError("CSV file must contain a column: 'assetId'")
            for row in reader:
                entity_id = row['assetId'].strip()
                if entity_id:
                    asset_ids.append(entity_id)
        if not asset_ids:
            raise ValueError("No valid asset IDs found in the CSV file")
        return asset_ids
    except Exception as e:
        logging.error(f"Error reading CSV file: {e}", exc_info=True)
        raise

def delete_entity_metadata_auto(client, entity_id):
    """Fetch entity type from API and delete metadata accordingly."""
    try:
        try:
            entity = client.asset(entity_id)
            entity_type = 'asset'
        except Exception:
            entity = client.folder(entity_id)
            entity_type = 'folder'
        client.delete_metadata(entity, 'http://www.openarchives.org/OAI/2.0/oai_dc/')
        return True, entity_type
    except Exception as e:
        logging.error(f"Failed to delete metadata for entity {entity_id}: {e}", exc_info=True)
        return False, None

def delete_from_csv(client, csv_file):
    asset_ids = read_entities_from_csv(csv_file)
    total = len(asset_ids)
    logging.info(f"Found {total} entities to process from CSV.")

    # Fetch entity info and prepare summary
    entity_summaries = []
    for entity_id in asset_ids:
        try:
            try:
                entity = client.asset(entity_id)
                entity_type = 'asset'
            except Exception:
                entity = client.folder(entity_id)
                entity_type = 'folder'
            title = getattr(entity, 'title', '')
            entity_summaries.append((entity_id, entity_type, title))
        except Exception as e:
            logging.error(f"Could not fetch entity {entity_id}: {e}")
            entity_summaries.append((entity_id, 'unknown', 'ERROR FETCHING'))

    # Print summary table
    print("\nThe following entities will have their metadata removed:")
    print(f"{'ID':<40} {'Type':<8} Title")
    print("-" * 80)
    for eid, etype, title in entity_summaries:
        print(f"{eid:<40} {etype:<8} {title}")
    print("-" * 80)

    confirmation = input(f"Are you sure you want to delete metadata for these {total} entities? (Y/N): ").strip().lower()
    if confirmation != 'y':
        logging.info("Operation cancelled by user")
        return
    success, fail = 0, 0
    for i, (entity_id, entity_type, _) in enumerate(entity_summaries, 1):
        if entity_type == 'unknown':
            fail += 1
            continue
        logging.info(f"Processing entity {i}/{total}: {entity_id}")
        ok, _ = delete_entity_metadata_auto(client, entity_id)
        if ok:
            success += 1
            logging.info(f"Successfully deleted metadata for {entity_type}: {entity_id}")
        else:
            fail += 1
    logging.info(f"Metadata deletion completed: {success} succeeded, {fail} failed.")

def delete_from_folder(client, folder_ref):
    descendants = list(client.all_descendants(folder_ref))
    total = len(descendants)
    # Prepare summary
    entity_summaries = []
    for entity in descendants:
        try:
            entity_type = 'asset' if str(entity.entity_type) == 'EntityType.ASSET' else 'folder'
            title = getattr(entity, 'title', '')
            entity_summaries.append((entity.reference, entity_type, title))
        except Exception as e:
            logging.error(f"Could not fetch entity {getattr(entity, 'reference', '?')}: {e}")
            entity_summaries.append((getattr(entity, 'reference', '?'), 'unknown', 'ERROR FETCHING'))

    # Print summary table
    print("\nThe following entities will have their metadata removed:")
    print(f"{'ID':<40} {'Type':<8} Title")
    print("-" * 80)
    for eid, etype, title in entity_summaries:
        print(f"{eid:<40} {etype:<8} {title}")
    print("-" * 80)

    confirmation = input(f'Are you sure you want to delete the metadata for these {total} entities? (Y/N): ').strip().lower()
    if confirmation != 'y':
        logging.info("Operation cancelled by user")
        return
    success, fail = 0, 0
    for i, (entity_id, entity_type, _) in enumerate(entity_summaries, 1):
        if entity_type == 'unknown':
            fail += 1
            continue
        logging.info(f"Deleting metadata for {entity_type} {i}/{total}: {entity_id}")
        try:
            if entity_type == 'folder':
                obj = client.folder(entity_id)
            else:
                obj = client.asset(entity_id)
            client.delete_metadata(obj, 'http://www.openarchives.org/OAI/2.0/oai_dc/')
            success += 1
        except Exception as e:
            logging.error(f"Failed to delete metadata for {entity_type} {entity_id}: {e}", exc_info=True)
            fail += 1
    logging.info(f"Metadata deletion completed: {success} succeeded, {fail} failed.")

def main():
    parser = argparse.ArgumentParser(description='Delete metadata from Preservica assets/folders via CSV or folder reference.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--csv-file', help='Path to CSV file containing assetId and entity.entity_type columns')
    group.add_argument('--preservica_folder_ref', help='Preservica folder reference (delete all descendants)')
    parser.add_argument('--log-dir', help='Directory to store log files (default: current directory)')
    args = parser.parse_args()
    log_file = setup_logging(args.log_dir)
    logging.info(f"Starting metadata deletion process. Log file: {log_file}")
    required_env_vars = ['USERNAME', 'PASSWORD', 'TENANT', 'SERVER']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return
    client = EntityAPI(username=USERNAME, password=PASSWORD, tenant=TENANT, server=SERVER)
    try:
        if args.csv_file:
            delete_from_csv(client, args.csv_file)
        elif args.preservica_folder_ref:
            delete_from_folder(client, args.preservica_folder_ref)
    except KeyboardInterrupt:
        logging.warning("\nProcess interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)

if __name__ == "__main__":
    main() 