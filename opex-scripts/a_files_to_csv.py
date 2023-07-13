#!/usr/bin/env python
"""
This script reads a folder of files calculates a sha1/md5 hash of each and then generates a Dublin Core CSV file template.

This generated CSV file can be used in conjunction with b_csv_to_opex_xml.py to produce OPEX XML files.

Usage: a_files_to_csv.py [-h] [--hash_type {sha1,md5}] directory output
"""

import argparse
import csv
import hashlib
import os


def calculate_hash(file_path, hash_type='sha1'):
    hash_function = getattr(hashlib, hash_type)()
    with open(file_path, 'rb') as file:
        for chunk in iter(lambda: file.read(4096), b''):
            hash_function.update(chunk)
    return hash_function.hexdigest()


def list_files(directory, output_file, hash_type='sha1'):
    row = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            hash = calculate_hash(file_path, hash_type)
            row.append([file, hash, '', '', '', '', '', '', '',
                        '', '', '', '', '', '', '', '', '', '', ''])

    with open(output_file, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['filename', hash_type, 'Title', 'Description', 'SecurityDescriptor', 'Title', 'Creator', 'Subject', 'Description',
                        'Publisher', 'Contributor', 'Date', 'Type', 'Format', 'Identifier', 'Source', 'Language', 'Relation', 'Coverage', 'Rights'])
        writer.writerows(row)

    print(
        f"File list with {hash_type} checksums successfully saved to {output_file}.")


def main():
    parser = argparse.ArgumentParser(
        description='List files in a directory and calculate checksums.')
    parser.add_argument('directory', help='Directory path to search for files')
    parser.add_argument('output', help='Output file path (CSV format)')
    parser.add_argument('--hash_type', '-t', help='Checksum algorithm to use (sha1, md5)',
                        choices=['sha1', 'md5'], default='sha1')
    args = parser.parse_args()

    directory_path = args.directory
    output_file_path = args.output
    hash_type = args.hash_type

    list_files(directory_path, output_file_path, hash_type)


if __name__ == '__main__':
    main()
