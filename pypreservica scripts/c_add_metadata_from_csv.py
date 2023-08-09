#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Adds metadata to Preservica assets and folders using a CSV file.

The script requires the CSV file to contain an assetId column containing Preservica asset references and columns prefixed with 'dc:' (i.e. 'dc:title').

usage: c_add_metadata_from_csv.py [-h] csv_file
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
parser.add_argument('csv_file', help='Path to the CSV input file')

# Parse command-line arguments
args = parser.parse_args()

OAI_DC = 'http://www.openarchives.org/OAI/2.0/oai_dc/'
DC = 'http://purl.org/dc/elements/1.1/'
XSI = 'http://www.w3.org/2001/XMLSchema-instance'

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
            xml_object = ET.Element(
                'oai_dc:dc', {"xmlns:oai_dc": OAI_DC, "xmlns:dc": DC, "xmlns:xsi": XSI})
            for value, header in zip(row, headers):
                if header.startswith('dc:'):
                    ET.SubElement(
                        xml_object, header).text = value
                elif header.startswith('assetId'):
                    assetID = value

            # The following removes empty elements from the XML - to remove empty repeated elements from csv file
            root = etree.fromstring(ET.tostring(
                xml_object, encoding='utf-8').decode('utf-8'))
            for element in root.xpath(".//*[not(node())]"):
                element.getparent().remove(element)
            xml_request = etree.tostring(
                root, pretty_print=False).decode('utf-8')

            # The following does not remove empty elements from the XML
            # xml_request = ET.tostring(
            #     xml_object, encoding='utf-8', xml_declaration=True).decode('utf-8')
            # print(xml_request)

            # Try/except to add metadata to asset or folder
            try:
                asset = entity.asset(assetID)
                print(f"Adding metadata for assetID: {asset.reference}")
                entity.add_metadata(asset, OAI_DC, xml_request)
            except:
                pass
            try:
                asset = entity.folder(assetID)
                print(f"Adding metadata for assetID: {asset.reference}")
                entity.add_metadata(asset, OAI_DC, xml_request)
            except:
                pass
    else:
        print("The CSV file should contain an assetId column containing the Preservica identifier for the asset to be updated")
