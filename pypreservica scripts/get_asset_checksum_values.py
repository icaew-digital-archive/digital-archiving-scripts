#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Obtains checksum values from child assets when given parent folder reference 
number.
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

FOLDER_REF = 'ce1a24c4-9e9e-45b2-b9ad-f3fb748423a2'
CHECKSUM_ALGO = 'MD5'

client = EntityAPI(username=USERNAME,
                   password=PASSWORD, tenant=TENANT, server=SERVER)

folder = client.folder(FOLDER_REF)

for asset in filter(only_assets, client.all_descendants(folder.reference)):
    """
    Remove argument from client.all_descendants(folder.reference) to get to 
    root folder.
    """
    for representation in client.representations(asset):
        for content_object in client.content_objects(representation):
            try:    # getting around embedded content not having own fixity values/bitstream?
                for generation in client.generations(content_object):
                    for bitstream in generation.bitstreams:
                        for algorithm, value in bitstream.fixity.items():
                            if algorithm == CHECKSUM_ALGO:
                                print(value.ljust(40), algorithm.ljust(4),
                                      asset.title)
            except:
                pass
