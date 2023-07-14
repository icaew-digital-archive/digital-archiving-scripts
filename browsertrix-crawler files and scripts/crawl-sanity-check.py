#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Checks against list of URLs given to browsertrix with URLs crawled reported by the pages.jsonl log.
"""

import argparse
import json


def read_file_into_list(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file]


def load_jsonl(file_path):
    with open(file_path, 'r') as file:
        next(file)  # Skip first line
        return [json.loads(line) for line in file]


def print_matching_urls(url_list, pages_data):
    pages_data_url_list = []
    for entry in pages_data:
        if entry['url'] in url_list:
            print(entry['title'], '\n', entry['url'], '\n')
        pages_data_url_list.append(entry['url'])
    return pages_data_url_list


def print_missing_urls(url_list, pages_data_url_list):
    missing_urls = [url for url in url_list if url not in pages_data_url_list]
    print('URLs not found in pages.jsonl but present in the URL list file:')
    for url in missing_urls:
        print(url)


def main():
    parser = argparse.ArgumentParser(
        description='Check URLs against crawled data')
    parser.add_argument('url_list', help='Path to the URL list file')
    parser.add_argument('pages_jsonl', help='Path to the pages.jsonl file')
    args = parser.parse_args()

    url_list_file = args.url_list
    pages_json_file = args.pages_jsonl

    # Read URL file into list
    url_list = read_file_into_list(url_list_file)

    # Read JSON from pages.jsonl file
    pages_jsonl_data = load_jsonl(pages_json_file)

    # Print matching URLs
    pages_jsonl_data_url_list = print_matching_urls(url_list, pages_jsonl_data)

    # Print missing URLs if any
    print_missing_urls(url_list, pages_jsonl_data_url_list)


if __name__ == '__main__':
    main()
