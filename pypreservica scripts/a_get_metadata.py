#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to export metadata, checksum values, and file format information to CSV from a Preservica folder.

This script extracts comprehensive information from Preservica assets including:
- Asset metadata (title, description, security tag, entity type)
- Multiple checksum algorithms (MD5, SHA1, SHA256) by default
- File format information (filename, file size, file extension)
- Full Preservica path from root to asset
- Dublin Core and ICAEW metadata
- Only processes first generation (original ingested) assets

Usage: 
    a_get_metadata.py [-h] --preservica-folder-ref --metadata-csv METADATA_CSV [--algorithm ALGORITHM] [--new-template] [--exclude-folders EXCLUDE_FOLDERS] [--entity-type {assets,folders,both}]

Options:
    --preservica-folder-ref      Preservica folder reference. Example: "bb45f999-7c07-4471-9c30-54b057c500ff". Enter "root" if needing to get metadata from the root folder
    --metadata-csv METADATA_CSV  Output CSV filename for metadata and checksums
    --algorithm ALGORITHM        The checksum algorithm to use (choices: MD5, SHA1, SHA256, ALL) [default: ALL]
    --new-template               Flag to use new template with extended Dublin Core elements
    --exclude-folders            List of folder references to exclude from processing. These folders and their children will be skipped.
    --entity-type                Type of entities to include in output (choices: assets, folders, both) [default: both]

Output CSV Columns:
    ALL algorithm mode:
        assetId, MD5 checksum, SHA1 checksum, SHA256 checksum, entity.entity_type, asset.security_tag, 
        entity.title, entity.description, preservica_path, filename, file_size, file_extension, 
        icaew:ContentType, dc:title, dc:description, dc:date, dc:type, dc:identifier
    
    Single algorithm mode:
        assetId, [ALGORITHM] checksum, entity.entity_type, asset.security_tag, entity.title, 
        entity.description, preservica_path, filename, file_size, file_extension, 
        icaew:ContentType, dc:title, dc:description, dc:date, dc:type, dc:identifier

Features:
    - Extracts all available checksum algorithms by default (MD5, SHA1, SHA256)
    - Includes full Preservica folder path from root to asset
    - Processes only first generation (original ingested) assets
    - Supports exclusion of specific folders and their children
    - Handles both Dublin Core and ICAEW metadata
    - Extracts file format information from bitstreams
    - Provides comprehensive error logging
    - Supports filtering by entity type (assets only, folders only, or both)
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
    parser.add_argument('--preservica-folder-ref', required=True,
                        help='Preservica folder reference. Example: "bb45f999-7c07-4471-9c30-54b057c500ff". Enter "root" if needing to get metadata from the root folder')
    parser.add_argument('--metadata-csv', required=True,
                        help='Output CSV filename for metadata and checksums')
    parser.add_argument('--algorithm', default='ALL', choices=['MD5', 'SHA1', 'SHA256', 'ALL'],
                        help='The checksum algorithm to use (choices: MD5, SHA1, SHA256, ALL) [default: ALL]')
    parser.add_argument('--new-template', action='store_true',
                        help='Flag to use new template with extended Dublin Core elements')
    parser.add_argument('--exclude-folders', nargs='+',
                        help='List of folder references to exclude from processing. These folders and their children will be skipped.')
    parser.add_argument('--entity-type', default='both', choices=['assets', 'folders', 'both'],
                        help='Type of entities to include in output (choices: assets, folders, both) [default: both]')
    args = parser.parse_args()
    
    # Create backward-compatible attribute names for existing code
    args.preservica_folder_ref = getattr(args, 'preservica_folder_ref', None)
    args.metadata_csv = getattr(args, 'metadata_csv', None)
    args.exclude_folders = getattr(args, 'exclude_folders', None)
    args.entity_type = getattr(args, 'entity_type', None)
    args.new_template = getattr(args, 'new_template', None)
    
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


def extract_icaew_elements_and_update_header(xml_string, max_counts):
    if xml_string is not None:
        root = ET.fromstring(xml_string)
        # ICAEW fields are under the ICAEW namespace
        for child in root:
            tag = child.tag.split('}')[-1]
            icaew_field = f"icaew:{tag}"
            if max_counts[icaew_field] < 1:
                max_counts[icaew_field] = 1
    return max_counts


