#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Get a list of assets/folders from a given folder reference number and produce a 
CSV template for use with add_metadata_from_csv.py / update_metadata_from_csv.py
"""

import csv
import os

from dotenv import load_dotenv
from pyPreservica import *

# Override is needed as the function will load local username instead of from the .env file
load_dotenv(override=True)

USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TENANT = os.getenv('TENANT')
SERVER = os.getenv('SERVER')

FOLDER_REF = '5db21e22-1f33-48b5-88c1-a74adbdfe264'
CSV_OUTPUT_FILENAME = 'dublincore.csv'

client = EntityAPI(username=USERNAME,
                   password=PASSWORD, tenant=TENANT, server=SERVER)

folder = client.folder(FOLDER_REF)

# CSV header
header = ['assetId', 'entity type', 'file extension', 'title', 'dc:title',
          'dc:creator', 'dc:subject', 'dc:description', 'dc:publisher',
          'dc:contributor', 'dc:date', 'dc:type', 'dc:format', 'dc:identifier',
          'dc:source', 'dc:language', 'dc:relation', 'dc:coverage', 'dc:rights']

# Write CSV file
with open(CSV_OUTPUT_FILENAME, 'w', encoding='UTF8', newline='') as f:
    writer = csv.writer(f, delimiter=',', quotechar='"',
                        quoting=csv.QUOTE_MINIMAL)
    # Write header
    writer.writerow(header)

    # Write rows from Preservica API requests / remove filter to include folders
    for asset in client.all_descendants(folder.reference):
        """
        Remove argument from client.all_descendants(folder.reference) to get to 
        root folder.
        Add filter(only_assets, client.all_descendants(folder.reference)) to get
        assets only.
        """
        if str(asset.entity_type) == 'EntityType.ASSET':
            for representation in client.representations(asset):
                for content_object in client.content_objects(representation):
                    for generation in client.generations(content_object):
                        for bitstream in generation.bitstreams:
                            _, file_extension = os.path.splitext(
                                bitstream.filename)  # get filename extension
        if str(asset.entity_type) == 'EntityType.FOLDER':
            file_extension = ''
        writer.writerow([asset.reference, asset.entity_type,
                        file_extension, asset.title])
