#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Obtains checksum values from child assets when given a parent folder reference 
number and checksum algorithm via command-line arguments.
"""

import os
import argparse
import csv
import logging
from dotenv import load_dotenv
from pyPreservica import EntityAPI, only_assets

# Initialize logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv(override=True)
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TENANT = os.getenv('TENANT')
SERVER = os.getenv('SERVER')

# Parse command-line arguments
parser = argparse.ArgumentParser(
    description="Obtain checksum values from child assets.")
parser.add_argument('algorithm', type=str, choices=['MD5', 'SHA1', 'SHA256'],
                    help='The checksum algorithm to use (choices: MD5, SHA1, SHA256)')
parser.add_argument('folder_ref', type=str,
                    help='The reference number of the parent folder')
parser.add_argument('output_csv', type=str, help='The output CSV file')
args = parser.parse_args()

FOLDER_REF = args.folder_ref
CHECKSUM_ALGO = args.algorithm
OUTPUT_CSV = args.output_csv

# Initialize client
client = EntityAPI(username=USERNAME, password=PASSWORD,
                   tenant=TENANT, server=SERVER)
folder = client.folder(FOLDER_REF)

# Function to process assets and write checksum values to CSV


def process_assets(folder, output_csv, checksum_algo):
    with open(output_csv, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow([f'{checksum_algo} Checksum', 'Asset Title'])

        for asset in filter(only_assets, client.all_descendants(folder.reference)):
            for representation in client.representations(asset):
                for content_object in client.content_objects(representation):
                    try:
                        for generation in client.generations(content_object):
                            for bitstream in generation.bitstreams:
                                for algorithm, value in bitstream.fixity.items():
                                    if algorithm == checksum_algo:
                                        csvwriter.writerow(
                                            [value, asset.title])
                                        logging.info(
                                            f'Processed asset: {asset.title}')
                    except Exception as e:
                        logging.error(
                            f"Error processing asset {asset.title}: {e}")


# Process assets in the folder and write to CSV
process_assets(folder, OUTPUT_CSV, CHECKSUM_ALGO)
logging.info(f"Checksums have been written to {OUTPUT_CSV}")
