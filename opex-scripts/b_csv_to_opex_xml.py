#!/usr/bin/env python
"""
This script reads the Dublin Core CSV template produced by a_files_to_csv.py and outputs OPEX XML files.

Usage: b_csv_to_opex_xml.py csv_file, output_dir
"""

import argparse
import csv
import os


def write_xml_file(output_path, checksum, title, description, security_descriptor, header, row, fixity_type):
    descriptive_metadata = ''
    for i, field in enumerate(header):
        # Write descriptive metadata lines
        if i == len(header) - 1:
            descriptive_metadata += f'{12 * " "}<dc:{field.lower()}>{row[i]}</dc:{field.lower()}>' # If the final line omit the \n
        else:
            descriptive_metadata += f'{12 * " "}<dc:{field.lower()}>{row[i]}</dc:{field.lower()}>\n'

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


def read_csv_file(csv_file, output_dir):
    with open(csv_file, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        header = next(reader)

        # Get fixity type from the header
        if header[1] == 'md5':
            fixity_type = 'MD5'
        else:
            fixity_type = 'SHA-1'

        header = header[5:] # Remove the first 5 columns from the headers

        for row in reader:
            filename = row[0]  # Get filename for OPEX file
            checksum = row[1]  # Get checksum
            title = row[2]  # Get Title
            description = row[3]  # Get Description
            security_descriptor = row[4]  # Get SecurityDescriptor
            row = row[5:]  # Remove the first 5 columns from the rows

            output_path = os.path.join(output_dir, filename + '.opex')
            write_xml_file(output_path, checksum, title, description, security_descriptor, header, row, fixity_type)


def main():
    parser = argparse.ArgumentParser(description='Read data from a CSV file.')
    parser.add_argument('csv_file', help='Path to the CSV file')
    parser.add_argument('output_dir', help='Path to the output directory for OPEX XML files')
    args = parser.parse_args()

    csv_file_path = args.csv_file
    output_directory = args.output_dir

    read_csv_file(csv_file_path, output_directory)


if __name__ == '__main__':
    main()
