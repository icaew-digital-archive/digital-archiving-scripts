#!/usr/bin/env python
"""
This script reads a folder of files, calculates a sha1/md5 hash of each, and then generates a Dublin Core CSV file template.
This generated CSV file can be used in conjunction with b_csv_to_opex_xml.py to produce OPEX XML files.

Usage: a_files_to_csv.py [-h] [--hash_type {sha1,md5}] directory output
"""

import argparse
import csv
import hashlib
import os

# Constants
COLUMN_NAMES = [
    'filename', 'hash', 'Title', 'Description', 'SecurityDescriptor',
    'dc:title', 'dc:creator', 'dc:subject', 'dc:description',
    'dc:publisher', 'dc:contributor', 'dc:date', 'dc:type', 'dc:format',
    'dc:identifier', 'dc:source', 'dc:language', 'dc:relation',
    'dc:coverage', 'dc:rights'
]
HASH_TYPES = {'sha1', 'md5'}


def calculate_hash(file_path, hash_type='sha1'):
    hash_function = hashlib.new(hash_type)
    with open(file_path, 'rb') as file:
        for chunk in iter(lambda: file.read(4096), b''):
            hash_function.update(chunk)
    return hash_function.hexdigest()


def list_files(directory, output_file, hash_type='sha1'):
    if not os.path.exists(directory):
        print(f"Directory '{directory}' does not exist.")
        return

    if not hash_type in HASH_TYPES:
        print(
            f"Invalid hash type '{hash_type}'. Supported types: {', '.join(HASH_TYPES)}.")
        return

    if not output_file.lower().endswith('.csv'):
        output_file += '.csv'

    rows = []
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            hash_value = calculate_hash(file_path, hash_type)
            rows.append([file, hash_value] + [''] * (len(COLUMN_NAMES) - 2))

    with open(output_file, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(COLUMN_NAMES)
        writer.writerows(rows)

    print(
        f"File list with {hash_type} checksums successfully saved to {output_file}.")


def main():
    parser = argparse.ArgumentParser(
        description='List files in a directory and calculate checksums.')
    parser.add_argument('input_dir', help='Directory path to search for files')
    parser.add_argument('csv_output', help='Output file path (CSV format)')
    parser.add_argument('--hash_type', '-t', help='Checksum algorithm to use (sha1, md5)',
                        choices=HASH_TYPES, default='sha1')
    args = parser.parse_args()

    list_files(args.input_dir, args.csv_output, args.hash_type)


if __name__ == '__main__':
    main()
