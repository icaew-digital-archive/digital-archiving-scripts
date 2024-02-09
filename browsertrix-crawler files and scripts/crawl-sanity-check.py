#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Checks against a list of URLs given to browsertrix with URLs crawled reported by the pages.jsonl log.
"""

import argparse
import json


def read_urls_from_file(file_path):
    """Reads URLs from a given file and returns them as a set."""
    try:
        with open(file_path, 'r') as file:
            return set(line.strip() for line in file)
    except IOError as e:
        print(f"Error reading file {file_path}: {e}")
        return set()


def load_jsonl_to_set(file_path, url_key='url', skip_first_line=False):
    """Loads JSON Lines from a given file, optionally skipping the first line, and extracts URLs into a set."""
    urls = set()
    try:
        with open(file_path, 'r') as file:
            if skip_first_line:
                next(file)  # Skip the first line if necessary
            for line_number, line in enumerate(file, start=1):
                try:
                    json_line = json.loads(line)
                    url = json_line.get(url_key)  # Use .get() to avoid KeyError
                    if url:
                        urls.add(url)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON on line {line_number}: {e}")
    except IOError as e:
        print(f"Error reading file {file_path}: {e}")
    return urls



def compare_and_print_results(url_list, pages_urls):
    """Compares two sets of URLs and prints matching and missing URLs."""
    matching_urls = url_list.intersection(pages_urls)
    missing_urls = url_list.difference(pages_urls)

    if matching_urls:
        print("Matching URLs:")
        for url in matching_urls:
            print(url)
    else:
        print("No matching URLs found.")

    if missing_urls:
        print("\nURLs not found in pages.jsonl but present in the URL list file:")
        for url in missing_urls:
            print(url)
    else:
        print("\nNo missing URLs.")


def main():
    parser = argparse.ArgumentParser(description='Check URLs against crawled data')
    parser.add_argument('url_list', help='Path to the URL list file')
    parser.add_argument('pages_jsonl', help='Path to the pages.jsonl file')
    args = parser.parse_args()

    url_list = read_urls_from_file(args.url_list)
    pages_urls = load_jsonl_to_set(args.pages_jsonl)

    compare_and_print_results(url_list, pages_urls)


if __name__ == '__main__':
    main()
