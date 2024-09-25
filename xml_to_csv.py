#!/usr/bin/env python3
"""
This script converts an XML file into a CSV file. It parses the XML data and extracts
all 'item' elements, converting each item and its associated elements into a row in the CSV.
The script handles XML elements with missing data by filling those fields with empty strings.

Usage:
    python script.py <input_xml_file> <output_csv_file>

Arguments:
    xml_file: The path to the input XML file.
    csv_file: The desired output CSV filename.
"""

import xml.etree.ElementTree as ET
import csv
import argparse


def parse_xml_to_csv(xml_file, csv_file):
    # Parse XML file
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Find all 'item' elements
    items = root.findall('.//item')

    if not items:
        print("No items found in the XML file.")
        return

    # Extract headers from the first item
    headers = [elem.tag for elem in items[0]]

    # Create CSV file
    with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
        # Ensure proper quoting
        csvwriter = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)

        # Write headers
        csvwriter.writerow(headers)

        # Write item data
        for item in items:
            row = [item.find(header).text if item.find(header)
                   is not None else '' for header in headers]
            csvwriter.writerow(row)

    print(f"CSV file '{csv_file}' created successfully.")


if __name__ == "__main__":
    # Set up the argument parser
    parser = argparse.ArgumentParser(description='Convert an XML file to CSV.')
    parser.add_argument('xml_file', help='The path to the input XML file.')
    parser.add_argument('csv_file', help='The desired output CSV filename.')

    # Parse the command line arguments
    args = parser.parse_args()

    # Run the XML to CSV conversion
    parse_xml_to_csv(args.xml_file, args.csv_file)
