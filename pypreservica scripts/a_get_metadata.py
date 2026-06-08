#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to export metadata, checksum values, and file format information to CSV from Preservica.

This script extracts comprehensive information from Preservica assets including:
- Asset metadata (title, description, security tag, entity type)
- Multiple checksum algorithms (MD5, SHA1, SHA256) by default
- File format information (filename, file size, file extension)
- Full Preservica path from root to asset
- Dublin Core and ICAEW metadata
- Only processes first generation (original ingested) assets46357ae5-5278-461d-a9c7-b269ba59e861

The script can process entities in two ways:
1. From a folder: retrieves all descendants of a specified folder
2. From a file: processes specific references listed in a text file (one per line)

Usage:
    a_get_metadata.py [-h] (--preservica-folder-ref FOLDER_REF | --references-file FILE) --metadata-csv METADATA_CSV [--algorithm ALGORITHM] [--new-template] [--exclude-folders EXCLUDE_FOLDERS] [--entity-type {assets,folders,both}] [--all-generations]

Options:
    --preservica-folder-ref      Preservica folder reference. Example: "bb45f999-7c07-4471-9c30-54b057c500ff". Enter "root" if needing to get metadata from the root folder. Required if --references-file is not provided.
    --references-file            Path to a text file containing Preservica references (one per line). Required if --preservica-folder-ref is not provided.
    --metadata-csv METADATA_CSV  Output CSV filename for metadata and checksums
    --algorithm ALGORITHM        The checksum algorithm to use (choices: MD5, SHA1, SHA256, ALL) [default: ALL]
    --new-template               Flag to use new template with extended Dublin Core elements
    --exclude-folders            List of folder references to exclude from processing. These folders and their children will be skipped.
    --entity-type                Type of entities to include in output (choices: assets, folders, both) [default: both]
    --all-generations            Extract metadata from all generations, including derived files. By default, only the original submitted file (first generation) is processed.

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
    - By default, processes only first generation (original submitted) files; can be configured to include all generations
    - Supports processing from folder or from a list of references in a text file
    - Supports exclusion of specific folders and their children (folder mode only)
    - Handles both Dublin Core and ICAEW metadata
    - Extracts file format information from bitstreams
    - Provides comprehensive error logging
    - Supports filtering by entity type (assets only, folders only, or both)
