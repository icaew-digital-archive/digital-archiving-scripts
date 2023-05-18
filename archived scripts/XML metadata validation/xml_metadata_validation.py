#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A tool to quickly find malformed XML .metadata files. Built to test .metadata
files prior to ingest into Preservica.
"""

import os

import xmlschema

print('XML .metadata file validation')
my_schema = input('Enter path to xsd file: ')
my_schema = my_schema.strip().strip("'")
my_schema = xmlschema.XMLSchema(my_schema)

directory = input('Enter path to directory containing .metadata files: ')
directory = directory.strip().strip("'")

# Walk path recursively and test XML .metadata files
for r, d, f in os.walk(directory):
    for file in f:
        if file.endswith(".metadata"):
            try:
                if my_schema.is_valid(os.path.join(r, file)):
                    print(f'OK - {os.path.join(r, file)}')
            except Exception as e:
                print(f'NOT VALID - {os.path.join(r, file)} - {e}')
input()
