#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Adds metadata to Preservica assets and folders using a CSV file.

The script requires the CSV file to contain an assetId column containing Preservica asset references and columns prefixed with 'dc:' (i.e. 'dc:title').

usage: c_add_metadata_from_csv.py [-h] --csv_file
"""

import argparse
import csv
import os
import xml.etree.ElementTree as ET

from dotenv import load_dotenv
from lxml import etree
from pyPreservica import *

# Override is needed as the function will load local username instead of from the .env file
load_dotenv(override=True)

# Retrieve environment variables
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TENANT = os.getenv('TENANT')
SERVER = os.getenv('SERVER')

# Define command-line arguments
parser = argparse.ArgumentParser(
    description='Add metadata to Preservica assets and folders using a CSV file.')
parser.add_argument('--csv_file', required=True,
                    help='Path to the CSV input file')

# Parse command-line arguments
args = parser.parse_args()

OAI_DC = 'http://www.openarchives.org/OAI/2.0/oai_dc/'
DC = 'http://purl.org/dc/elements/1.1/'
XSI = 'http://www.w3.org/2001/XMLSchema-instance'
ICAEW = 'https://www.icaew.com/metadata/'

entity = EntityAPI(username=USERNAME,
                   password=PASSWORD, tenant=TENANT, server=SERVER)

headers = list()
with open(args.csv_file, encoding='utf-8-sig', newline='') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        for header in row:
            headers.append(header)
        break
    if 'assetId' in headers:
        for row in reader:
            assetID = None
            asset = None
            # --- OAI_DC XML ---
            xml_object = ET.Element(
                'oai_dc:dc', {"xmlns:oai_dc": OAI_DC, "xmlns:dc": DC, "xmlns:xsi": XSI})
            # --- ICAEW XML ---
            icaew_object = ET.Element(
                'icaew:ICAEW', {"xmlns:icaew": ICAEW, "xmlns": "http://preservica.com/XIP/v7.6"})
            has_dc = False
            has_icaew = False
            for value, header in zip(row, headers):
                if header.startswith('dc:'):
                    if value:
                        ET.SubElement(
                            xml_object, header).text = value
                        has_dc = True
                elif header.startswith('icaew:'):
                    if value:
                        ET.SubElement(
                            icaew_object, header).text = value
                        has_icaew = True
                elif header.startswith('assetId'):
                    assetID = value

            # Remove empty elements from both XMLs
            root_dc = etree.fromstring(ET.tostring(
                xml_object, encoding='utf-8').decode('utf-8'))
            for element in root_dc.xpath(".//*[not(node())]"):
                element.getparent().remove(element)
            xml_request_dc = etree.tostring(
                root_dc, pretty_print=False).decode('utf-8')

            root_icaew = etree.fromstring(ET.tostring(
                icaew_object, encoding='utf-8').decode('utf-8'))
            for element in root_icaew.xpath(".//*[not(node())]"):
                element.getparent().remove(element)
            xml_request_icaew = etree.tostring(
                root_icaew, pretty_print=False).decode('utf-8')

            # Try/except to add metadata to asset or folder
            for schema_uri, xml_request, present in [
                (OAI_DC, xml_request_dc, has_dc),
                (ICAEW, xml_request_icaew, has_icaew)
            ]:
                if not present:
                    continue
                try:
                    asset = entity.asset(assetID)
                    print(f"Adding {schema_uri} metadata for assetID: {asset.reference}")
                    entity.add_metadata(asset, schema_uri, xml_request)
                except:
                    pass
                try:
                    asset = entity.folder(assetID)
                    print(f"Adding {schema_uri} metadata for assetID: {asset.reference}")
                    entity.add_metadata(asset, schema_uri, xml_request)
                except:
                    pass
    else:
        print("The CSV file should contain an assetId column containing the Preservica identifier for the asset to be updated")
