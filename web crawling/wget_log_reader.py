#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Reads the wget log file and uses regex matching to compare to the URL list
input to wget to verify the success of a crawl.

Errors are logged to: error_log.txt with details of unmet criteria.
"""

import re
import argparse


def compile_patterns():
    return {
        "log_entry": re.compile(r"--\d{4}-\d{2}-\d{2}.*?\d+\]\n", re.DOTALL),
        "url": re.compile(r"https?://[^\s]+"),
        "status_code": re.compile(r"response... (\d{3})"),
        "length": re.compile(r"Length: (\d+)"),
        "saved_number": re.compile(r"saved \[(\d+)/")
    }


def extract_log_entries(file_path, patterns):
    with open(file_path, 'r') as file:
        log_data = file.read()
    return patterns["log_entry"].findall(log_data)


def extract_details(log_entry, patterns):
    return {
        "url": (match := patterns["url"].search(log_entry)) and match.group(0),
        "status_code": (match := patterns["status_code"].search(log_entry)) and match.group(1),
        "length": (match := patterns["length"].search(log_entry)) and match.group(1),
        "saved_number": (match := patterns["saved_number"].search(log_entry)) and match.group(1)
    }


def read_urls(file_path):
    with open(file_path, 'r') as file:
        return list(set(line.strip() for line in file))  # De-duplicate URLs


def check_url_details(url, details, error_log):
    errors = []

    if not details:
        errors.append("URL not found in log.")
    else:
        if details["status_code"] != "200":
            errors.append(f"Status code mismatch (found {details['status_code']}, expected 200).")
        if details["length"] != details["saved_number"]:
            errors.append(
                f"Length mismatch (Length: {details['length']}, Saved: {details['saved_number']})."
            )
    
    if errors:
        error_log.write(f"{url} errors:\n")
        for error in errors:
            error_log.write(f"  - {error}\n")
        error_log.write("\n")  # Add a line break after each URL entry

        # Print errors to console
        print(f"{url} failed checks:")
        for error in errors:
            print(f"  - {error}")
        print()

        return False  # Indicates the URL failed some checks

    return True  # Indicates the URL passed all checks


def main(log_file_path, url_file_path, error_log_path):
    patterns = compile_patterns()

    unique_logs = extract_log_entries(log_file_path, patterns)
    log_details = {details["url"]: details for log in unique_logs if (
        details := extract_details(log, patterns))}

    urls_to_check = read_urls(url_file_path)

    with open(error_log_path, 'w') as error_log:  # Overwrite old errors
        for url in urls_to_check:
            details = log_details.get(url)
            check_url_details(url, details, error_log)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process log and URL files.")
    parser.add_argument("log_file_path", help="Path to the log file")
    parser.add_argument("url_file_path", help="Path to the file containing URLs")
    parser.add_argument("--error_log_path", help="Path to the error log file", default="error_log.txt")

    args = parser.parse_args()

    main(args.log_file_path, args.url_file_path, args.error_log_path)

