#!/usr/bin/env python
"""
This script renames the filenames to filenames given in the Title field (row[2]) from the csv produced by a_files_to_csv.py.

This would typically be run after the csv has been completed and before b_csv_to_opex_xml.py

Usage: csv_file_rename.py [-h] file_directory csv_file_path
"""

import csv
import os
import argparse

def main(file_directory, csv_file_path):
    # Get a list of all files in the directory
    file_list = os.listdir(file_directory)

    # Set used to detect duplicates
    seen = set()

    # Open the CSV file for reading row[2], detect duplicates and empty Title fields
    with open(csv_file_path, mode='r', newline='') as csv_file:
        csv_reader = csv.reader(csv_file)

        # Skip the first line (header)
        next(csv_reader, None)

        # Loop through the first column of the CSV file
        for row in csv_reader:
            if row[2] == '':
                raise ValueError('An empty Title field has been detected in the CSV file')

            if row[2] not in seen:
                seen.add(row[2])
            else:
                raise ValueError('A duplicate Title field has been detected in the CSV file')

    # Open the CSV file for reading
    with open(csv_file_path, mode='r', newline='') as csv_file:
        csv_reader = csv.reader(csv_file)

        # Skip the first line (header)
        next(csv_reader, None)

        # Loop through the first column of the CSV file
        for row in csv_reader:
            if row[0] in file_list:
                ext = os.path.splitext(row[0])[1]
                os.rename(os.path.join(file_directory, row[0]), os.path.join(file_directory, row[2].strip() + ext))
                print(f"File '{row[0]}' has been renamed to '{os.path.join(file_directory, row[2].strip() + ext)}'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Rename files based on a CSV mapping.')
    parser.add_argument('file_directory', help='Path to the directory containing files to rename')
    parser.add_argument('csv_file_path', help='Path to the CSV file with mapping information')

    args = parser.parse_args()
    main(args.file_directory, args.csv_file_path)
