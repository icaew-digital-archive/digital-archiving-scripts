#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validate URLs against crawl data from a WACZ file.

This script compares a list of target URLs (provided in a plain text file)
against URLs recorded in the `pages.jsonl` and `extraPages.jsonl` files 
stored in a WACZ archive. It identifies:
- Matching URLs found in the WACZ file,
- Missing URLs not present in the WACZ file,
- URLs with a status code other than 200.

The WACZ archive must follow the standard structure where `pages.jsonl` and
`extraPages.jsonl` are located under the `pages/` directory.

Usage:
    pages_json_log_validate.py url_list.txt archive.wacz

Arguments:
    url_list: Path to the plain text file containing target URLs (one per line).
    wacz_file: Path to the WACZ file to be analyzed.

Output:
    - Matching URLs and their count.
    - Missing URLs and their count.
    - URLs with non-200 status codes, their count, and their corresponding status.
"""

import argparse
import json
import zipfile


def read_urls_from_file(file_path):
    """Reads target URLs from a file and returns them as a set."""
    try:
        with open(file_path, 'r') as file:
            return set(line.strip() for line in file)
    except IOError as e:
        print(f"Error reading file {file_path}: {e}")
        return set()


def load_jsonl_from_wacz(wacz_path, jsonl_name):
    """
    Extracts URL and status information from a JSONL file within a WACZ archive.

    Args:
        wacz_path (str): Path to the WACZ file.
        jsonl_name (str): Name of the JSONL file (e.g., 'pages.jsonl') to extract.

    Returns:
        dict: A dictionary where keys are URLs and values are status codes.
    """
    url_data = {}
    try:
        with zipfile.ZipFile(wacz_path, 'r') as wacz:
            # Look for the JSONL file in the 'pages/' directory of the WACZ archive
            jsonl_path = f"pages/{jsonl_name}"
            if jsonl_path not in wacz.namelist():
                print(f"File {jsonl_name} not found in WACZ archive {wacz_path}.")
                return url_data

            with wacz.open(jsonl_path) as jsonl_file:
                for line_number, line in enumerate(jsonl_file, start=1):
                    try:
                        json_line = json.loads(line)
                        url = json_line.get('url')  # Extract URL
                        status = json_line.get('status', None)  # Extract status code
                        if url:
                            url_data[url] = status
                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON on line {line_number} of {jsonl_name}: {e}")
    except IOError as e:
        print(f"Error reading WACZ file {wacz_path}: {e}")
    return url_data


def compare_and_print_results(url_list, crawled_data):
    """
    Compares the target URLs against crawled data and prints results.

    Args:
        url_list (set): Set of target URLs from the input file.
        crawled_data (dict): Dictionary of crawled URLs and their statuses.

    Output:
        Prints the following information:
        - Count and list of matching URLs.
        - Count and list of missing URLs.
        - Count and list of URLs with non-200 statuses, including their status codes.
    """
    matching_urls = url_list.intersection(crawled_data.keys())
    missing_urls = url_list.difference(crawled_data.keys())
    non_200_status_urls = {url: status for url, status in crawled_data.items() if url in url_list and status != 200}

    # Print results with counts
    print(f"Matching URLs ({len(matching_urls)}):")
    if matching_urls:
        for url in matching_urls:
            print(url)
    else:
        print("No matching URLs found.")

    print(f"\nMissing URLs ({len(missing_urls)}):")
    if missing_urls:
        for url in missing_urls:
            print(url)
    else:
        print("No missing URLs.")

    print(f"\nURLs with non-200 statuses ({len(non_200_status_urls)}):")
    if non_200_status_urls:
        for url, status in non_200_status_urls.items():
            print(f"{url} - Status: {status}")
    else:
        print("All matching URLs have a status of 200.")


def main():
    """
    Main entry point for the script.

    - Parses command-line arguments for the URL list and WACZ file paths.
    - Reads the target URLs from the input file.
    - Loads crawled data from `pages.jsonl` and `extraPages.jsonl` in the WACZ file.
    - Compares the target URLs against crawled data and prints results.
    """
    parser = argparse.ArgumentParser(description='Validate URLs against crawl data in a WACZ file.')
    parser.add_argument('url_list', help='Path to the URL list file')
    parser.add_argument('wacz_file', help='Path to the WACZ file containing pages.jsonl and extraPages.jsonl')
    args = parser.parse_args()

    # Read target URLs
    url_list = read_urls_from_file(args.url_list)

    # Load crawled data from pages.jsonl and extraPages.jsonl
    pages_data = load_jsonl_from_wacz(args.wacz_file, 'pages.jsonl')
    extra_pages_data = load_jsonl_from_wacz(args.wacz_file, 'extraPages.jsonl')

    # Combine data from both files
    all_crawled_data = {**pages_data, **extra_pages_data}

    # Compare and print results
    compare_and_print_results(url_list, all_crawled_data)


if __name__ == '__main__':
    main()

