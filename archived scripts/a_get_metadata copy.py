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
from collections import defaultdict, Counter

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
client = EntityAPI(username=USERNAME, password=PASSWORD,
                   tenant=TENANT, server=SERVER)

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

# Define initial CSV header (excluding dynamically generated Dublin Core fields)
csv_header = ['entity.title', 'entity.description',
              'entity.entity_type', 'asset.security_tag', 'assetId']

# Function to extract DC elements and handle repeating fields


def extract_dc_elements_and_update_header(xml_string, max_counts):
    if xml_string is not None:
        root = ET.fromstring(xml_string)
        counts = Counter(child.tag.split('}')[-1] for child in root)
        for tag, count in counts.items():
            dc_field = f"dc:{tag}"
            if count > max_counts[dc_field]:
                max_counts[dc_field] = count
    return max_counts


# Gather max counts of unique DC fields
max_counts = defaultdict(int)
for entity in client.all_descendants(args.preservica_folder_ref):
    xml_string = client.metadata_for_entity(
        entity, 'http://www.openarchives.org/OAI/2.0/oai_dc/')
    max_counts = extract_dc_elements_and_update_header(xml_string, max_counts)

# Update CSV header with unique DC fields, handling repeats
extended_headers = []
for field, count in max_counts.items():
    extended_headers.extend([field] * count)

csv_header.extend(extended_headers)

# Open CSV file for writing
with open(args.csv_output, 'w', encoding='UTF8', newline='') as csv_file:
    csv_writer = csv.writer(csv_file, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
    csv_writer.writerow(csv_header)

    # Iterate through entities and retrieve metadata
    for entity in client.all_descendants(args.preservica_folder_ref):
        if str(entity.entity_type) == 'EntityType.FOLDER':
            asset = client.folder(entity.reference)
        if str(entity.entity_type) == 'EntityType.ASSET':
            asset = client.asset(entity.reference)

        xml_string = client.metadata_for_entity(
            entity, 'http://www.openarchives.org/OAI/2.0/oai_dc/')
        dc_values = defaultdict(list)

        if xml_string is not None:
            root = ET.fromstring(xml_string)
            for child in root:
                tag = child.tag.split('}')[-1]
                dc_field = f"dc:{tag}"
                if child.text:
                    dc_values[dc_field].append(child.text)

        row_data = [
            asset.title, asset.description, asset.entity_type,
            asset.security_tag, asset.reference
        ]

        for header in csv_header[5:]:
            if dc_values[header]:
                row_data.append(dc_values[header].pop(0))
            else:
                row_data.append('')

        csv_writer.writerow(row_data)

    print("CSV file has been written successfully.")
