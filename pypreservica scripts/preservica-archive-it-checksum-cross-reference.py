#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Compares to lists of checksums. Script for use with the MD5 manifest .txt files produced by py-wasapi-client (Archive-It downloader) 
and the output of get_asset_checksum_values.py.

Stdout to a .txt file via preservice-archive-it-checksum-cross-reference.py > files-not-present-in-preservica.txt

Use the following bash script to download the missing WARC files:

#!/bin/bash

# Path to the text file to loop through
file_path="/home/digital-archivist/Documents/apps/py-wasapi-client/files-not-present-in-preservica.txt"

# Loop through each line in the file
while read line; do

  # Extract the substring from the line (using sed command)
  sub_string=$(echo "$line" | sed 's/.*\(substring\).*/\1/')

  # Use the substring in a shell command (replace with your own command)
  echo "Downloading $sub_string"
  wasapi-client --profile icaew --filename $sub_string
  # Replace the above echo statement with your own shell command that uses the sub_string

done < "$file_path"

"""


def read_file(checksum_list):
    """Load the .txt file and return list"""
    with open(checksum_list, 'r') as f:
        lines_file = [line.strip() for line in f]
    return lines_file


def main():

    PRESERVICA_CHECKSUM_FILE = '/home/digital-archivist/Documents/custom scripts/web-archiving-scripts/test_files/files-not-present-in-preservica.txt'
    ARCHIVE_IT_CHECKSUM_FILE = '/home/digital-archivist/Documents/custom scripts/web-archiving-scripts/test_files/manifest-md5.txt'

    preservica_checksums = [x[:32].lower()
                            for x in read_file(PRESERVICA_CHECKSUM_FILE)]
    archive_it_checksums = [x[:32].lower()
                            for x in read_file(ARCHIVE_IT_CHECKSUM_FILE)]

    # Determine missing checksums from Preservica
    missing_from_preservica = []
    for archive_it_checksum in archive_it_checksums:
        if archive_it_checksum not in preservica_checksums:
            missing_from_preservica.append(archive_it_checksum)

    archive_it_raw_output = read_file(ARCHIVE_IT_CHECKSUM_FILE)

    # Get filenames for missing from Preservica
    for line in archive_it_raw_output:
        for missing in missing_from_preservica:
            if missing in line:
                print(line[34:])


if __name__ == '__main__':
    main()
