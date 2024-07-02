#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generates checksum values for files in a directory and writes them to a CSV file.
"""

import os
import hashlib
import csv
import argparse
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to calculate checksum of a file
def calculate_checksum(file_path, algorithm):
    hash_func = getattr(hashlib, algorithm)()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(65536)  # Read the file in chunks to avoid memory issues with large files
            if not data:
                break
            hash_func.update(data)
    return hash_func.hexdigest()

# Function to generate checksums and write to CSV
def generate_checksums(directory, output_csv, algorithm):
    with open(output_csv, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow([f'{algorithm.upper()} Checksum', 'Filename'])

        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                checksum = calculate_checksum(file_path, algorithm)
                csvwriter.writerow([checksum, file])
                logging.info(f'Processed file: {file}')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate checksum values for local files.")
    parser.add_argument('folder_directory', type=str, help='The directory containing files')
    parser.add_argument('output_csv', type=str, help='The output CSV file')
    parser.add_argument('algorithm', type=str, choices=hashlib.algorithms_available,
                        help='The checksum algorithm to use')
    args = parser.parse_args()

    folder_directory = args.folder_directory
    output_csv = args.output_csv
    algorithm = args.algorithm

    generate_checksums(folder_directory, output_csv, algorithm)
    logging.info(f"{algorithm.upper()} checksums and filenames have been written to {output_csv}")


