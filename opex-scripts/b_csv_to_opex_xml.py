#!/usr/bin/env python
"""
This script converts Dublin Core CSV data generated by 'a_files_to_csv.py' into OPEX XML files.

Usage: b_csv_to_opex_xml.py <csv_file> <output_dir> [--allow_empty_duplicates] [--disable_sanitization]
"""

import argparse
import csv
import os
import xml.sax.saxutils as saxutils
import logging
import io


class InMemoryHandler(logging.Handler):
    """
    A logging handler that keeps logs in memory.
    """
    def __init__(self):
        super().__init__()
        self.log_entries = []

    def emit(self, record):
        self.log_entries.append(self.format(record))

    def has_logs(self):
        return len(self.log_entries) > 0

    def get_logs(self):
        return "\n".join(self.log_entries)


def setup_logger():
    """
    Set up the logger to report escaped characters to both a file and the console.
    """
    logger = logging.getLogger('xml_sanitizer')
    logger.setLevel(logging.INFO)

    # In-memory handler to check if there are any logs
    in_memory_handler = InMemoryHandler()
    in_memory_handler.setLevel(logging.INFO)
    in_memory_formatter = logging.Formatter('%(asctime)s - %(message)s')
    in_memory_handler.setFormatter(in_memory_formatter)
    logger.addHandler(in_memory_handler)

    # Stream handler for logging to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger, in_memory_handler


logger, in_memory_handler = setup_logger()


def sanitize_xml_string(value, row_num, col_name, disable_sanitization):
    """
    Sanitize a string for XML by escaping illegal characters and log the changes.
    """
    if disable_sanitization:
        return value

    original_value = value
    sanitized_value = saxutils.escape(value)
    if original_value != sanitized_value:
        logger.info(f'Row {row_num}, Column "{col_name}": {original_value} -> {sanitized_value}')
    return sanitized_value


def generate_metadata(checksum, title, description, security_descriptor, header, row, fixity_type, allow_empty_duplicates, row_num, disable_sanitization):
    descriptive_metadata = ''
    already_seen = []
    for i, field in enumerate(header):

        sanitized_value = sanitize_xml_string(row[i].strip(), row_num, field, disable_sanitization)

        if allow_empty_duplicates:
            descriptive_metadata += f'{" " * 12}<{field}>{sanitized_value}</{field}>\n'
        else:
            if field in already_seen and sanitized_value == '':
                continue
            else:
                descriptive_metadata += f'{" " * 12}<{field}>{sanitized_value}</{field}>\n'

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
            <opex:Fixity type="{sanitize_xml_string(checksum, row_num, 'checksum', disable_sanitization)}"/>
        </opex:Fixities>
    </opex:Transfer>
    <opex:Properties>
        <opex:Title>{sanitize_xml_string(title, row_num, 'title', disable_sanitization)}</opex:Title>
        <opex:Description>{sanitize_xml_string(description, row_num, 'description', disable_sanitization)}</opex:Description>
        <opex:SecurityDescriptor>{sanitize_xml_string(security_descriptor, row_num, 'security_descriptor', disable_sanitization)}</opex:SecurityDescriptor>
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


def read_csv_file(csv_file, output_dir, allow_empty_duplicates, disable_sanitization):
    with open(csv_file, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        header = next(reader)

        # Determine fixity type from the header
        fixity_type = 'MD5' if header[1] == 'md5' else 'SHA-1'

        header = header[5:]  # Skip the first 5 columns from the headers

        for row_num, row in enumerate(reader, start=1):
            # Extract the first 5 columns
            filename, checksum, title, description, security_descriptor = row[:5]
            row = row[5:]  # Remove the first 5 columns from the rows

            output_path = os.path.join(output_dir, filename + '.opex')

            metadata = generate_metadata(checksum, title, description,
                                         security_descriptor, header, row, fixity_type, allow_empty_duplicates, row_num, disable_sanitization)

            with open(output_path, 'w') as xmlfile:
                xmlfile.write(metadata)

    # Write to the log file if there are any log entries
    if in_memory_handler.has_logs():
        with open('sanitization_report.log', 'w') as log_file:
            log_file.write(in_memory_handler.get_logs())


def main():
    parser = argparse.ArgumentParser(
        description='Convert CSV data to OPEX XML format.')
    parser.add_argument('csv_input', help='Path to the CSV file')
    parser.add_argument(
        'output_dir', help='Path to the output directory for OPEX XML files')
    parser.add_argument('--allow_empty_duplicates', '-rd', action='store_true',
                        help='Allow empty duplicate elements')
    parser.add_argument('--disable_sanitization', action='store_true',
                        help='Disable sanitization of XML characters')
    args = parser.parse_args()

    read_csv_file(args.csv_input, args.output_dir,
                  args.allow_empty_duplicates, args.disable_sanitization)


if __name__ == '__main__':
    main()

