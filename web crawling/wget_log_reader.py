#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Reads the wget log file and uses regex matching to compare to the URL list
input to wget to verify the success of a crawl. Tracks redirect chains (301/302)
and logs all redirects encountered.

Output:
    - CSV files containing:
        - matching_urls.csv: URLs found with 200 status
        - missing_urls.csv: URLs not found in archives
        - non_200_urls.csv: URLs with non-200 status codes and their details
    - Console output with summary statistics
"""

import re
import argparse
import logging
from datetime import datetime
import os
import csv
import sys
from collections import defaultdict


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


def compile_patterns():
    return {
        "log_entry": re.compile(r"--\d{4}-\d{2}-\d{2}.*?\d+\]\n", re.DOTALL),
        "url": re.compile(r"https?://[^\s]+"),
        "status_code": re.compile(r"response... (\d{3})"),
        "length": re.compile(r"Length: (\d+)"),
        "saved_number": re.compile(r"saved \[(\d+)/"),
        "location": re.compile(r"Location: ([^\n]+)"),  # For redirect chains
        "redirect_chain": re.compile(r"following redirect to ([^\n]+)")
    }


def extract_log_entries(file_path, patterns):
    with open(file_path, 'r') as file:
        log_data = file.read()
    return patterns["log_entry"].findall(log_data)


def extract_details(log_entry, patterns):
    url_match = patterns["url"].search(log_entry)
    status_match = patterns["status_code"].search(log_entry)
    length_match = patterns["length"].search(log_entry)
    saved_match = patterns["saved_number"].search(log_entry)
    location_match = patterns["location"].search(log_entry)
    redirect_matches = patterns["redirect_chain"].findall(log_entry)

    details = {
        "url": url_match and url_match.group(0),
        "status_code": status_match and status_match.group(1),
        "length": length_match and length_match.group(1),
        "saved_number": saved_match and saved_match.group(1),
        "location": location_match and location_match.group(1),
        "redirect_chain": redirect_matches
    }
    return details


def read_urls(file_path):
    with open(file_path, 'r') as file:
        return list(set(line.strip() for line in file))


def process_log_entries(log_details, target_urls):
    """Process log entries and categorize URLs."""
    results = {
        'matching_urls': set(),
        'missing_urls': set(target_urls),
        'non_200_urls': defaultdict(dict)
    }

    for url, details in log_details.items():
        if url in target_urls:
            if details["status_code"] == "200":
                results['matching_urls'].add(url)
                results['missing_urls'].discard(url)
            else:
                status = details["status_code"]
                redirect_info = {
                    'status': status,
                }
                
                if status in ['301', '302']:
                    # Add the immediate redirect destination
                    if details["location"]:
                        redirect_info['redirect_to'] = details["location"].strip()
                        redirect_info['final_destination'] = details["location"].strip()
                    
                    # Build redirect chain
                    chain = []
                    current_url = url
                    if details["redirect_chain"]:
                        for next_url in details["redirect_chain"]:
                            chain.append((current_url, status, next_url.strip()))
                            current_url = next_url.strip()
                            # Update final destination to last URL in chain
                            redirect_info['final_destination'] = current_url
                    
                    if chain:
                        redirect_info['redirect_chain'] = chain

                results['non_200_urls'][url] = redirect_info
                results['missing_urls'].discard(url)

    return results


def write_results_to_csv(results):
    """Writes the validation results to CSV files in current directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Write matching URLs
    matching_path = f'matching_urls_{timestamp}.csv'
    with open(matching_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['URL'])
        for url in sorted(results['matching_urls']):
            writer.writerow([url])

    # Write missing URLs
    missing_path = f'missing_urls_{timestamp}.csv'
    with open(missing_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['URL'])
        for url in sorted(results['missing_urls']):
            writer.writerow([url])

    # Write non-200 URLs with their details
    non_200_path = f'non_200_urls_{timestamp}.csv'
    with open(non_200_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['URL', 'Status', 'Redirect Chain', 'Final Destination'])
        for url, details in sorted(results['non_200_urls'].items()):
            status = details['status']
            redirect_chain = ''
            final_destination = details.get('final_destination', '')

            if status in ['301', '302']:
                if 'redirect_chain' in details:
                    chain = []
                    for from_url, status_code, to_url in details['redirect_chain']:
                        chain.append(f"{from_url} → {to_url}")
                    redirect_chain = ' → '.join(chain)
                elif 'redirect_to' in details:
                    redirect_chain = f"{url} → {details['redirect_to']}"

            writer.writerow([url, status, redirect_chain, final_destination])

    logging.info(f"Results have been written to CSV files with timestamp: {timestamp}")
    logging.info(f"- {matching_path}")
    logging.info(f"- {missing_path}")
    logging.info(f"- {non_200_path}")


def print_results(results):
    """Prints summary statistics."""
    print("\nSummary Statistics:")
    print(
        f"- Total URLs processed: {len(results['matching_urls']) + len(results['missing_urls']) + len(results['non_200_urls'])}")
    print(f"- Matching URLs (200 status): {len(results['matching_urls'])}")
    print(f"- Missing URLs: {len(results['missing_urls'])}")
    print(f"- URLs with non-200 status codes: {len(results['non_200_urls'])}")


def main():
    parser = argparse.ArgumentParser(
        description="Process wget log and URL files.")
    parser.add_argument("log_file_path", help="Path to the wget log file")
    parser.add_argument(
        "url_file_path", help="Path to the file containing URLs")
    parser.add_argument(
        '--log-file', help='Optional file to write logs (in addition to console output)')

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.log_file)

    try:
        # Read target URLs
        target_urls = read_urls(args.url_file_path)
        if not target_urls:
            logging.error("No URLs found in the input file")
            sys.exit(1)

        logging.info(f"Starting analysis of log file: {args.log_file_path}")
        logging.info(f"Found {len(target_urls)} URLs to check")

        # Process log file
        patterns = compile_patterns()
        unique_logs = extract_log_entries(args.log_file_path, patterns)

        log_details = {
            details["url"]: details
            for log in unique_logs
            if (details := extract_details(log, patterns))
        }

        # Process results
        results = process_log_entries(log_details, target_urls)

        # Output results
        print_results(results)
        write_results_to_csv(results)

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
