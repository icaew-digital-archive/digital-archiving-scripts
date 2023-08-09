#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Rough script to get the Title field from the metadata schema.
"""

import os
import xml.etree.ElementTree as ET

from dotenv import load_dotenv
from pyPreservica import *

# Override is needed as the function will load local username instead of from the .env file
load_dotenv(override=True)

USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TENANT = os.getenv('TENANT')
SERVER = os.getenv('SERVER')

client = EntityAPI(username=USERNAME,
                   password=PASSWORD, tenant=TENANT, server=SERVER)

# Get root folders
root_folder_references = []
for entity in client.descendants():
    root_folder_references.append(entity.reference)

# Leave argument empty for root folder
for e in client.all_descendants('e662a4f2-e222-4e47-8569-7fe2d3c557ff'):

    if str(e.entity_type) == 'EntityType.ASSET':
        asset = client.asset(e.reference)
        for url, schema in asset.metadata.items():
            if schema != 'http://preservica.com/LegacyXIP':  # Ignore the LegacyXIP schema
                root = ET.fromstring(client.metadata(url))
                print(root[0].text)  # Title field
