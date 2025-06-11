#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Deletes metadata for specific assets and folders listed in a CSV file.

The CSV file must contain the following columns:
- 'entityId': The Preservica reference ID
- 'entity.entity_type': Either 'asset' or 'folder' (case insensitive)

This script will delete metadata for the exact entities listed in the CSV file.

usage: b_delete_metadata_from_csv.py [-h] --csv-file CSV_FILE
"""

import argparse
import os
import csv
import logging
from datetime import datetime
from pathlib import Path
from enum import Enum

from dotenv import load_dotenv
from pyPreservica import EntityAPI, EntityType

# Load environment variables from .env file
load_dotenv(override=True)

# Retrieve environment variables
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TENANT = os.getenv('TENANT')
SERVER = os.getenv('SERVER')

class EntityTypeEnum(Enum):
    ASSET = 'asset'
    FOLDER = 'folder'

def setup_logging(log_dir=None):
    """Configure logging to both console and file."""
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f'preservica_metadata_deletion_{timestamp}.log'
    else:
        log_file = 'metadata_deletion_log.txt'

    # Configure logging to console (INFO level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

    # Configure logging to file (ERROR level and above)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return log_file

def read_entities(csv_file):
    """Read entity IDs and types from the CSV file."""
    entities = []
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            required_columns = {'assetId', 'entity.entity_type'}
            if not required_columns.issubset(reader.fieldnames):
                raise ValueError("CSV file must contain columns: 'assetId' and 'entity.entity_type'")
            
            for row in reader:
                entity_id = row['assetId'].strip()
                entity_type_raw = row['entity.entity_type'].strip().lower()
                # Normalize entity type
                if entity_type_raw in ['folder', 'entitytype.folder']:
                    entity_type = 'folder'
                elif entity_type_raw in ['asset', 'entitytype.asset']:
                    entity_type = 'asset'
                else:
                    entity_type = entity_type_raw
                
                if not entity_id:  # Skip empty rows
                    continue
                try:
                    entity_type_enum = EntityTypeEnum(entity_type)
                    entities.append((entity_id, entity_type_enum))
                except ValueError:
                    logging.warning(f"Invalid entity type '{entity_type_raw}' for entity {entity_id}. Skipping.")
                    continue
        
        if not entities:
            raise ValueError("No valid entities found in the CSV file")
        return entities
    except Exception as e:
        logging.error(f"Error reading CSV file: {e}", exc_info=True)
        raise

def delete_entity_metadata(client, entity_id, entity_type):
    """Delete metadata for a single entity (asset or folder)."""
    try:
        if entity_type == EntityTypeEnum.ASSET:
            entity = client.asset(entity_id)
        else:  # EntityTypeEnum.FOLDER
            entity = client.folder(entity_id)
            
        client.delete_metadata(entity, 'http://www.openarchives.org/OAI/2.0/oai_dc/')
        return True
    except Exception as e:
        logging.error(f"Failed to delete metadata for {entity_type.value} {entity_id}: {e}", exc_info=True)
        return False

def main():
    # Setup argument parser
    parser = argparse.ArgumentParser(
        description='Delete metadata for assets and folders listed in a CSV file.')
    parser.add_argument('--csv-file', required=True,
                      help='Path to CSV file containing entity IDs and types')
    parser.add_argument('--log-dir',
                      help='Directory to store log files (default: current directory)')
    
    args = parser.parse_args()

    # Setup logging
    log_file = setup_logging(args.log_dir)
    logging.info(f"Starting metadata deletion process. Log file: {log_file}")

    # Verify environment variables
    required_env_vars = ['USERNAME', 'PASSWORD', 'TENANT', 'SERVER']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return

    try:
        # Initialize Preservica API client
        client = EntityAPI(username=USERNAME,
                          password=PASSWORD,
                          tenant=TENANT,
                          server=SERVER)

        # Read entities from CSV
        entities = read_entities(args.csv_file)
        total_entities = len(entities)
        
        # Count entities by type
        asset_count = sum(1 for _, entity_type in entities if entity_type == EntityTypeEnum.ASSET)
        folder_count = sum(1 for _, entity_type in entities if entity_type == EntityTypeEnum.FOLDER)
        
        logging.info(f"Found {total_entities} entities to process:")
        logging.info(f"- {asset_count} assets")
        logging.info(f"- {folder_count} folders")

        # Get confirmation from user
        confirmation = input(
            f"Are you sure you want to delete metadata for {total_entities} entities ({asset_count} assets, {folder_count} folders)? (Y/N): ").strip().lower()

        if confirmation != 'y':
            logging.info("Operation cancelled by user")
            return

        # Process each entity
        successful_deletions = 0
        failed_deletions = 0

        for i, (entity_id, entity_type) in enumerate(entities, 1):
            logging.info(f"Processing {entity_type.value} {i}/{total_entities}: {entity_id}")
            if delete_entity_metadata(client, entity_id, entity_type):
                successful_deletions += 1
                logging.info(f"Successfully deleted metadata for {entity_type.value}: {entity_id}")
            else:
                failed_deletions += 1

        # Log summary
        logging.info(f"Metadata deletion completed:")
        logging.info(f"Successfully processed: {successful_deletions} entities")
        logging.info(f"Failed to process: {failed_deletions} entities")

    except KeyboardInterrupt:
        logging.warning("\nProcess interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)

if __name__ == "__main__":
    main() 