def extract_file_extension(filename):
    """Extract file extension from filename without the period"""
    if filename:
        return os.path.splitext(filename)[1].lower().lstrip('.')
    return ''


def get_full_preservica_path(client, entity):
    """Get the full Preservica path from root to the entity"""
    path_parts = []
    current = entity
    
    try:
        # Get the properly instantiated entity
        if str(entity.entity_type) == 'EntityType.FOLDER':
            current = client.folder(entity.reference)
        else:  # EntityType.ASSET
            current = client.asset(entity.reference)
        
        # Add the current entity's title
        path_parts.append(current.title or current.reference)
        
        # Traverse up the hierarchy
        parent_ref = current.parent
        while parent_ref is not None:
            try:
                parent_folder = client.folder(parent_ref)
                path_parts.append(parent_folder.title or parent_folder.reference)
                parent_ref = parent_folder.parent
            except Exception as e:
                logging.error(f"Error getting parent folder {parent_ref}: {e}")
                path_parts.append(parent_ref)  # Add reference if title unavailable
                break
        
        # Reverse the list to get root-to-leaf order and join with '/'
        path_parts.reverse()
        return '/'.join(path_parts)
        
    except Exception as e:
        logging.error(f"Error building path for {entity.reference}: {e}")
        return entity.reference  # Fallback to reference if path building fails


def get_all_descendants_with_logging(client, folder_ref, exclude_folders=None):
    logging.info(
        f"Starting retrieval of descendants for folder reference: {folder_ref}")

    if exclude_folders is None:
        exclude_folders = []

    # Get all descendants first
    all_descendants = list(client.all_descendants(folder_ref))

    # Create a set of excluded folder references for faster lookup
    excluded_refs = set(exclude_folders)

    # First, identify all entities that should be excluded (including children of excluded folders)
    excluded_entities = set()
    for entity in all_descendants:
        try:
            # Get the entity's parent reference
            if str(entity.entity_type) == 'EntityType.FOLDER':
                current = client.folder(entity.reference)
            else:  # EntityType.ASSET
                current = client.asset(entity.reference)

            # If this is a folder and it's directly in the excluded list, add it
            if str(entity.entity_type) == 'EntityType.FOLDER' and current.reference in excluded_refs:
                excluded_entities.add(current.reference)
                logging.info(
                    f"Marking folder for exclusion: {current.reference}")
                continue

            # Check parent hierarchy for both folders and assets
            parent_ref = current.parent
            while parent_ref is not None:
                if parent_ref in excluded_refs:
                    excluded_entities.add(entity.reference)
                    logging.info(
                        f"Marking {'folder' if str(entity.entity_type) == 'EntityType.FOLDER' else 'asset'} for exclusion (child of excluded folder): {entity.reference}")
                    break
                parent_folder = client.folder(parent_ref)
                parent_ref = parent_folder.parent
        except Exception as e:
            logging.error(
                f"Error checking hierarchy for {entity.reference}: {e}")
            continue

    # Now filter the descendants using our complete set of excluded entities
    filtered_descendants = []
    for entity in all_descendants:
        if entity.reference in excluded_entities:
            logging.info(f"Skipping excluded entity: {entity.reference}")
            continue
        filtered_descendants.append(entity)

    logging.info(
        f"Completed retrieval of descendants. Total items retrieved: {len(filtered_descendants)} (after exclusions)")
    logging.info(f"Total entities excluded: {len(excluded_entities)}")
    return filtered_descendants


