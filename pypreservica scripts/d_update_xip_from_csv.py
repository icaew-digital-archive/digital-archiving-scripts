#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Update Preservica assets (title and description) and security tags from CSV file.
"""

import argparse
import csv
import os
from dotenv import load_dotenv
from pyPreservica import EntityAPI
import logging

# Load environment variables from .env file
load_dotenv(override=True)

# Retrieve environment variables and check if they are set
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TENANT = os.getenv('TENANT')
SERVER = os.getenv('SERVER')

if not all([USERNAME, PASSWORD, TENANT, SERVER]):
    raise EnvironmentError(
        "Required environment variables (USERNAME, PASSWORD, TENANT, SERVER) are not all set")

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_assets_from_csv(client, csv_file):
    with open(csv_file, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            asset_id = row['assetId']
            new_title = row['entity.title']
            new_description = row['entity.description']
            new_security_tag = row['asset.security_tag']
            entity_type = row['entity.entity_type']

            if entity_type == 'EntityType.FOLDER':
                asset = client.folder(asset_id)
            if entity_type == 'EntityType.ASSET':
                asset = client.asset(asset_id)

            try:
                metadata_updated = False
                security_tag_updated = False

                # Check and update title
                if (asset.title or "") != (new_title or ""):
                    asset.title = new_title
                    metadata_updated = True

                # Check and update description
                if (asset.description or "") != (new_description or ""):
                    asset.description = new_description
                    metadata_updated = True

                # Check and update security tag
                if asset.security_tag != new_security_tag:
                    try:
                        client.security_tag_async(asset, new_security_tag)
                        security_tag_updated = True
                        logger.info(
                            f"Security Tag update for asset {asset_id} initiated with tag '{new_security_tag}'")
                    except Exception as e:
                        logger.error(
                            f"Failed to initiate security tag update for asset {asset_id}: {e}")

                # Save asset if metadata was updated
                if metadata_updated:
                    asset = client.save(asset)
                    logger.info(
                        f"Updated asset {asset_id}: Title set to '{new_title}', Description set to '{new_description}'")

                if not metadata_updated and not security_tag_updated:
                    logger.info(f"No updates required for asset {asset_id}")

            except Exception as e:
                logger.error(f"Failed to update asset {asset_id}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update Preservica assets from CSV file")
    parser.add_argument(
        '--csv_input', required=True, help="Path to the CSV file containing asset updates")
    args = parser.parse_args()

    # Initialize the Preservica API client
    client = EntityAPI(username=USERNAME, password=PASSWORD,
                       tenant=TENANT, server=SERVER)

    # Update assets from CSV
    update_assets_from_csv(client, args.csv_input)
