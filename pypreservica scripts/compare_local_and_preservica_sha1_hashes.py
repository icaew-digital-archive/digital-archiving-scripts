#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ipsum
"""

preservica_checksum_list = '/home/digital-archivist/Documents/custom scripts/web-archiving-scripts/vital-mag-checksums.txt'

# find . -type f -exec sha1sum {} + > checksums.txt

local_checksum_list = '/home/digital-archivist/Documents/custom scripts/web-archiving-scripts/checksums.txt'


def read_first_40_char_lines_to_list(file_path):
    with open(file_path, 'r') as file:
        file_contents = file.readlines()
        file_contents = [line.strip()[:40] for line in file_contents]
    return file_contents


preservica_checksums_only = read_first_40_char_lines_to_list(
    preservica_checksum_list)

local_checksums_only = read_first_40_char_lines_to_list(local_checksum_list)

for local_checksum in local_checksums_only:
    if local_checksum not in preservica_checksums_only:
        print(f'Not found in Preservica: {local_checksum}')
