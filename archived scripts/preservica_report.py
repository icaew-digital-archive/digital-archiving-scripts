#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This script outputs information regarding Preservica assets below a specified folder reference to a CSV file.
The CSV file contains the following fields: Folder/Asset path, entity.title, entity.reference, entity.entity_type, entity.security_tag, Dublin Core Metadata (Title).
"""

import csv
import os
import xml.etree.ElementTree as ET
import logging

# Configure logging to write to a file with a basic format, set the log level to ERROR
logging.basicConfig(filename='error_log.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')


from dotenv import load_dotenv
from pyPreservica import *

# Override is needed as the function will load local username instead of from the .env file
load_dotenv(override=True)

USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TENANT = os.getenv('TENANT')
SERVER = os.getenv('SERVER')

client = EntityAPI(username=USERNAME,
                   password=PASSWORD, tenant=TENANT, server=SERVER)

CSV_OUTPUT_FILENAME = '20240206-report.csv'
# PARENT_FOLDER_REF: None for root, or a specific folder reference number such as - 'a9c9fa31-4842-4ff3-9dad-d0ae2fbe6c28'
PARENT_FOLDER_REF = None


def main():

    with open(CSV_OUTPUT_FILENAME, 'w', encoding='UTF8', newline='') as f:
        writer = csv.writer(f, delimiter=',', quotechar='"',
                            quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Folder/Asset path', 'entity.title', 'entity.reference',
                        'entity.entity_type', 'entity.security_tag', 'Dublin Core Metadata (Title)'])

        # Filter can be applied via: for asset in filter(only_assets, client.all_descendants()):
        for entity in client.all_descendants(PARENT_FOLDER_REF):

            try:

                # Create directory path to root
                if entity.parent != None:  # Gets around calling entity.parent etc. on root implied root reference in all_descendants()
                    folderpath = []
                    folder = client.folder(entity.parent)
                    folderpath.insert(0, folder.title + '/')
                    while folder.parent != None:
                        folder = client.folder(folder.parent)
                        folderpath.insert(0, folder.title + '/')
                    folder_and_assetpath = ''.join(folderpath) + entity.title
                else:
                    folder_and_assetpath = entity.title
                print(folder_and_assetpath + '\n')

                # Folder logic
                if str(entity.entity_type) == 'EntityType.FOLDER':
                    asset = client.folder(entity.reference)
                    security_tag = asset.security_tag
                    for metadata in client.all_metadata(asset):
                        schema = metadata[0]
                        if schema == 'http://www.openarchives.org/OAI/2.0/oai_dc/':
                            xml_string = metadata[1]
                            root = ET.fromstring(xml_string)
                            title_metadata = root[0].text
                        else:
                            title_metadata = ''

                # Asset logic
                if str(entity.entity_type) == 'EntityType.ASSET':
                    asset = client.asset(entity.reference)
                    security_tag = asset.security_tag
                    for metadata in client.all_metadata(asset):
                        schema = metadata[0]
                        if schema == 'http://www.openarchives.org/OAI/2.0/oai_dc/':
                            xml_string = metadata[1]
                            root = ET.fromstring(xml_string)
                            title_metadata = root[0].text
                            print(root[0].text)
                            print(root[1].text)
                            print(root[2].text)
                            print(root[3].text)
                            print(root[4].text)
                            print(root[5].text)
                            print(root[6].text)
                            print(root[7].text)
                            print(root[8].text)
                        else:
                            title_metadata = ''

                writer.writerow([folder_and_assetpath, entity.title, entity.reference, entity.entity_type, security_tag, title_metadata])
            
            except Exception as e:
                # Log the exception
                logging.error("An error occurred: %s", e)


if __name__ == "__main__":
    main()
