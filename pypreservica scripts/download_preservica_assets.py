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

# Configure logging to console (INFO level)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')

# Configure logging to a file (ERROR level and above)
file_handler = logging.FileHandler('error_log.txt')
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s'))

# Add the file handler to the root logger
logging.getLogger().addHandler(file_handler)


def calculate_file_hash(file_path, hash_algorithm):
    hash_obj = hashlib.new(hash_algorithm)
    with open(file_path, 'rb') as file:
        for byte_block in iter(lambda: file.read(4096), b""):
            hash_obj.update(byte_block)
    return hash_obj.hexdigest()


def download_bitstream(client, bitstream, download_path):
    try:
        client.bitstream_content(bitstream, download_path)
        return True
    except Exception as e:
        # Log the error
        logging.error(
            f"Error downloading {bitstream.filename}: {e}", exc_info=True)
        return False


def check_fixity(downloaded_path, preservica_hash, algorithm, bitstream_filename):
    if preservica_hash:
        downloaded_hash = calculate_file_hash(downloaded_path, algorithm)
        if downloaded_hash == preservica_hash:
            logging.info(
                f"Fixity values match ({algorithm.upper()}: {preservica_hash})")
            return True
        else:
            logging.error(
                f"Fixity values did not match for - {bitstream_filename}.")
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

    error_count = 0

    for asset in filter(only_assets, client.all_descendants(args.preservica_folder_ref)):

        for representation in client.representations(asset):
            for content_object in client.content_objects(representation):
                for generation in client.generations(content_object):
                    for bitstream in generation.bitstreams:
                        for algorithm, value in bitstream.fixity.items():
                            # calculate_file_hash() takes an algorithm arg as lowercase
                            algorithm = algorithm.lower()
                            value = value.lower()  # Checksums are case insenstive

                        download_path = os.path.join(
                            args.download_folder, bitstream.filename)

                        if os.path.exists(download_path):
                            if value == calculate_file_hash(download_path, algorithm):
                                logging.info(
                                    f"{bitstream.filename} already exists locally with matching {algorithm}.")
                            else:
                                logging.info(
                                    f"{bitstream.filename} already exists locally but the {algorithm} does not match.")
                                logging.info(
                                    f'Re-downloading {bitstream.filename} ({asset.reference})')
                                if download_bitstream(client, bitstream, download_path):
                                    if not check_fixity(download_path, value, algorithm, bitstream.filename):
                                        error_count += 1
                        else:
                            logging.info(
                                f'Downloading {bitstream.filename} ({asset.reference})')
                            if download_bitstream(client, bitstream, download_path):
                                if not check_fixity(download_path, value, algorithm, bitstream.filename):
                                    error_count += 1

    if error_count != 0:
        print(f"Error count: {error_count}. Please check the log file.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download Preservica assets from a given parent folder")
    parser.add_argument("preservica_folder_ref",
                        help="Preservica folder reference. Example: \"bb45f999-7c07-4471-9c30-54b057c500ff\". Enter \"root\" if needing to get metadata from the root folder")
    parser.add_argument("download_folder",
                        help="Folder to save the downloaded assets")
    args = parser.parse_args()

    main(args)
