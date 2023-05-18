#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Checks against list of URLs given to browsertrix with URLs crawled reported by the pages.jsonl log.
"""

import json

URL_LIST_FILE = ''
PAGES_JSON = ''

# Read URL file into list
with open(URL_LIST_FILE, 'r') as f:
    url_list = [line.strip() for line in f]

# Read JSON from pages.jsonl file
with open(PAGES_JSON, 'r') as f:
    next(f)  # Skip first line
    pages_jsonl_data = [json.loads(line) for line in f]

# Create empty list to store the URLs from pages.jsonl
pages_jsonl_data_url_list = []

# Loop through pages_jsonl_data to append
for entry in pages_jsonl_data:
    # Print to console page titles and URLs
    if entry['url'] in url_list:
        print(entry['title'], '\n', entry['url'], '\n')
    pages_jsonl_data_url_list.append(entry['url'])

# Print missing URLs if any
for url in url_list:
    if url not in pages_jsonl_data_url_list:
        print('\nMISSING:', url)