"""

import argparse
import csv
import os
import time
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter
import logging
from dotenv import load_dotenv
from pyPreservica import EntityAPI

log_file = "errors.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w'),
        logging.StreamHandler()
    ]
)

error_count = 0

DC_SCHEMA = 'http://www.openarchives.org/OAI/2.0/oai_dc/'
ICAEW_SCHEMA = 'https://www.icaew.com/metadata/'

# Shared caches to avoid redundant API calls across both phases
_entity_cache = {}   # ref -> full entity object (asset or folder)
_path_cache = {}     # ref -> full path string
_metadata_cache = {} # ref -> list of (schema, xml_string) tuples from all_metadata()


def load_env_variables():
    logging.info("Loading environment variables from .env file")
    load_dotenv(override=True)
    username = os.getenv('USERNAME')
    password = os.getenv('PASSWORD')
    tenant = os.getenv('TENANT')
    server = os.getenv('SERVER')
    if not all([username, password, tenant, server]):
        logging.error("One or more environment variables are missing. Please check the .env file.")
        exit(1)
    return username, password, tenant, server


def initialize_client(username, password, tenant, server):
    logging.info("Initializing Preservica API client")
    try:
        return EntityAPI(username=username, password=password, tenant=tenant, server=server)
    except Exception as e:
        global error_count
        logging.error(f"Failed to initialize Preservica API client: {e}")
        error_count += 1
        exit(1)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Export metadata and checksums to CSV from Preservica.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--preservica-folder-ref',
                       help='Preservica folder reference. Enter "root" for the root folder.')
    group.add_argument('--references-file',
                       help='Path to a text file containing Preservica references (one per line)')
    parser.add_argument('--metadata-csv', required=True,
                        help='Output CSV filename for metadata and checksums')
    parser.add_argument('--algorithm', default='ALL', choices=['MD5', 'SHA1', 'SHA256', 'ALL'],
                        help='The checksum algorithm to use [default: ALL]')
    parser.add_argument('--new-template', action='store_true',
                        help='Flag to use new template with extended Dublin Core elements')
    parser.add_argument('--exclude-folders', nargs='+',
                        help='Folder references to exclude (and their children)')
    parser.add_argument('--entity-type', default='both', choices=['assets', 'folders', 'both'],
                        help='Type of entities to include [default: both]')
    parser.add_argument('--all-generations', action='store_true',
                        help='Extract metadata from all generations (default: first generation only)')
    args = parser.parse_args()
    args.original_only = not args.all_generations
    if args.preservica_folder_ref == 'root':
        args.preservica_folder_ref = None
    return args


def get_cached_entity(client, entity):
    """Fetch and cache a full entity object (asset or folder) by entity stub."""
    ref = entity.reference
    if ref not in _entity_cache:
        if str(entity.entity_type) == 'EntityType.FOLDER':
            _entity_cache[ref] = client.folder(ref)
        else:
            _entity_cache[ref] = client.asset(ref)
    return _entity_cache[ref]


def get_cached_folder(client, ref):
    """Fetch and cache a folder by reference string."""
    if ref not in _entity_cache:
        _entity_cache[ref] = client.folder(ref)
    return _entity_cache[ref]


def fetch_and_cache_metadata(client, entity):
    """
    Fetch all metadata schemas for an entity in a single all_metadata() call and cache
    the result. Returns a list of (schema, xml_string) tuples.
    Raises on API error so the caller can track discovery errors.
    Note: all_metadata() requires a fully-fetched entity, not a stub from all_descendants().
    """
    ref = entity.reference
    if ref in _metadata_cache:
        return _metadata_cache[ref]
    full_entity = get_cached_entity(client, entity)
    results = list(client.all_metadata(full_entity))
    _metadata_cache[ref] = results
    return results


def get_cached_metadata(entity):
    """Return cached metadata as {'dc': xml_or_None, 'icaew': xml_or_None}."""
    cached = _metadata_cache.get(entity.reference, [])
    dc_xml = None
    icaew_xml = None
    for schema, xml_string in cached:
        if DC_SCHEMA in schema:
            dc_xml = xml_string
        elif ICAEW_SCHEMA in schema or 'icaew' in schema.lower():
            icaew_xml = xml_string
    return dc_xml, icaew_xml


def get_full_preservica_path(client, entity):
    """Build the full path from root to entity, caching both entity objects and completed paths."""
    ref = entity.reference
    if ref in _path_cache:
        return _path_cache[ref]

    path_parts = []
    try:
        full_entity = get_cached_entity(client, entity)
        path_parts.append(full_entity.title or full_entity.reference)

        parent_ref = full_entity.parent
        while parent_ref is not None:
            if parent_ref in _path_cache:
                # Reuse an already-computed ancestor path
                path_parts.reverse()
                result = _path_cache[parent_ref] + '/' + '/'.join(path_parts)
                _path_cache[ref] = result
                return result
            try:
                parent_folder = get_cached_folder(client, parent_ref)
                path_parts.append(parent_folder.title or parent_folder.reference)
                parent_ref = parent_folder.parent
            except Exception as e:
                logging.error(f"Error getting parent folder {parent_ref}: {e}")
                path_parts.append(parent_ref)
                break

        path_parts.reverse()
        result = '/'.join(path_parts)
    except Exception as e:
        logging.error(f"Error building path for {entity.reference}: {e}")
        result = entity.reference

    _path_cache[ref] = result
    return result


def extract_file_extension(filename):
    if filename:
        return os.path.splitext(filename)[1].lower().lstrip('.')
    return ''


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
        for elem in root.iter():
            if elem == root:
                continue
            tag = elem.tag.split('}')[-1]
            icaew_field = f"icaew:{tag}"
            if max_counts[icaew_field] < 1:
                max_counts[icaew_field] = 1
    return max_counts


def parse_dc_values(xml_string):
    dc_values = defaultdict(list)
    if xml_string:
        root = ET.fromstring(xml_string)
        for child in root:
            tag = child.tag.split('}')[-1]
            if child.text:
                dc_values[f"dc:{tag}"].append(child.text)
    return dc_values


def parse_icaew_values(xml_string):
    icaew_values = {}
    if not xml_string:
        return icaew_values
    root = ET.fromstring(xml_string)
    direct_child_ids = {id(child) for child in root}
    for child in root:
        tag = child.tag.split('}')[-1]
        icaew_field = f"icaew:{tag}"
        if len(child) == 0:
            text_content = child.text or ''
        else:
            parts = []
            if child.text and child.text.strip():
                parts.append(child.text.strip())
            for desc in child.iter():
                if desc != child and desc.text and desc.text.strip():
                    parts.append(desc.text.strip())
            text_content = ' '.join(parts).strip()
        if text_content or icaew_field not in icaew_values:
            icaew_values[icaew_field] = text_content
    # Pick up any nested fields not yet captured as direct children
    for elem in root.iter():
        if elem == root or id(elem) in direct_child_ids:
            continue
        tag = elem.tag.split('}')[-1]
        icaew_field = f"icaew:{tag}"
        if icaew_field not in icaew_values and elem.text:
            icaew_values[icaew_field] = elem.text.strip()
    return icaew_values


def build_dc_icaew_row(csv_header, dc_start_column, dc_values, icaew_values):
    """Build the DC/ICAEW portion of a CSV row from the given column offset."""
    field_usage = defaultdict(int)
    row = []
    for header in csv_header[dc_start_column:]:
        if header.startswith('dc:'):
            value_list = dc_values[header]
            usage = field_usage[header]
            row.append(value_list[usage] if usage < len(value_list) else '')
            field_usage[header] += 1
        elif header.startswith('icaew:'):
            row.append(icaew_values.get(header, ''))
        else:
            row.append('')
    return row


def read_references_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            references = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        logging.info(f"Read {len(references)} references from {file_path}")
        return references
    except FileNotFoundError:
        logging.error(f"References file not found: {file_path}")
        exit(1)
    except Exception as e:
        logging.error(f"Error reading references file {file_path}: {e}")
        exit(1)


def get_entities_from_references(client, references):
    global error_count
    entities = []
    for ref in references:
        try:
            entity = client.asset(ref)
            entities.append(entity)
            logging.info(f"Successfully retrieved asset: {ref}")
        except Exception:
            try:
                entity = client.folder(ref)
                entities.append(entity)
                logging.info(f"Successfully retrieved folder: {ref}")
            except Exception as e:
                logging.error(f"Failed to retrieve entity {ref}: {e}")
                error_count += 1
    logging.info(f"Retrieved {len(entities)} entities from {len(references)} references")
    return entities


def get_all_descendants_with_logging(client, folder_ref, exclude_folders=None):
    logging.info(f"Starting retrieval of descendants for folder reference: {folder_ref}")
    all_descendants = list(client.all_descendants(folder_ref))

    if not exclude_folders:
        logging.info(f"Total items retrieved: {len(all_descendants)}")
        return all_descendants

    # Build excluded set by collecting descendants of each excluded folder directly.
    # This avoids traversing the full parent hierarchy for every entity in the collection.
    excluded_refs = set(exclude_folders)
    for excl_ref in exclude_folders:
        try:
            for desc in client.all_descendants(excl_ref):
                excluded_refs.add(desc.reference)
            logging.info(f"Marked folder {excl_ref} and its descendants for exclusion")
        except Exception as e:
            logging.error(f"Error getting descendants of excluded folder {excl_ref}: {e}")

    filtered = [e for e in all_descendants if e.reference not in excluded_refs]
    excluded_count = len(all_descendants) - len(filtered)
    logging.info(f"Total items after exclusions: {len(filtered)} (excluded {excluded_count})")
    logging.info(f"Total entities excluded: {excluded_count}")
    return filtered


def main():
    global error_count

    username, password, tenant, server = load_env_variables()
    client = initialize_client(username, password, tenant, server)
    args = parse_arguments()

    if args.algorithm == 'ALL':
        csv_header = ['assetId', 'MD5 checksum', 'SHA1 checksum', 'SHA256 checksum',
                      'entity.entity_type', 'asset.security_tag', 'entity.title',
                      'entity.description', 'preservica_path', 'filename', 'file_size',
                      'file_extension', 'total_metadata_fragments']
    else:
        csv_header = ['assetId', f'{args.algorithm} checksum', 'entity.entity_type',
                      'asset.security_tag', 'entity.title', 'entity.description',
                      'preservica_path', 'filename', 'file_size', 'file_extension',
                      'total_metadata_fragments']
    max_counts = defaultdict(int)

    if args.references_file:
        logging.info(f"Reading references from file: {args.references_file}")
        references = read_references_from_file(args.references_file)
        try:
            descendants = get_entities_from_references(client, references)
        except Exception as e:
            logging.error(f"Error retrieving entities from references: {e}")
            error_count += 1
            exit(1)
    else:
        logging.info("Retrieving all descendants of the specified folder")
        try:
            descendants = get_all_descendants_with_logging(
                client, args.preservica_folder_ref, args.exclude_folders)
        except Exception as e:
            logging.error(f"Error retrieving descendants: {e}")
            error_count += 1
            exit(1)

    print(f"\n{'='*70}")
    print("PHASE 1: DISCOVERY - Analyzing metadata structure")
    print(f"{'='*70}")
    print(f"Scanning {len(descendants)} entities to discover all metadata fields...")
    print(f"  This may take a few moments depending on the number of entities...\n")

    start_time = time.time()
    processed = 0
    errors_in_discovery = 0
    update_interval = 10 if len(descendants) < 1000 else 25

    for entity in descendants:
        try:
            # Single all_metadata() call replaces two metadata_for_entity() calls,
            # and the result is cached for reuse in Phase 2.
            meta_list = fetch_and_cache_metadata(client, entity)
            for schema, xml_string in meta_list:
                if DC_SCHEMA in schema:
                    max_counts = extract_dc_elements_and_update_header(xml_string, max_counts)
                elif ICAEW_SCHEMA in schema or 'icaew' in schema.lower():
                    max_counts = extract_icaew_elements_and_update_header(xml_string, max_counts)
            processed += 1

            if processed % update_interval == 0 or processed == len(descendants):
                percentage = (processed / len(descendants)) * 100
                elapsed = time.time() - start_time
                avg_time_per_entity = elapsed / processed
                remaining = (len(descendants) - processed) * avg_time_per_entity
                if remaining > 60:
                    eta = f" (~{remaining/60:.1f} min remaining)"
                elif remaining > 0:
                    eta = f" (~{remaining:.0f} sec remaining)"
                else:
                    eta = ""
                print(f"  Progress: {processed}/{len(descendants)} entities ({percentage:.1f}%){eta}", end='\r', flush=True)
        except Exception as e:
            logging.error(f"Skipping entity {entity.reference} due to metadata error: {e}")
            error_count += 1
            errors_in_discovery += 1
            _metadata_cache[entity.reference] = []  # Cache empty to avoid retry in Phase 2
            processed += 1

    elapsed_time = time.time() - start_time
    final_percentage = (processed / len(descendants)) * 100 if len(descendants) > 0 else 100.0
    print(f"  Processed {processed}/{len(descendants)} entities ({final_percentage:.1f}%) in {elapsed_time:.1f} seconds.          ")
    if errors_in_discovery > 0:
        print(f"  ⚠️  {errors_in_discovery} entities had errors during discovery (check logs for details)")

    print(f"\nDiscovery complete. Found the following metadata fields:")
    dc_fields = {k: v for k, v in max_counts.items() if k.startswith('dc:')}
    icaew_fields = {k: v for k, v in max_counts.items() if k.startswith('icaew:')}

    if dc_fields:
        print(f"\n  Dublin Core fields:")
        for field, count in sorted(dc_fields.items()):
            if count > 1:
                print(f"    - {field}: {count} columns (repeating field)")
            else:
                print(f"    - {field}: 1 column")

    if icaew_fields:
        print(f"\n  ICAEW fields:")
        for field, count in sorted(icaew_fields.items()):
            if count > 1:
                print(f"    - {field}: {count} columns (repeating field)")
            else:
                print(f"    - {field}: 1 column")

    extended_headers = []
    for field, count in max_counts.items():
        extended_headers.extend([field] * count)

    total_metadata_columns = len(extended_headers)
    print(f"\n  Total metadata columns to be created: {total_metadata_columns}")
    print(f"{'='*70}\n")

    if args.new_template:
        required_icaew = ['icaew:ContentType', 'icaew:InternalReference', 'icaew:Notes']
        required_icaew_lower = {f.lower() for f in required_icaew}
        extra_icaew = list(dict.fromkeys(
            f for f in max_counts
            if f.startswith('icaew:') and f.lower() not in required_icaew_lower
        ))
        extended_headers = [
            'dc:title', 'dc:creator', 'dc:subject', 'dc:description', 'dc:publisher',
            'dc:contributor', 'dc:date', 'dc:type', 'dc:type', 'dc:format',
            'dc:identifier', 'dc:source', 'dc:language', 'dc:relation',
            'dc:coverage', 'dc:rights',
        ] + required_icaew + extra_icaew

    csv_header.extend(extended_headers)
    dc_start_column = 13 if args.algorithm == 'ALL' else 11

    logging.info(f"Opening {args.metadata_csv} for writing")
    print(f"{'='*70}")
    print("PHASE 2: EXTRACTION - Writing metadata to CSV")
    print(f"{'='*70}")
    print(f"Output file: {args.metadata_csv}")
    print(f"Total columns: {len(csv_header)}")
    print(f"Writing CSV header...")

    with open(args.metadata_csv, 'w', encoding='UTF8', newline='') as metadata_csv_file:
        csv_writer = csv.writer(metadata_csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(csv_header)

        logging.info("Processing entities and writing to CSV")
        print(f"Processing {len(descendants)} entities and writing data...\n")

        rows_written = 0
        entities_processed = 0

        for entity in descendants:
            entity_type_str = str(entity.entity_type)
            if args.entity_type == 'assets' and entity_type_str != 'EntityType.ASSET':
                continue
            elif args.entity_type == 'folders' and entity_type_str != 'EntityType.FOLDER':
                continue

            asset = get_cached_entity(client, entity)

            logging.info(f"Getting metadata and checksum for assetID: {asset.reference}")

            # Fragment count from cached all_metadata() results — no extra API call
            total_fragments = len(_metadata_cache.get(entity.reference, []))

            # Parse metadata from cache — no extra API calls
            dc_xml, icaew_xml = get_cached_metadata(entity)
            dc_values = parse_dc_values(dc_xml)
            icaew_values = parse_icaew_values(icaew_xml)

            base_row_data = [
                asset.reference, '', asset.entity_type,
                asset.security_tag, asset.title, asset.description,
                get_full_preservica_path(client, entity)
            ]

            dc_icaew_data = build_dc_icaew_row(csv_header, dc_start_column, dc_values, icaew_values)

            original_files = []
            derived_files = []

            for representation in client.representations(entity):
                rep_name = (getattr(representation, 'name', '') or '').lower()
                rep_type = (getattr(representation, 'type', '') or '').lower()
                if rep_name or rep_type:
                    is_preservation = 'preservation' in rep_name or 'preservation' in rep_type
                else:
                    is_preservation = True

                if args.original_only and not is_preservation:
                    continue

                for content_object in client.content_objects(representation):
                    try:
                        generations = list(client.generations(content_object))
                        if not generations:
                            continue
                        generations_to_process = [generations[0]] if args.original_only else generations

                        for gen_index, generation in enumerate(generations_to_process):
                            is_original_submitted = is_preservation and gen_index == 0
                            for bitstream in generation.bitstreams:
                                if args.algorithm == 'ALL':
                                    format_data = {
                                        'filename': bitstream.filename,
                                        'file_size': bitstream.length,
                                        'file_extension': extract_file_extension(bitstream.filename),
                                        'md5_checksum': bitstream.fixity.get('MD5', ''),
                                        'sha1_checksum': bitstream.fixity.get('SHA1', ''),
                                        'sha256_checksum': bitstream.fixity.get('SHA256', '')
                                    }
                                else:
                                    format_data = {
                                        'filename': bitstream.filename,
                                        'file_size': bitstream.length,
                                        'file_extension': extract_file_extension(bitstream.filename),
                                        'checksum': bitstream.fixity.get(args.algorithm, '')
                                    }
                                (original_files if is_original_submitted else derived_files).append(format_data)
                    except Exception as e:
                        logging.error(f"Error processing asset {asset.title}: {e}")
                        error_count += 1

            format_checksum_data = original_files + derived_files

            if format_checksum_data:
                first = format_checksum_data[0]
                if args.algorithm == 'ALL':
                    complete_row = [base_row_data[0],
                                    first['md5_checksum'], first['sha1_checksum'], first['sha256_checksum']]
                    complete_row.extend(base_row_data[2:7])
                    complete_row.extend([first['filename'], first['file_size'], first['file_extension'], total_fragments])
                    complete_row.extend(dc_icaew_data)
                    csv_writer.writerow(complete_row)
                    rows_written += 1

                    for fd in format_checksum_data[1:]:
                        blank_row = [base_row_data[0],
                                     fd['md5_checksum'], fd['sha1_checksum'], fd['sha256_checksum'],
                                     '', '', '', '', '']
                        blank_row.extend([fd['filename'], fd['file_size'], fd['file_extension'], total_fragments])
                        blank_row.extend([''] * len(dc_icaew_data))
                        csv_writer.writerow(blank_row)
                        rows_written += 1
                else:
                    base_row_data[1] = first['checksum']
                    complete_row = base_row_data[:7]
                    complete_row.extend([first['filename'], first['file_size'], first['file_extension'], total_fragments])
                    complete_row.extend(dc_icaew_data)
                    csv_writer.writerow(complete_row)
                    rows_written += 1

                    for fd in format_checksum_data[1:]:
                        blank_row = [base_row_data[0], fd['checksum'], '', '', '', '', '']
                        blank_row.extend([fd['filename'], fd['file_size'], fd['file_extension'], total_fragments])
                        blank_row.extend([''] * len(dc_icaew_data))
                        csv_writer.writerow(blank_row)
                        rows_written += 1
            else:
                if args.algorithm == 'ALL':
                    complete_row = [base_row_data[0], '', '', '']
                    complete_row.extend(base_row_data[2:7])
                    complete_row.extend(['', '', '', total_fragments])
                    complete_row.extend(dc_icaew_data)
                else:
                    complete_row = base_row_data[:7]
                    complete_row.extend(['', '', '', total_fragments])
                    complete_row.extend(dc_icaew_data)
                csv_writer.writerow(complete_row)
                rows_written += 1

            entities_processed += 1
            if entities_processed % 25 == 0:
                print(f"  Processed {entities_processed}/{len(descendants)} entities, written {rows_written} rows...", end='\r')

    print(f"  Processed {entities_processed}/{len(descendants)} entities, written {rows_written} rows.          ")
    logging.info(f"Metadata and checksums have been written to {args.metadata_csv}")

    print(f"\n{'='*70}")
    print("EXTRACTION COMPLETE")
    print(f"{'='*70}")
    print(f"Output file: {args.metadata_csv}")
    print(f"Total entities processed: {entities_processed}")
    print(f"Total rows written: {rows_written}")
    print(f"Total columns: {len(csv_header)}")

    if error_count > 0:
        print(f"\n⚠️  {error_count} errors occurred. Check '{log_file}' for details.")
    else:
        print(f"\n✓ Script completed successfully with no errors.")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
