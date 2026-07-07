#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Log Analysis with wget_log_reader.py

The script analyzes wget log files and compares them against the original URL list.
Generates four CSV files with timestamps:
- matching_urls_[timestamp].csv: URLs successfully crawled with 200 status
- missing_urls_[timestamp].csv: URLs not found in the archives
- non_200_urls_[timestamp].csv: URLs with non-200 status codes (excluding redirects)
- redirections_[timestamp].csv: URLs that returned a 3xx redirect, with destination

Usage:
    python wget_log_reader.py <log_file_path> <url_file_path>
"""

import re
import argparse
import csv
from datetime import datetime


def compile_patterns():
    return {
        "log_entry": re.compile(r"--\d{4}-\d{2}-\d{2}.*?(?=--\d{4}-\d{2}-\d{2}|$)", re.DOTALL),
        "url": re.compile(r"https?://[^\s]+"),
        "status_code": re.compile(r"response... (\d{3})"),
        "length": re.compile(r"Length: (\d+)"),
        "length_unspecified": re.compile(r"Length: unspecified"),
        "saved_number": re.compile(r"saved \[(\d+)\]"),
        "redirect_location": re.compile(r"Location: (https?://[^\s\[]+)")
    }


def extract_log_entries(file_path, patterns):
    with open(file_path, 'r') as file:
        log_data = file.read()
    return patterns["log_entry"].findall(log_data)


def extract_details(log_entry, patterns):
    url_match = patterns["url"].search(log_entry)
    status_match = patterns["status_code"].search(log_entry)
    length_match = patterns["length"].search(log_entry)
    length_unspecified = patterns["length_unspecified"].search(log_entry) is not None
    saved_match = patterns["saved_number"].search(log_entry)
    redirect_match = patterns["redirect_location"].search(log_entry)

    return {
        "url": url_match.group(0) if url_match else None,
        "status_code": status_match.group(1) if status_match else None,
        "length": length_match.group(1) if length_match else None,
        "length_unspecified": length_unspecified,
        "saved_number": saved_match.group(1) if saved_match else None,
        "redirect_location": redirect_match.group(1).strip() if redirect_match else None
    }


def read_urls(file_path):
    with open(file_path, 'r') as file:
        return list(set(line.strip() for line in file))  # De-duplicate URLs


def categorize_url(url, details):
    """
    Categorize a URL based on its status in the log.
    Returns: 'matching', 'missing', or 'non_200'
    """
    if not details or not details["url"]:
        return 'missing'

    if not details["status_code"]:
        return 'non_200'

    if details["status_code"].startswith("3"):
        return 'redirect'

    if details["status_code"] != "200":
        return 'non_200'

    return 'matching'


def main(log_file_path, url_file_path):
    patterns = compile_patterns()

    unique_logs = extract_log_entries(log_file_path, patterns)
    log_details = {details["url"]: details for log in unique_logs if (
        details := extract_details(log, patterns))}

    urls_to_check = read_urls(url_file_path)

    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Initialize lists for each category
    matching_urls = []
    missing_urls = []
    non_200_urls = []
    redirect_urls = []

    # Categorize each URL
    for url in urls_to_check:
        details = log_details.get(url)
        category = categorize_url(url, details)

        if category == 'matching':
            matching_urls.append({
                'url': url,
                'status_code': details.get('status_code', 'N/A'),
                'saved_bytes': details.get('saved_number', 'N/A')
            })
        elif category == 'missing':
            missing_urls.append({'url': url})
        elif category == 'redirect':
            redirect_urls.append({
                'original_url': url,
                'redirect_url': details.get('redirect_location', 'N/A') if details else 'N/A',
                'status_code': details.get('status_code', 'N/A') if details else 'N/A'
            })
        else:  # non_200
            non_200_urls.append({
                'url': url,
                'status_code': details.get('status_code', 'N/A') if details else 'N/A'
            })

    # Write CSV files
    matching_file = f"matching_urls_{timestamp}.csv"
    missing_file = f"missing_urls_{timestamp}.csv"
    non_200_file = f"non_200_urls_{timestamp}.csv"
    redirections_file = f"redirections_{timestamp}.csv"

    with open(matching_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['url', 'status_code', 'saved_bytes'])
        writer.writeheader()
        writer.writerows(matching_urls)

    with open(missing_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['url'])
        writer.writeheader()
        writer.writerows(missing_urls)

    with open(non_200_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['url', 'status_code'])
        writer.writeheader()
        writer.writerows(non_200_urls)

    with open(redirections_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['original_url', 'redirect_url', 'status_code'])
        writer.writeheader()
        writer.writerows(redirect_urls)

    # Print summary
    total = len(urls_to_check)
    print(f"\n{'='*60}")
    print(f"Log Analysis Summary:")
    print(f"  Total URLs checked: {total}")
    print(f"  Matching (200 status): {len(matching_urls)}")
    print(f"  Missing (not found): {len(missing_urls)}")
    print(f"  Redirected (3xx): {len(redirect_urls)}")
    print(f"  Non-200 status codes: {len(non_200_urls)}")
    print(f"{'='*60}")
    print(f"\nGenerated CSV files:")
    print(f"  - {matching_file}")
    print(f"  - {missing_file}")
    print(f"  - {non_200_file}")
    print(f"  - {redirections_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze wget log files and compare against URL list. "
                    "Generates three CSV files with timestamps: matching_urls, missing_urls, and non_200_urls."
    )
    parser.add_argument("log_file_path", help="Path to the wget log file")
    parser.add_argument("url_file_path", help="Path to the file containing URLs to check")

    args = parser.parse_args()

    main(args.log_file_path, args.url_file_path)

