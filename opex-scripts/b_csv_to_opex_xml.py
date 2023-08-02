#!/usr/bin/env python
"""
This script reads the Dublin Core CSV template produced by a_files_to_csv.py and outputs OPEX XML files.

Usage: b_csv_to_opex_xml.py csv_file, output_dir
"""

import argparse
import csv
import os


def write_xml_file(output_path, checksum, title, description, security_descriptor, header, row, fixity_type, include_full_dc):
    descriptive_metadata = ''
    for i, field in enumerate(header):
        if include_full_dc:
            descriptive_metadata += f'{12 * " "}<dc:{field.lower()}>{row[i]}</dc:{field.lower()}>\n'
        else:
            if row[i] != '':  # Only write the Dublin Core field if the cell the CSV is not empty
                descriptive_metadata += f'{12 * " "}<dc:{field.lower()}>{row[i]}</dc:{field.lower()}>\n'
        if i == len(header) - 1:
            descriptive_metadata = descriptive_metadata[:len(
                descriptive_metadata)-1]  # Remove the final character, i.e. the \n

    # Template used to output to the OPEX XML files
    template = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<opex:OPEXMetadata
    xmlns:opex="http://www.openpreservationexchange.org/opex/v1.1">
    <opex:Transfer>
        <opex:Fixities>
            <opex:Fixity type="{fixity_type}" value="{checksum}"/>
        </opex:Fixities>
    </opex:Transfer>
    <opex:Properties>
        <opex:Title>{title}</opex:Title>
        <opex:Description>{description}</opex:Description>
        <opex:SecurityDescriptor>{security_descriptor}</opex:SecurityDescriptor>
    </opex:Properties>
    <opex:DescriptiveMetadata>
        <oai_dc:dc xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ oai_dc.xsd"
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
{descriptive_metadata}
        </oai_dc:dc>
    </opex:DescriptiveMetadata>
</opex:OPEXMetadata>"""

    with open(output_path, 'w') as xmlfile:
        xmlfile.write(template)


def read_csv_file(csv_file, output_dir, include_full_dc):
    with open(csv_file, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        header = next(reader)

        # Get fixity type from the header
        fixity_type = 'MD5' if header[1] == 'md5' else 'SHA-1'

        header = header[5:]  # Remove the first 5 columns from the headers

        for row in reader:
            filename, checksum, title, description, security_descriptor = row[:5]  # Unpack the first 5 columns from the row
            row = row[5:]  # Remove the first 5 columns from the rows

            output_path = os.path.join(output_dir, filename + '.opex')
            write_xml_file(output_path, checksum, title, description,
                           security_descriptor, header, row, fixity_type, include_full_dc)


def main():
    parser = argparse.ArgumentParser(description='Read data from a CSV file.')
    parser.add_argument('csv_file', help='Path to the CSV file')
    parser.add_argument(
        'output_dir', help='Path to the output directory for OPEX XML files')
    parser.add_argument('--include_full_dc_template', '-dc', action='store_true',
                        help='Include the full Dublin Core template in the OPEX XML output even if the CSV fields are empty')
    args = parser.parse_args()

    csv_file_path = args.csv_file
    output_directory = args.output_dir
    include_full_dc = args.include_full_dc_template

    read_csv_file(csv_file_path, output_directory, include_full_dc)


if __name__ == '__main__':
    main()
