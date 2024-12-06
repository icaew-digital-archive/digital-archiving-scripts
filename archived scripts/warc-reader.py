#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A script which reads a folder of WARC files and cross-references the content with a list of URLs.
It also uses BS4 to search the HTML content for specific HTML elements.
"""

import csv
import os
from pathlib import Path

from bs4 import BeautifulSoup
from tqdm import tqdm
from warcio.archiveiterator import ArchiveIterator

# URL_LIST is most likely going to be a sitemap 'snapshot'
URL_LIST = ''
# WARC_FOLDER_PATH is a path to a folder containing WARC files
WARC_FOLDER_PATH = ''
# CSV_FILENAME is the filename for the CSV output
CSV_FILENAME = ''


def read_file(url_list):
    """Load the .txt file and return list"""
    with open(url_list, 'r') as f:
        lines_file = [line.strip() for line in f]
    return lines_file


def get_warc_paths(warc_path):
    """Get WARC file paths from file/directory path, filtering out non-WARC files"""
    warc_paths = []
    if os.path.isfile(warc_path):
        if Path(warc_path).match('*warc*'):
            warc_paths.append(warc_path)
    elif os.path.isdir(warc_path):
        warc_files = os.listdir(warc_path)
        for filename in warc_files:
            warc_path_tmp = os.path.join(warc_path, filename)
            if not Path(warc_path_tmp).match('*warc*'):
                continue
            warc_paths.append(warc_path_tmp)
    return warc_paths


def element_test(soup, tag, attr_type, attr_val):
    """Return True or False if HTML contains element as defined in soup.findAll"""
    out = soup.findAll(tag, attrs={attr_type: attr_val})
    return bool(out)


def main():
    urls = read_file(URL_LIST)
    warc_paths = get_warc_paths(WARC_FOLDER_PATH)

    # Create a list of dictionaries for each URL
    cross_ref_list = []
    for url in urls:
        cross_ref_list.append({'url': url, 'title': None, 'present-in-WARC': False,
                              'datetime-crawled': None, 'icon__user--active': None, 'more-link': None, 'c-navigation-pagination': None, 'tab-placeholder': None, 'c-filter--dynamic': None})

    # Loop though WARC file/s
    for warc in tqdm(warc_paths):
        with open(warc, 'rb') as stream:
            for record in ArchiveIterator(stream):
                # Filter out requests
                if record.rec_type == 'response':
                    # Get URI from record
                    record_uri = record.rec_headers.get_header(
                        'WARC-Target-URI')
                    record_date = record.rec_headers.get_header('WARC-Date')

                    # Loop through the cross_ref_list to see if the warc_uri matches a cross_ref_item's URL
                    for cross_ref_item in cross_ref_list:
                        if cross_ref_item['url'] == record_uri:
                            cross_ref_item['present-in-WARC'] = True
                            cross_ref_item['datetime-crawled'] = record_date

                            # Read the HTML content to find elements
                            # Decode bytes to utf-8 string and strip whitespace
                            html = record.content_stream().read().decode('utf-8').strip()
                            soup = BeautifulSoup(html, 'html.parser')

                            # Get title
                            if soup.title is not None:
                                cross_ref_item['title'] = soup.title.string

                            # HTML element tests
                            # Tests for 'icon__user--active'
                            if element_test(soup, tag='span', attr_type='class', attr_val='icon__user--active'):
                                cross_ref_item['icon__user--active'] = True
                            else:
                                cross_ref_item['icon__user--active'] = False

                            # Tests for 'more-link'
                            if element_test(soup, tag='div', attr_type='class', attr_val='more-link'):
                                cross_ref_item['more-link'] = True
                            else:
                                cross_ref_item['more-link'] = False

                            # Tests for - 'c-navigation-pagination'
                            if element_test(soup, tag='div', attr_type='class', attr_val='c-navigation-pagination'):
                                cross_ref_item['c-navigation-pagination'] = True
                            else:
                                cross_ref_item['c-navigation-pagination'] = False

                            # Tests for - 'tab-placeholder'
                            if element_test(soup, tag='div', attr_type='class', attr_val='tab-placeholder'):
                                cross_ref_item['tab-placeholder'] = True
                            else:
                                cross_ref_item['tab-placeholder'] = False

                            # Tests for - 'c-filter--dynamic'
                            if element_test(soup, tag='div', attr_type='class', attr_val='c-filter--dynamic'):
                                cross_ref_item['c-filter--dynamic'] = True
                            else:
                                cross_ref_item['c-filter--dynamic'] = False

    # Write to CSV
    with open(CSV_FILENAME, 'w') as f:
        # Create the csv writer
        writer = csv.writer(f)
        # Write header
        writer.writerow(['url', 'title', 'present-in-WARC', 'datetime-crawled', 'icon__user--active',
                         'more-link', 'c-navigation-pagination', 'tab-placeholder', 'c-filter--dynamic'])
        # Write rows
        for dictionary in cross_ref_list:
            writer.writerow(dictionary.values())


if __name__ == '__main__':
    main()
