#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Download Preservica assets from a given parent folder. Checks that fixity values from Preservica and local file match.

Enter "root" as argument to preservica_folder_ref if needing to download from the root level.

usage: download_preservica_assets.py [-h] preservica_folder_ref download_folder
"""

import argparse
import os
from pathlib import Path
import hashlib
import logging

from dotenv import load_dotenv
from pyPreservica import *

# Load configuration from environment variables
load_dotenv(override=True)
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TENANT = os.getenv('TENANT')
SERVER = os.getenv('SERVER')

# Configure logging
# You can set the level according to your needs
logging.basicConfig(level=logging.INFO)


def calculate_file_hash(file_path, hash_algorithm):
    hash_obj = hashlib.new(hash_algorithm)
    with open(file_path, 'rb') as file:
        for byte_block in iter(lambda: file.read(4096), b""):
            hash_obj.update(byte_block)
    return hash_obj.hexdigest()


def download_bitstream(client, bitstream, download_path):
    try:
        client.bitstream_content(bitstream, download_path)
    except Exception as e:
        logging.error(f"Error downloading {bitstream.filename}: {e}")


def check_fixity(downloaded_path, preservica_hash, algorithm):
    if preservica_hash:
        downloaded_hash = calculate_file_hash(downloaded_path, algorithm)
        if downloaded_hash == preservica_hash:
            logging.info(
                f"Fixity values match ({algorithm.upper()}: {preservica_hash})")
            return True
        else:
            logging.error('Fixity values did not match.')
            return False
    return True


def main(args):
    if not os.path.exists(args.download_folder):
        os.makedirs(args.download_folder)

    client = EntityAPI(username=USERNAME, password=PASSWORD,
                       tenant=TENANT, server=SERVER)

    # Deal with special root case
    if args.preservica_folder_ref == 'root':
        args.preservica_folder_ref = None

    for asset in filter(only_assets, client.all_descendants(args.preservica_folder_ref)):
        logging.info(f'Downloading {asset.title} ({asset.reference})')

        for representation in client.representations(asset):
            for content_object in client.content_objects(representation):
                for generation in client.generations(content_object):
                    for bitstream in generation.bitstreams:
                        for algorithm, value in bitstream.fixity.items():
                            algorithm = algorithm.lower()

                        download_path = os.path.join(
                            args.download_folder, bitstream.filename)

                        download_bitstream(client, bitstream, download_path)
                        if not check_fixity(download_path, value, algorithm):
                            sys.exit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download Preservica assets from a given parent folder")
    parser.add_argument("preservica_folder_ref",
                        help="Preservica folder reference. Example: \"bb45f999-7c07-4471-9c30-54b057c500ff\". Enter \"root\" if needing to get metadata from the root folder")
    parser.add_argument("download_folder",
                        help="Folder to save the downloaded assets")
    args = parser.parse_args()

    main(args)
