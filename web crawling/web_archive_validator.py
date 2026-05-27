#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validate URLs against crawl data from WARC or WACZ files.

This script compares a list of target URLs (provided in a plain text file)
against URLs recorded in one or more WARC or WACZ files. It can process both
individual files and directories containing multiple archive files. The script
recursively searches through directories for .warc.gz and .wacz files.

It identifies:
- Matching URLs found in the files,
- Missing URLs not present in any file,
- URLs with non-200 status codes, including redirects and their destinations.

Usage:
    warc_validator.py url_list.txt archive1.warc.gz archive2.wacz ...
    warc_validator.py url_list.txt ./archives/ [file1.warc.gz ...]

Arguments:
    url_list: Path to the plain text file containing target URLs (one per line).
    archive_files: One or more WARC/WACZ files or directories containing archive files.

Options:
    --output-dir: Directory to save CSV files (default: current directory)
    --verbose: Enable verbose output
    --log-file: Path to log file (if not specified, logging to file is disabled)

Output:
    - CSV files containing:
        - matching_urls.csv: URLs found with 200 status
        - missing_urls.csv: URLs not found in archives
        - non_200_urls.csv: URLs with non-200 status codes and their details
    - Console output with summary statistics
"""

import argparse
from warcio.archiveiterator import ArchiveIterator
from collections import defaultdict
import zipfile
import tempfile
import os
import csv
from datetime import datetime
import logging
import sys
import urllib.parse
from tqdm import tqdm
import shutil

# Configure logging


def setup_logging(log_file=None, verbose=False):
    """Set up logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def validate_url(url):
    """Validate URL format."""
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def read_urls_from_file(file_path):
    """Reads target URLs from a file and returns them as a set."""
    urls = set()
    try:
        with open(file_path, 'r') as file:
            for line in file:
                url = line.strip()
                if url and validate_url(url):
                    urls.add(url)
                else:
                    logging.warning(f"Invalid URL format skipped: {url}")
        return urls
    except IOError as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return set()


def extract_warc_from_wacz(wacz_path, temp_dir):
    """
    Extracts WARC files from a WACZ archive.

    Args:
        wacz_path (str): Path to the WACZ file
        temp_dir (str): Temporary directory for extraction

    Returns:
        list: List of paths to extracted WARC files
    """
    extracted_warcs = []
    try:
        with zipfile.ZipFile(wacz_path, 'r') as wacz:
            # Extract all .warc.gz files
            for file in wacz.namelist():
                if file.endswith('.warc.gz'):
                    extracted_path = os.path.join(
                        temp_dir, os.path.basename(file))
                    with wacz.open(file) as source, open(extracted_path, 'wb') as target:
                        target.write(source.read())
                    extracted_warcs.append(extracted_path)
                    logging.debug(f"Extracted WARC file: {extracted_path}")
    except Exception as e:
        logging.error(f"Error extracting WARC files from {wacz_path}: {e}")
        raise

    return extracted_warcs


def process_warc_file(warc_path, target_urls):
    """
    Processes a WARC file and extracts URL and status information.

    Args:
        warc_path (str): Path to the WARC file
        target_urls (set): Set of target URLs to validate

    Returns:
        dict: Dictionary containing:
            - matching_urls: URLs found in WARC with 200 status
            - missing_urls: URLs not found in WARC
            - non_200_urls: URLs with non-200 status codes and their details
    """
    results = {
        'matching_urls': set(),
        'missing_urls': set(target_urls),
        'non_200_urls': defaultdict(dict)
    }

    redirect_chains = defaultdict(list)
    total_records = 0
    processed_records = 0

    try:
        # First pass to count total records
        with open(warc_path, 'rb') as stream:
            for _ in ArchiveIterator(stream):
                total_records += 1

        # Second pass to process records
        with open(warc_path, 'rb') as stream:
            for record in tqdm(ArchiveIterator(stream), total=total_records, desc=f"Processing {os.path.basename(warc_path)}"):
                processed_records += 1
                if record.rec_type in ['response', 'revisit']:
                    url = record.rec_headers.get_header('WARC-Target-URI')
                    if url in target_urls:
                        status = record.http_headers.get_statuscode()
                        if status == '200':
                            results['matching_urls'].add(url)
                            results['missing_urls'].discard(url)
                        else:
                            details = {'status': status}
                            if status in ['301', '302']:
                                location = record.http_headers.get_header(
                                    'Location')
                                if location:
                                    details['redirect_to'] = location
                                    redirect_chains[url].append(
                                        (status, location))
                            results['non_200_urls'][url] = details
                            results['missing_urls'].discard(url)

    except Exception as e:
        logging.error(f"Error processing WARC file {warc_path}: {e}")
        raise

    # Process redirect chains
    for url, chain in redirect_chains.items():
        if url in results['non_200_urls']:
            current_url = url
            full_chain = []

            while current_url in redirect_chains and len(redirect_chains[current_url]) > 0:
                status, next_url = redirect_chains[current_url][0]
                full_chain.append((current_url, status, next_url))
                current_url = next_url

            if full_chain:
                results['non_200_urls'][url]['redirect_chain'] = full_chain
                results['non_200_urls'][url]['final_destination'] = current_url

    logging.info(f"Processed {processed_records} records from {warc_path}")
    return results