def retrieve_metadata_and_checksums(client, descendants, csv_writer, csv_header, algorithm, new_template):
    global error_count

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

        # Create base row data with all metadata
        base_row_data = [
            asset.reference, '', asset.entity_type,
            asset.security_tag, asset.title, asset.description
        ]

        # Add DC values if not using new template
        if not new_template:
            for header in csv_header[6:]:
                if header.startswith('dc:'):
                    # Join all values for this field, or use empty string if none
                    if dc_values[header]:
                        base_row_data.append('; '.join(dc_values[header]))
                    else:
                        base_row_data.append('')
                elif header.startswith('icaew:'):
                    base_row_data.append('')
                else:
                    base_row_data.append('')

        # Collect all checksum values
        checksum_values = []
        for representation in client.representations(asset):
            for content_object in client.content_objects(representation):
                try:
                    for generation in client.generations(content_object):
                        for bitstream in generation.bitstreams:
                            if algorithm in bitstream.fixity:
                                checksum_values.append(
                                    bitstream.fixity[algorithm])
                except Exception as e:
                    logging.error(f"Error processing asset {asset.title}: {e}")
                    error_count += 1

        # Write rows for checksums
        if checksum_values:
            # Write first row with all metadata
            base_row_data[1] = checksum_values[0]
            csv_writer.writerow(base_row_data)

            # Write additional rows with only checksum
            for checksum in checksum_values[1:]:
                blank_row = [''] * len(base_row_data)  # Create empty row
                blank_row[1] = checksum  # Set only the checksum
                csv_writer.writerow(blank_row)
        else:
            # If no checksums found, write the row with empty checksum field
            csv_writer.writerow(base_row_data)


