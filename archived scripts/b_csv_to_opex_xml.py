#!/usr/bin/env python
"""
This script converts Dublin Core CSV data generated by 'a_files_to_csv.py' into OPEX XML files.

Usage: b_csv_to_opex_xml.py <csv_file> <output_dir> [--remove_empty_duplicates]
"""

import argparse
import csv
import os


def generate_metadata(checksum, title, description, security_descriptor, header, row, fixity_type, allow_empty_duplicates):
    descriptive_metadata = ''
    already_seen = []
    for i, field in enumerate(header):

        if allow_empty_duplicates:
            descriptive_metadata += f'{" " * 12}<{field}>{row[i].strip()}</{field}>\n'
        else:
            if field in already_seen and row[i] == '':
                continue
            else:
                descriptive_metadata += f'{" " * 12}<{field}>{row[i].strip()}</{field}>\n'

        if i == len(header) - 1:
            descriptive_metadata = descriptive_metadata.rstrip(
                "\n")  # Remove the trailing newline

        already_seen.append(field)

    # Template used to create OPEX XML files
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<opex:OPEXMetadata
    xmlns:opex="http://www.openpreservationexchange.org/opex/v1.1">
    <opex:Transfer>
        <opex:Fixities>
            <opex:Fixity type="{fixity_type}" value="{checksum}"/>
        </opex:Fixities>
    </opex:Transfer>
    <opex:Properties>
        <opex:Title>{title.strip()}</opex:Title>
        <opex:Description>{description.strip()}</opex:Description>
        <opex:SecurityDescriptor>{security_descriptor.strip()}</opex:SecurityDescriptor>
    </opex:Properties>
    <opex:DescriptiveMetadata>
        <oai_dc:dc xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ oai_dc.xsd"
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
{descriptive_metadata}
        </oai_dc:dc>
    </opex:DescriptiveMetadata>
</opex:OPEXMetadata>'''


def read_csv_file(csv_file, output_dir, allow_empty_duplicates):
    with open(csv_file, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        header = next(reader)

        # Determine fixity type from the header
        fixity_type = 'MD5' if header[1] == 'md5' else 'SHA-1'

        header = header[5:]  # Skip the first 5 columns from the headers

        for row in reader:
            # Extract the first 5 columns
            filename, checksum, title, description, security_descriptor = row[:5]
            row = row[5:]  # Remove the first 5 columns from the rows

            output_path = os.path.join(output_dir, filename + '.opex')

            metadata = generate_metadata(checksum, title, description,
                                         security_descriptor, header, row, fixity_type, allow_empty_duplicates)

            with open(output_path, 'w') as xmlfile:
                xmlfile.write(metadata)


def main():
    parser = argparse.ArgumentParser(
        description='Convert CSV data to OPEX XML format.')
    parser.add_argument('csv_input', help='Path to the CSV file')
    parser.add_argument(
        'output_dir', help='Path to the output directory for OPEX XML files')
    parser.add_argument('--allow_empty_duplicates', '-rd', action='store_true',
                        help='Allow empty duplicate elements')
    args = parser.parse_args()

    read_csv_file(args.csv_input, args.output_dir,
                  args.allow_empty_duplicates)


if __name__ == '__main__':
    main()
