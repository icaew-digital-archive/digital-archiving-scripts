#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gets asset information and metadata for child folders/assets given a Preservica folder reference.

Enter "root" as argument to preservica_folder_ref if needing to get metadata from the root folder.

usage: a_get_metadata.py [-h] preservica_folder_ref csv_output
"""

import argparse
import csv
import os
import xml.etree.ElementTree as ET

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
    description='Export metadata to CSV from Preservica.')
parser.add_argument('preservica_folder_ref',
                    help='Preservica folder reference. Example: "bb45f999-7c07-4471-9c30-54b057c500ff". Enter "root" if needing to get metadata from the root folder')
parser.add_argument('csv_output', help='Output CSV filename')

# Parse command-line arguments
args = parser.parse_args()

# Deal with special root case
if args.preservica_folder_ref == 'root':
    args.preservica_folder_ref = None

# Define CSV header
csv_header = ['entity.title', 'entity.entity_type', 'asset.security_tag', 'assetId', 'dc:title', 'dc:creator', 'dc:subject', 'dc:description',
              'dc:publisher', 'dc:contributor', 'dc:date', 'dc:type', 'dc:format', 'dc:identifier', 'dc:source',
              'dc:language', 'dc:relation', 'dc:coverage', 'dc:rights']

# Open CSV file for writing
with open(args.csv_output, 'w', encoding='UTF8', newline='') as csv_file:
    csv_writer = csv.writer(csv_file, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
    csv_writer.writerow(csv_header)

    # Iterate through entities and retrieve metadata
    for entity in client.all_descendants(args.preservica_folder_ref):
        xml_string = client.metadata_for_entity(
            entity, 'http://www.openarchives.org/OAI/2.0/oai_dc/')

        if xml_string is not None:
            root = ET.fromstring(xml_string)
            item_list = [item.text for item in root]
        else:
            item_list = []

        # To enable the retrieval of the security_tag
        if str(entity.entity_type) == 'EntityType.FOLDER':
            asset = client.folder(entity.reference)
        if str(entity.entity_type) == 'EntityType.ASSET':
            asset = client.asset(entity.reference)

        print(f"Writing assetId: {entity.reference} to CSV.")
        row_data = [entity.title, entity.entity_type,
                    asset.security_tag, entity.reference] + item_list
        csv_writer.writerow(row_data)

    print("WARNING: The CSV output will require manual column realignment if there are repeating Dublin Core elements.")