def main():
    global error_count

    username, password, tenant, server = load_env_variables()
    client = initialize_client(username, password, tenant, server)
    args = parse_arguments()

    # Updated CSV header to include format information
    if args.algorithm == 'ALL':
        csv_header = ['assetId', 'MD5 checksum', 'SHA1 checksum', 'SHA256 checksum', 'entity.entity_type',
                      'asset.security_tag', 'entity.title', 'entity.description', 'preservica_path',
                      'filename', 'file_size', 'file_extension']
    else:
        csv_header = ['assetId', f'{args.algorithm} checksum', 'entity.entity_type',
                      'asset.security_tag', 'entity.title', 'entity.description', 'preservica_path',
                      'filename', 'file_size', 'file_extension']
    max_counts = defaultdict(int)

    # Always include ICAEW columns
    icaew_fields = ['icaew:ContentType']
    for field in icaew_fields:
        max_counts[field] = 1

    logging.info("Retrieving all descendants of the specified folder")
    try:
        descendants = get_all_descendants_with_logging(
            client, args.preservica_folder_ref, args.exclude_folders)
        for entity in descendants:
            try:
                xml_string = client.metadata_for_entity(
                    entity, 'http://www.openarchives.org/OAI/2.0/oai_dc/')
                max_counts = extract_dc_elements_and_update_header(
                    xml_string, max_counts)
                # Also check ICAEW
                icaew_xml = client.metadata_for_entity(
                    entity, 'https://www.icaew.com/metadata/')
                max_counts = extract_icaew_elements_and_update_header(
                    icaew_xml, max_counts)
            except Exception as e:
                logging.error(
                    f"Skipping entity {entity.reference} due to metadata error: {e}")
                error_count += 1
    except Exception as e:
        logging.error(f"Error retrieving descendants: {e}")
        error_count += 1
        exit(1)

    extended_headers = []
    for field, count in max_counts.items():
        extended_headers.extend([field] * count)

    if args.new_template:
        extended_headers = ['dc:title', 'dc:creator', 'dc:subject', 'dc:description', 'dc:publisher', 'dc:contributor', 'dc:date',
                            'dc:type', 'dc:type', 'dc:format', 'dc:identifier', 'dc:source', 'dc:language', 'dc:relation', 'dc:coverage', 'dc:rights'] + icaew_fields

    csv_header.extend(extended_headers)

    logging.info(f"Opening {args.metadata_csv} for writing")
    with open(args.metadata_csv, 'w', encoding='UTF8', newline='') as metadata_csv_file:
        csv_writer = csv.writer(
            metadata_csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(csv_header)

        logging.info("Processing entities and writing to CSV")
        for entity in descendants:
            # Filter by entity type if specified
            if args.entity_type == 'assets' and str(entity.entity_type) != 'EntityType.ASSET':
                continue
            elif args.entity_type == 'folders' and str(entity.entity_type) != 'EntityType.FOLDER':
                continue
            
            # Get the properly instantiated asset/folder object
            if str(entity.entity_type) == 'EntityType.FOLDER':
                asset = client.folder(entity.reference)
            elif str(entity.entity_type) == 'EntityType.ASSET':
                asset = client.asset(entity.reference)
            else:
                continue
                
            dc_values = defaultdict(list)
            icaew_values = {}
            # Get ICAEW metadata
            try:
                icaew_xml = client.metadata_for_entity(entity, 'https://www.icaew.com/metadata/')
                if icaew_xml is not None:
                    root = ET.fromstring(icaew_xml)
                    for child in root:
                        tag = child.tag.split('}')[-1]
                        icaew_field = f"icaew:{tag}"
                        icaew_values[icaew_field] = child.text or ''
            except Exception as e:
                logging.error(f"Error extracting ICAEW metadata for {entity.reference}: {e}")
            # Extract DC metadata
            try:
                xml_string = client.metadata_for_entity(
                    entity, 'http://www.openarchives.org/OAI/2.0/oai_dc/')
                if xml_string is not None:
                    root = ET.fromstring(xml_string)
                    for child in root:
                        tag = child.tag.split('}')[-1]
                        dc_field = f"dc:{tag}"
                        if child.text:
                            dc_values[dc_field].append(child.text)
            except Exception:
                pass
            # Create base row data with asset info only
            base_row_data = [
                asset.reference, '', asset.entity_type,
                asset.security_tag, asset.title, asset.description, get_full_preservica_path(client, entity)
            ]
            
            # Prepare DC and ICAEW metadata separately
            dc_icaew_data = []
            if not args.new_template:
                # Track how many times we've used each field for this row
                field_usage = defaultdict(int)
                # Determine the starting column for DC/ICAEW metadata based on algorithm mode
                if args.algorithm == 'ALL':
                    dc_start_column = 12  # After asset info (5) + checksums (3) + format fields (3)
                else:
                    dc_start_column = 10  # After asset info (7) + format fields (3)
                
                for header in csv_header[dc_start_column:]:  # Start from appropriate column
                    if header.startswith('dc:'):
                        value_list = dc_values[header]
                        usage = field_usage[header]
                        if usage < len(value_list):
                            dc_icaew_data.append(value_list[usage])
                        else:
                            dc_icaew_data.append('')
                        field_usage[header] += 1
                    elif header.startswith('icaew:'):
                        value = icaew_values.get(header, '')
                        dc_icaew_data.append(value)
                    else:
                        dc_icaew_data.append('')
            else:
                # For new template, just add blanks for ICAEW fields
                field_usage = defaultdict(int)
                # Determine the starting column for DC/ICAEW metadata based on algorithm mode
                if args.algorithm == 'ALL':
                    dc_start_column = 12  # After asset info (5) + checksums (3) + format fields (3)
                else:
                    dc_start_column = 10  # After asset info (7) + format fields (3)
                
                for header in csv_header[dc_start_column:]:  # Start from appropriate column
                    if header.startswith('icaew:'):
                        value = icaew_values.get(header, '')
                        dc_icaew_data.append(value)
                    elif header.startswith('dc:'):
                        value_list = dc_values[header]
                        usage = field_usage[header]
                        if usage < len(value_list):
                            dc_icaew_data.append(value_list[usage])
                        else:
                            dc_icaew_data.append('')
                        field_usage[header] += 1
                    else:
                        dc_icaew_data.append('')
            
            # Collect format and checksum information for first generation only
            format_checksum_data = []
            for representation in client.representations(entity):
                for content_object in client.content_objects(representation):
                    try:
                        # Get only the first generation (original ingested content)
                        generations = list(client.generations(content_object))
                        if generations:
                            first_generation = generations[0]  # First generation only
                            for bitstream in first_generation.bitstreams:
                                if args.algorithm == 'ALL':
                                    format_data = {
                                        'filename': bitstream.filename,
                                        'file_size': bitstream.length,  # Use length instead of file_size
                                        'file_extension': extract_file_extension(bitstream.filename),
                                        'md5_checksum': bitstream.fixity.get('MD5', ''),
                                        'sha1_checksum': bitstream.fixity.get('SHA1', ''),
                                        'sha256_checksum': bitstream.fixity.get('SHA256', '')
                                    }
                                else:
                                    format_data = {
                                        'filename': bitstream.filename,
                                        'file_size': bitstream.length,  # Use length instead of file_size
                                        'file_extension': extract_file_extension(bitstream.filename),
                                        'checksum': bitstream.fixity.get(args.algorithm, '') if args.algorithm in bitstream.fixity else ''
                                    }
                                format_checksum_data.append(format_data)
                    except Exception as e:
                        logging.error(f"Error processing bitstream for {asset.title}: {e}")
                        error_count += 1
            
            # Write rows for format and checksum data
            if format_checksum_data:
                # Write first row with all metadata and format info
                first_format_data = format_checksum_data[0]
                
                if args.algorithm == 'ALL':
                    # Build complete row with multiple checksums
                    complete_row = [base_row_data[0]]  # assetId
                    complete_row.extend([
                        first_format_data['md5_checksum'],
                        first_format_data['sha1_checksum'], 
                        first_format_data['sha256_checksum']
                    ])  # All checksums (columns 1-3)
                    complete_row.extend(base_row_data[2:7])  # entity_type, security_tag, title, description, path (columns 4-8)
                    complete_row.extend([
                        first_format_data['filename'],
                        first_format_data['file_size'],
                        first_format_data['file_extension']
                    ])  # Format data (columns 9-11)
                    complete_row.extend(dc_icaew_data)  # DC/ICAEW metadata (columns 12+)
                    csv_writer.writerow(complete_row)
                    
                    # Write additional rows with only checksums and format info (for multiple files)
                    for format_data in format_checksum_data[1:]:
                        # Create row with only asset ID, checksums, and format data
                        blank_row = [base_row_data[0]]  # assetId
                        blank_row.extend([
                            format_data['md5_checksum'],
                            format_data['sha1_checksum'],
                            format_data['sha256_checksum']
                        ])  # All checksums
                        blank_row.extend(['', '', '', '', ''])  # entity_type, security_tag, title, description, path (empty)
                        blank_row.extend([
                            format_data['filename'],
                            format_data['file_size'],
                            format_data['file_extension']
                        ])  # Format data
                        blank_row.extend([''] * len(dc_icaew_data))  # Empty DC/ICAEW fields
                        csv_writer.writerow(blank_row)
                else:
                    # Single algorithm mode
                    base_row_data[1] = first_format_data['checksum']  # checksum
                    
                    # Build complete row: asset info + format data + DC/ICAEW metadata
                    complete_row = base_row_data[:7]  # Asset info (first 7 columns including path)
                    complete_row.extend([
                        first_format_data['filename'],
                        first_format_data['file_size'],
                        first_format_data['file_extension']
                    ])  # Format data (columns 7-9)
                    complete_row.extend(dc_icaew_data)  # DC/ICAEW metadata (columns 10+)
                    csv_writer.writerow(complete_row)
                    
                    # Write additional rows with only checksum and format info (for multiple files)
                    for format_data in format_checksum_data[1:]:
                        # Create row with only asset ID, checksum, and format data
                        blank_row = [base_row_data[0]]  # assetId
                        blank_row.append(format_data['checksum'])  # checksum
                        blank_row.extend(['', '', '', '', ''])  # entity_type, security_tag, title, description, path (empty)
                        blank_row.extend([
                            format_data['filename'],
                            format_data['file_size'],
                            format_data['file_extension']
                        ])  # Format data
                        blank_row.extend([''] * len(dc_icaew_data))  # Empty DC/ICAEW fields
                        csv_writer.writerow(blank_row)
            else:
                # If no format data found, write the row with empty format fields
                if args.algorithm == 'ALL':
                    complete_row = [base_row_data[0]]  # assetId
                    complete_row.extend(['', '', ''])  # Empty checksums (MD5, SHA1, SHA256)
                    complete_row.extend(base_row_data[2:7])  # entity_type, security_tag, title, description, path
                    complete_row.extend(['', '', ''])  # Empty format fields
                    complete_row.extend(dc_icaew_data)  # DC/ICAEW metadata
                    csv_writer.writerow(complete_row)
                else:
                    complete_row = base_row_data[:7]  # Asset info (first 7 columns including path)
                    complete_row.extend(['', '', ''])  # Empty format fields (columns 7-9)
                    complete_row.extend(dc_icaew_data)  # DC/ICAEW metadata (columns 10+)
                    csv_writer.writerow(complete_row)

    logging.info(
        f"Metadata and checksums have been written to {args.metadata_csv}")

    # Final error summary
    if error_count > 0:
        print(f"\n{error_count} errors occurred. Check '{log_file}' for details.")
    else:
        print("\nScript completed with no errors.")


if __name__ == '__main__':
    main()
