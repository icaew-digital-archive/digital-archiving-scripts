#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Obtains child asset references from below a given parent folder and then downloads the assets individually.
Specifically created to download WARC files.
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

FOLDER_REF = '5b2391ee-b6cb-4091-8339-83d1f56fa38b'

client = EntityAPI(username=USERNAME,
                   password=PASSWORD, tenant=TENANT, server=SERVER)

folder = client.folder(FOLDER_REF)

# Get child assets individually and download them
for asset in filter(only_assets, client.all_descendants(folder.reference)):
    print(f'Downloading {asset.title}...')
    asset = client.asset(asset.reference)
    # Preservica strips the .gz extension from asset.title, this adds it back on
    client.download(asset, asset.title + '.gz')
