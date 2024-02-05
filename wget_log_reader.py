#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Reads the wget log file and uses regex matching to compare to the url list 
input to wget to verify the success of a crawl.

Errors are logged to: error_log.txt.
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
        return [line.strip() for line in file]


def main(log_file_path, url_file_path, error_log_path):
    patterns = compile_patterns()

    unique_logs = extract_log_entries(log_file_path, patterns)
    log_details = {details["url"]: details for log in unique_logs if (
        details := extract_details(log, patterns))}

    urls_to_check = read_urls(url_file_path)

    with open(error_log_path, 'a') as error_log:
        for url in urls_to_check:
            details = log_details.get(url)
            if details:
                if details["status_code"] == "200" and details["length"] == details["saved_number"]:
                    print(
                        f"{url} is in logs, status code 200, and length matches saved number.")
                else:
                    error_log.write(
                        f"{url} is in logs, but does not meet all conditions.\n")
                    print(f"{url} is in logs, but does not meet all conditions.")
            else:
                error_log.write(f"{url} is not in logs.\n")
                print(f"{url} is not in logs.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process log and URL files.")
    parser.add_argument("log_file_path", help="Path to the log file")
    parser.add_argument(
        "url_file_path", help="Path to the file containing URLs")
    parser.add_argument(
        "--error_log_path", help="Path to the error log file", default="error_log.txt")

    args = parser.parse_args()

    main(args.log_file_path, args.url_file_path, args.error_log_path)
