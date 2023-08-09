#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Deletes metadata for child folders/assets given a Preservica folder reference.

usage: b_delete_metadata.py [-h] preservica_folder_ref
"""

import argparse
import os

from dotenv import load_dotenv
from pyPreservica import EntityAPI

# Load environment variables from .env file
load_dotenv(override=True)

# Retrieve environment variables
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TENANT = os.getenv('TENANT')
SERVER = os.getenv('SERVER')

# Initialize Preservica API client
client = EntityAPI(username=USERNAME,
                   password=PASSWORD, tenant=TENANT, server=SERVER)

# Define command-line arguments
parser = argparse.ArgumentParser(
    description='Delete metadata from Preservica assets.')
parser.add_argument('preservica_folder_ref',
                    help='Preservica folder reference')

# Parse command-line arguments
args = parser.parse_args()

confirmation = input(
    f"Are you sure you want to delete the metadata for assets in the folder: \"{client.folder(args.preservica_folder_ref).title}\"? (Y/N): ").strip().lower()

if confirmation == 'y':

    for entity in client.all_descendants(args.preservica_folder_ref):
        print(f"Deleting metadata for assetID: {entity.reference}")
        if str(entity.entity_type) == 'EntityType.FOLDER':
            asset = client.folder(entity.reference)
            client.delete_metadata(
                asset, 'http://www.openarchives.org/OAI/2.0/oai_dc/')
        if str(entity.entity_type) == 'EntityType.ASSET':
            asset = client.asset(entity.reference)
            client.delete_metadata(
                asset, 'http://www.openarchives.org/OAI/2.0/oai_dc/')