def process_archive_files(archive_paths, target_urls):
    """
    Processes multiple WARC or WACZ files and combines their results.
    Can handle both individual files and directories containing archive files.

    Args:
        archive_paths (list): List of WARC/WACZ file paths or directories
        target_urls (set): Set of target URLs to validate

    Returns:
        dict: Combined results from all files
    """
    combined_results = {
        'matching_urls': set(),
        'missing_urls': set(target_urls),
        'non_200_urls': defaultdict(dict)
    }

    logging.info(f"Starting with {len(target_urls)} target URLs")
    logging.info(
        f"Initial missing URLs: {len(combined_results['missing_urls'])}")

    temp_dir = tempfile.mkdtemp()
    try:
        for archive_path in archive_paths:
            logging.info(f"Processing {archive_path}...")

            if not os.path.exists(archive_path):
                logging.error(f"Archive file not found: {archive_path}")
                continue

            if archive_path.endswith('.wacz'):
                logging.info("Extracting WARC files from WACZ archive...")
                try:
                    warc_files = extract_warc_from_wacz(archive_path, temp_dir)
                    if not warc_files:
                        logging.warning(
                            f"No WARC files found in {archive_path}")
                        continue
                    logging.info(
                        f"Found {len(warc_files)} WARC files in WACZ archive")
                    archive_files = warc_files
                except Exception as e:
                    logging.error(
                        f"Failed to extract WARC files from {archive_path}: {e}")
                    continue
            else:
                archive_files = [archive_path]

            for file_path in archive_files:
                try:
                    logging.info(f"Processing {file_path}...")
                    results = process_warc_file(file_path, target_urls)

                    logging.info(f"Found in this file:")
                    logging.info(
                        f"- Matching URLs: {len(results['matching_urls'])}")
                    logging.info(
                        f"- Non-200 URLs: {len(results['non_200_urls'])}")

                    combined_results['matching_urls'].update(
                        results['matching_urls'])
                    found_urls = results['matching_urls'].union(
                        results['non_200_urls'].keys())
                    combined_results['missing_urls'].difference_update(
                        found_urls)

                    for url, details in results['non_200_urls'].items():
                        combined_results['non_200_urls'][url] = details

                    logging.info(f"Current totals:")
                    logging.info(
                        f"- Matching URLs: {len(combined_results['matching_urls'])}")
                    logging.info(
                        f"- Missing URLs: {len(combined_results['missing_urls'])}")
                    logging.info(
                        f"- Non-200 URLs: {len(combined_results['non_200_urls'])}")

                except Exception as e:
                    logging.error(f"Error processing file {file_path}: {e}")
                    continue

    finally:
        try:
            shutil.rmtree(temp_dir)
            logging.debug(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logging.warning(
                f"Failed to clean up temporary directory {temp_dir}: {e}")

    return combined_results


def write_results_to_csv(results, output_dir='.'):
    """Writes the validation results to CSV files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Write matching URLs
    matching_path = os.path.join(output_dir, f'matching_urls_{timestamp}.csv')
    with open(matching_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['URL'])
        for url in sorted(results['matching_urls']):
            writer.writerow([url])

    # Write missing URLs
    missing_path = os.path.join(output_dir, f'missing_urls_{timestamp}.csv')
    with open(missing_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['URL'])
        for url in sorted(results['missing_urls']):
            writer.writerow([url])

    # Write non-200 URLs with their details
    non_200_path = os.path.join(output_dir, f'non_200_urls_{timestamp}.csv')
    with open(non_200_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(
            ['URL', 'Status', 'Redirect Chain', 'Final Destination'])
        for url, details in sorted(results['non_200_urls'].items()):
            status = details['status']
            redirect_chain = ''
            final_destination = ''

            if status in ['301', '302'] and 'redirect_chain' in details:
                chain = []
                for from_url, status_code, to_url in details['redirect_chain']:
                    chain.append(f"{from_url} → {to_url} ({status_code})")
                redirect_chain = ' | '.join(chain)
                final_destination = details['final_destination']

            writer.writerow([url, status, redirect_chain, final_destination])

    logging.info(
        f"Results have been written to CSV files with timestamp: {timestamp}")
    logging.info(f"- {matching_path}")
    logging.info(f"- {missing_path}")
    logging.info(f"- {non_200_path}")


def print_results(results):
    """Prints summary statistics and writes detailed results to CSV."""
    print("\nSummary Statistics:")
    print(
        f"- Total URLs processed: {len(results['matching_urls']) + len(results['missing_urls']) + len(results['non_200_urls'])}")
    print(f"- Matching URLs (200 status): {len(results['matching_urls'])}")
    print(f"- Missing URLs: {len(results['missing_urls'])}")
    print(f"- URLs with non-200 status codes: {len(results['non_200_urls'])}")


def main():
    parser = argparse.ArgumentParser(
        description='Validate URLs against crawl data in WARC or WACZ files.')
    parser.add_argument('url_list', help='Path to the URL list file')
    parser.add_argument('archive_files', nargs='+',
                        help='One or more WARC or WACZ files/directories to analyze')
    parser.add_argument('--output-dir', default='.',
                        help='Directory to save CSV files (default: current directory)')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--log-file',
                        help='Path to log file (if not specified, logging to file is disabled)')
    args = parser.parse_args()

    # Set up logging
    setup_logging(args.log_file, args.verbose)

    try:
        # Read target URLs
        target_urls = read_urls_from_file(args.url_list)
        if not target_urls:
            logging.error("No valid URLs found in the input file")
            sys.exit(1)

        # Collect all archive files from directories
        archive_files = []
        for path in args.archive_files:
            if os.path.isdir(path):
                logging.info(f"Scanning directory: {path}")
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.endswith(('.warc.gz', '.wacz')):
                            archive_files.append(os.path.join(root, file))
            else:
                archive_files.append(path)

        if not archive_files:
            logging.error("No WARC or WACZ files found")
            sys.exit(1)

        logging.info(f"Found {len(archive_files)} archive files to process")

        # Process archive files
        results = process_archive_files(archive_files, target_urls)

        # Print results and write to CSV
        print_results(results)
        write_results_to_csv(results, args.output_dir)

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()