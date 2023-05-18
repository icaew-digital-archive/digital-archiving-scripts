#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Adds metadata to Preservica assets and folders using CSV file.
Once added, use update_metadata_from_csv.py to update.
"""

import csv
import os
import xml

from dotenv import load_dotenv
from pyPreservica import *

# Override is needed as the function will load local username instead of from the .env file
load_dotenv(override=True)

USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TENANT = os.getenv('TENANT')
SERVER = os.getenv('SERVER')

OAI_DC = 'http://www.openarchives.org/OAI/2.0/oai_dc/'
DC = 'http://purl.org/dc/elements/1.1/'
XSI = 'http://www.w3.org/2001/XMLSchema-instance'

CSV_INPUT_FILENAME = '/mnt/fc6d53c3-3dad-406c-a8ff-222b171f9208/work/code/pypreservica/dublincore-original.csv'

entity = EntityAPI(username=USERNAME,
                   password=PASSWORD, tenant=TENANT, server=SERVER)

headers = list()
with open(CSV_INPUT_FILENAME, encoding='utf-8-sig', newline='') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        for header in row:
            headers.append(header)
        break
    if 'assetId' in headers:
        for row in reader:
            assetID = None
            asset = None
            xml_object = xml.etree.ElementTree.Element(
                'oai_dc:dc', {"xmlns:oai_dc": OAI_DC, "xmlns:dc": DC, "xmlns:xsi": XSI})
            for value, header in zip(row, headers):
                if header.startswith('dc:'):
                    xml.etree.ElementTree.SubElement(
                        xml_object, header).text = value
                elif header.startswith('assetId'):
                    assetID = value
            xml_request = xml.etree.ElementTree.tostring(
                xml_object, encoding='utf-8', xml_declaration=True).decode('utf-8')
            # Try/except to add metadata to asset or folder
            try:
                asset = entity.asset(assetID)
                entity.add_metadata(asset, OAI_DC, xml_request)
            except:
                pass
            try:
                asset = entity.folder(assetID)
                entity.add_metadata(asset, OAI_DC, xml_request)
            except:
                pass
    else:
        print("The CSV file should contain a assetId column containing the Preservica identifier for the asset to be updated")
