#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Download Preservica assets from a given parent folder.

Enter "root" as argument to preservica_folder_ref if needing to download from the root level.

usage: download_preservica_assets.py [-h] preservica_folder_ref download_folder
"""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from pyPreservica import *

# Load configuration from environment variables
load_dotenv(override=True)
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TENANT = os.getenv('TENANT')
SERVER = os.getenv('SERVER')


def main(args):
    if not os.path.exists(args.download_folder):
        os.makedirs(args.download_folder)

    client = EntityAPI(username=USERNAME, password=PASSWORD,
                       tenant=TENANT, server=SERVER)

    # Deal with special root case
    if args.preservica_folder_ref == 'root':
        args.preservica_folder_ref = None

    for asset in filter(only_assets, client.all_descendants(args.preservica_folder_ref)):
        print(f'Downloading {asset.title} ({asset.reference})')

        for representation in client.representations(asset):
            for content_object in client.content_objects(representation):
                for generation in client.generations(content_object):
                    for bitstream in generation.bitstreams:
                        download_path = Path(
                            args.download_folder) / bitstream.filename
                        try:
                            client.bitstream_content(bitstream, download_path)
                        except Exception as e:
                            print(
                                f"Error downloading {bitstream.filename}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download Preservica assets from a given parent folder")
    parser.add_argument("preservica_folder_ref",
                        help="Preservica folder reference. Example: \"bb45f999-7c07-4471-9c30-54b057c500ff\". Enter \"root\" if needing to get metadata from the root folder")
    parser.add_argument("download_folder",
                        help="Folder to save the downloaded assets")
    args = parser.parse_args()

    main(args)
