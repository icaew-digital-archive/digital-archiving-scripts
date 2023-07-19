#!/usr/bin/env python
"""
This script reads a folder of files and generates a folder OPEX XML file and saves it in the same folder path.

Used in conjunction with a_files_to_csv.py and b_csv_to_opex_xml.py.

Usage: c_folders_of_files_to_folder_opex_xml.py folder_path
"""

import os
import argparse


def get_files_in_folder(folder_path):
    file_list = [file_name for file_name in os.listdir(
        folder_path) if os.path.isfile(os.path.join(folder_path, file_name))]
    return file_list


def create_xml_file(folder_path, xml_filename, descriptive_metadata):
    files = sorted(get_files_in_folder(folder_path))

    opex_file = ''
    for i, file in enumerate(files):
        if 'opex' in file:
            opex_file += f'{20 * " "}<opex:File type="metadata">{file}</opex:File>'
            if i != len(files) - 1:  # If not the final line, add a newline char
                opex_file += '\n'
        else:
            opex_file += f'{20 * " "}<opex:File type="content">{file}</opex:File>'
            if i != len(files) - 1:  # If not the final line, add a newline char
                opex_file += '\n'

    if descriptive_metadata:
        descriptive_metadata = """
        <opex:DescriptiveMetadata>
            <oai_dc:dc xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ oai_dc.xsd"
                xmlns:dc="http://purl.org/dc/elements/1.1/"
                xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                <dc:title></dc:title>
                <dc:creator></dc:creator>
                <dc:subject></dc:subject>
                <dc:description></dc:description>
                <dc:publisher></dc:publisher>
                <dc:contributor></dc:contributor>
                <dc:date></dc:date>
                <dc:type></dc:type>
                <dc:format></dc:format>
                <dc:identifier></dc:identifier>
                <dc:source></dc:source>
                <dc:language></dc:language>
                <dc:relation></dc:relation>
                <dc:coverage></dc:coverage>
                <dc:rights></dc:rights>
            </oai_dc:dc>
        </opex:DescriptiveMetadata>"""
    else:
        descriptive_metadata = ""

    template = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <opex:OPEXMetadata
        xmlns:opex="http://www.openpreservationexchange.org/opex/v1.1">
        <opex:Transfer>
            <opex:SourceID></opex:SourceID>
            <opex:Manifest>
                <opex:Files>
{opex_file}
                </opex:Files>
            </opex:Manifest>
        </opex:Transfer>
        <opex:Properties>
            <opex:Title></opex:Title>
            <opex:Description></opex:Description>
            <opex:SecurityDescriptor></opex:SecurityDescriptor>
        </opex:Properties>{descriptive_metadata}
    </opex:OPEXMetadata>"""

    with open(os.path.join(folder_path, xml_filename + '.opex'), 'w') as xml_file:
        xml_file.write(template)

    print(f"OPEX XML file '{xml_filename + '.opex'}' created successfully.")


def main():
    parser = argparse.ArgumentParser(
        description='Generate an OPEX XML file based on files in a folder.')
    parser.add_argument(
        'folder_path', help='Path to the folder containing the files')
    parser.add_argument('--descriptive_metadata', '-d', action='store_true',
                        help='Include this flag to include the descriptive metadata in the OPEX XML output')
    args = parser.parse_args()

    folder_path = args.folder_path
    descriptive_metadata = args.descriptive_metadata
    xml_filename = os.path.basename(folder_path)

    create_xml_file(folder_path, xml_filename, descriptive_metadata)


if __name__ == '__main__':
    main()
