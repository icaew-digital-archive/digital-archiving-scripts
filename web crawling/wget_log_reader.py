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
        "log_entry": re.compile(r"--\d{4}-\d{2}-\d{2}.*?(?=--\d{4}-\d{2}-\d{2}|$)", re.DOTALL),
        "url": re.compile(r"https?://[^\s]+"),
        "status_code": re.compile(r"response... (\d{3})"),
        "length": re.compile(r"Length: (\d+)"),
        "length_unspecified": re.compile(r"Length: unspecified"),
        "saved_number": re.compile(r"saved \[(\d+)\]")
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
    
    return {
        "url": url_match.group(0) if url_match else None,
        "status_code": status_match.group(1) if status_match else None,
        "length": length_match.group(1) if length_match else None,
        "length_unspecified": length_unspecified,
        "saved_number": saved_match.group(1) if saved_match else None
    }


def read_urls(file_path):
    with open(file_path, 'r') as file:
        return list(set(line.strip() for line in file))  # De-duplicate URLs


def check_url_details(url, details, error_log):
    errors = []

    if not details or not details["url"]:
        errors.append("URL not found in log.")
    else:
        # Check HTTP status code
        if not details["status_code"]:
            errors.append("HTTP status code not found in log entry.")
        elif details["status_code"] != "200":
            status_code = details["status_code"]
            # Provide more specific error messages based on status code type
            if status_code.startswith("4"):
                error_type = "Client Error"
            elif status_code.startswith("5"):
                error_type = "Server Error"
            elif status_code.startswith("3"):
                error_type = "Redirect"
            else:
                error_type = "Unexpected Status"
            errors.append(f"HTTP {error_type} (status code {status_code}, expected 200).")
        # When length is unspecified, we can't compare it to saved_number
        # Just verify that saved_number exists and is > 0
        if details["length_unspecified"]:
            if not details["saved_number"] or int(details["saved_number"]) == 0:
                errors.append(f"Length unspecified but saved number is invalid (Saved: {details['saved_number']}).")
        elif details["length"] and details["saved_number"]:
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

    passed_count = 0
    failed_count = 0

    with open(error_log_path, 'w') as error_log:  # Overwrite old errors
        for url in urls_to_check:
            details = log_details.get(url)
            if check_url_details(url, details, error_log):
                passed_count += 1
            else:
                failed_count += 1
    
    # Print summary
    total = len(urls_to_check)
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total URLs checked: {total}")
    print(f"  Passed: {passed_count}")
    print(f"  Failed: {failed_count}")
    print(f"{'='*60}")
    
    if failed_count > 0:
        print(f"\nErrors logged to: {error_log_path}")
    else:
        print(f"\n✓ All URLs passed validation checks!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process log and URL files.")
    parser.add_argument("log_file_path", help="Path to the log file")
    parser.add_argument("url_file_path", help="Path to the file containing URLs")
    parser.add_argument("--error_log_path", help="Path to the error log file", default="error_log.txt")

    args = parser.parse_args()

    main(args.log_file_path, args.url_file_path, args.error_log_path)

