#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to export metadata and checksum values to CSV from a Preservica folder.

Usage: 
    a_get_metadata.py [-h] --preservica_folder_ref --metadata_csv METADATA_CSV [--new_template]

Options:
    --preservica_folder_ref      Preservica folder reference. Example: "bb45f999-7c07-4471-9c30-54b057c500ff". Enter "root" if needing to get metadata from the root folder
    --metadata_csv METADATA_CSV  Output CSV filename for metadata and checksums
    --new_template               Flag to use new template with extended Dublin Core elements
"""

import argparse
import csv
import os
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter
import logging
from dotenv import load_dotenv
from pyPreservica import EntityAPI, only_assets

# Set up logging to file and console
log_file = "errors.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w'),
        logging.StreamHandler()
    ]
)

# Global error counter
error_count = 0


def load_env_variables():
    logging.info("Loading environment variables from .env file")
    load_dotenv(override=True)
    username = os.getenv('USERNAME')
    password = os.getenv('PASSWORD')
    tenant = os.getenv('TENANT')
    server = os.getenv('SERVER')

    if not username or not password or not tenant or not server:
        logging.error(
            "One or more environment variables are missing. Please check the .env file.")
        exit(1)

    return username, password, tenant, server


def initialize_client(username, password, tenant, server):
    logging.info("Initializing Preservica API client")
    try:
        client = EntityAPI(username=username, password=password,
                           tenant=tenant, server=server)
        return client
    except Exception as e:
        global error_count
        logging.error(f"Failed to initialize Preservica API client: {e}")
        error_count += 1
        exit(1)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Export metadata and checksums to CSV from Preservica.')
    parser.add_argument('--preservica_folder_ref', required=True,
                        help='Preservica folder reference. Example: "bb45f999-7c07-4471-9c30-54b057c500ff". Enter "root" if needing to get metadata from the root folder')
    parser.add_argument('--metadata_csv', required=True,
                        help='Output CSV filename for metadata and checksums')
    parser.add_argument('--new_template', action='store_true',
                        help='Flag to use new template with extended Dublin Core elements')
    args = parser.parse_args()
    if args.preservica_folder_ref == 'root':
        args.preservica_folder_ref = None
    return args


def extract_dc_elements_and_update_header(xml_string, max_counts):
    if xml_string is not None:
        root = ET.fromstring(xml_string)
        counts = Counter(child.tag.split('}')[-1] for child in root)
        for tag, count in counts.items():
            dc_field = f"dc:{tag}"
            if count > max_counts[dc_field]:
                max_counts[dc_field] = count
    return max_counts


def get_all_descendants_with_logging(client, folder_ref):
    logging.info(
        f"Starting retrieval of descendants for folder reference: {folder_ref}")
    descendants = list(client.all_descendants(folder_ref))
    logging.info(
        f"Completed retrieval of descendants. Total items retrieved: {len(descendants)}")
    return descendants


def retrieve_metadata_and_checksums(client, descendants, csv_writer, csv_header, new_template):
    global error_count
    available_algorithms = set()
    all_rows = []  # Store all rows until we know all algorithms

    for entity in descendants:
        if str(entity.entity_type) == 'EntityType.FOLDER':
            asset = client.folder(entity.reference)
        elif str(entity.entity_type) == 'EntityType.ASSET':
            asset = client.asset(entity.reference)
        else:
            continue

        logging.info(
            f"Getting metadata and checksum for assetID: {asset.reference}")

        try:
            xml_string = client.metadata_for_entity(
                entity, 'http://www.openarchives.org/OAI/2.0/oai_dc/')
        except Exception as e:
            logging.error(
                f"Skipping metadata for entity {entity.reference}: {e}")
            error_count += 1
            continue

        dc_values = defaultdict(list)

        if xml_string is not None:
            root = ET.fromstring(xml_string)
            for child in root:
                tag = child.tag.split('}')[-1]
                dc_field = f"dc:{tag}"
                if child.text:
                    dc_values[dc_field].append(child.text)

        # Create base row data with metadata
        base_row_data = [asset.reference, asset.entity_type, asset.security_tag, asset.title, asset.description]

        # Add DC values if not using new template
        if not new_template:
            for header in csv_header[5:]:  # Start after the base metadata columns
                if dc_values[header]:
                    base_row_data.append(dc_values[header].pop(0))
                else:
                    base_row_data.append('')

        # Collect all checksum values
        checksum_values = defaultdict(list)
        for representation in client.representations(asset):
            for content_object in client.content_objects(representation):
                try:
                    for generation in client.generations(content_object):
                        for bitstream in generation.bitstreams:
                            for algorithm in bitstream.fixity.keys():
                                available_algorithms.add(algorithm)
                                checksum_values[algorithm].append(bitstream.fixity[algorithm])
                except Exception as e:
                    logging.error(f"Error processing asset {asset.title}: {e}")
                    error_count += 1

        # Store the row data and checksums for later writing
        all_rows.append((base_row_data, checksum_values))

    # Now that we know all algorithms, create the final header
    checksum_headers = [f'{alg} checksum' for alg in sorted(available_algorithms)]
    final_header = ['assetId'] + checksum_headers + ['entity.entity_type', 'asset.security_tag', 'entity.title', 'entity.description']
    if not new_template:
        final_header.extend(csv_header[5:])  # Add DC headers
    csv_writer.writerow(final_header)

    # Write all rows with the complete set of checksum columns
    for base_row_data, checksum_values in all_rows:
        # Insert checksum values in the correct positions
        row_data = [base_row_data[0]]  # Start with assetId
        for algorithm in sorted(available_algorithms):
            row_data.append(checksum_values[algorithm][0] if checksum_values[algorithm] else '')
        row_data.extend(base_row_data[1:])  # Add the rest of the metadata
        csv_writer.writerow(row_data)

        # Write additional rows if there are multiple checksums
        max_checksums = max(len(checksums) for checksums in checksum_values.values())
        for i in range(1, max_checksums):
            blank_row = [''] * len(final_header)
            blank_row[0] = base_row_data[0]  # Keep the assetId
            for j, algorithm in enumerate(sorted(available_algorithms), start=1):
                blank_row[j] = checksum_values[algorithm][i] if i < len(checksum_values[algorithm]) else ''
            csv_writer.writerow(blank_row)


def main():
    global error_count

    username, password, tenant, server = load_env_variables()
    client = initialize_client(username, password, tenant, server)
    args = parse_arguments()

    logging.info("Retrieving all descendants of the specified folder")
    try:
        descendants = get_all_descendants_with_logging(
            client, args.preservica_folder_ref)

        # Initial header for DC metadata collection
        csv_header = ['assetId', 'entity.entity_type', 'asset.security_tag', 'entity.title', 'entity.description']
        max_counts = defaultdict(int)

        for entity in descendants:
            try:
                xml_string = client.metadata_for_entity(
                    entity, 'http://www.openarchives.org/OAI/2.0/oai_dc/')
                max_counts = extract_dc_elements_and_update_header(
                    xml_string, max_counts)
            except Exception as e:
                logging.error(
                    f"Skipping entity {entity.reference} due to metadata error: {e}")
                error_count += 1

        extended_headers = []
        for field, count in max_counts.items():
            extended_headers.extend([field] * count)

        if args.new_template:
            extended_headers = ['dc:title', 'dc:creator', 'dc:subject', 'dc:description', 'dc:publisher', 'dc:contributor', 'dc:date',
                              'dc:type', 'dc:type', 'dc:format', 'dc:identifier', 'dc:source', 'dc:language', 'dc:relation', 'dc:coverage', 'dc:rights']

        csv_header.extend(extended_headers)

        logging.info(f"Opening {args.metadata_csv} for writing")
        with open(args.metadata_csv, 'w', encoding='UTF8', newline='') as metadata_csv_file:
            csv_writer = csv.writer(
                metadata_csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

            logging.info("Processing entities and writing to CSV")
            retrieve_metadata_and_checksums(
                client, descendants, csv_writer, csv_header, args.new_template)

        logging.info(
            f"Metadata and checksums have been written to {args.metadata_csv}")

        # Final error summary
        if error_count > 0:
            print(f"\n{error_count} errors occurred. Check '{log_file}' for details.")
        else:
            print("\nScript completed with no errors.")

    except Exception as e:
        logging.error(f"Error retrieving descendants: {e}")
        error_count += 1
        exit(1)


if __name__ == '__main__':
    main()
