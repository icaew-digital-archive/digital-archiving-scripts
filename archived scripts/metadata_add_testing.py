#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script to add metadata to a Preservica asset via a string.
"""

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

OAI_DC = 'http://www.openarchives.org/OAI/2.0/oai_dc/'
DC = 'http://purl.org/dc/elements/1.1/'
XSI = 'http://www.w3.org/2001/XMLSchema-instance'
CUSTOM = 'http://icaew.com/icaew'

# Initialize the EntityAPI
entity = EntityAPI(username=USERNAME, password=PASSWORD, tenant=TENANT, server=SERVER)

# Define asset ID you want to update
assetID = '285f9e8a-19ee-4511-bcb3-583387dc62a2'

# Create XML metadata with Dublin Core and custom namespace
xml_object = ET.Element(
    'oai_dc:dc', {"xmlns:oai_dc": OAI_DC, "xmlns:dc": DC, "xmlns:xsi": XSI, "xmlns:icaew": CUSTOM})

xml.etree.ElementTree.register_namespace("icaew", CUSTOM)

# Add standard Dublin Core elements
ET.SubElement(xml_object, 'dc:title').text = 'Test Asset Title'
ET.SubElement(xml_object, 'dc:creator').text = 'John Doe'

# Add custom metadata element
ET.SubElement(xml_object, 'icaew:taxonomy').text = 'My custom field value'

# Remove any empty elements (optional)
root = etree.fromstring(ET.tostring(xml_object, encoding='utf-8').decode('utf-8'))
for element in root.xpath(".//*[not(node())]"):
    element.getparent().remove(element)
xml_request = etree.tostring(root, pretty_print=False).decode('utf-8')

# Print the XML for testing
print(xml_request)

# Try/except to add metadata to asset
try:
    asset = entity.asset(assetID)
    print(f"Adding metadata for assetID: {asset.reference}")
    entity.add_metadata(asset, OAI_DC, xml_request)
except Exception as e:
    print(f"Error adding metadata to asset: {e}")
