#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A tool that opens multiple URLs in a browser from a list of URLs supplied
via .txt file.

Built to be used in conjunction with Python Wayback (PyWb) in record mode. This tool will open
URLs up in the form of localhost:{PORT}/{COLLECTION}/record/{URL}.
"""

import argparse
import sys
import time
import webbrowser


def main():
    parser = argparse.ArgumentParser(
        description='A tool that opens multiple URLs in a browser from a list of URLs supplied via .txt file. Built to be used in conjunction with Python Wayback (PyWb) in record mode.')
    # Requires a list of URLs
    parser.add_argument('url_list', help='.txt file containing list of URLs')
    # Requires browser selection
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--chrome', action='store_true',
                       help='mutually exclusive argument, either --chrome or--firefox flags must be provided')
    group.add_argument('--firefox', action='store_true',
                       help='mutually exclusive argument, either --chrome or--firefox flags must be provided')
    # Optional argument to give start point of URLs to open
    parser.add_argument('--file_start', type=int,
                        help='start point of .txt file to read')
    # Optional argument to give end point of URLs to open
    parser.add_argument('--file_end', type=int,
                        help='end point of .txt file to read')
    # Optional argument, to enable pywb functions, if enabled the collection and port arguments are needed. Builds URLs in the form of localhost:{PORT}/{COLLECTION}/record/{URL}
    parser.add_argument('--pywb', action='store_true',
                        help='this flag enables \'pywb record mode\' and builds/opens URLs in the form of localhost:{PORT}/{COLLECTION}/record/{URL}')
    # Only required if --pywb is given
    parser.add_argument(
        '--collection', required='--pywb' in sys.argv, help='required flag when \'pywb record mode\' is enabled')
    # Only required if --pywb is given
    parser.add_argument('--port', required='--pywb' in sys.argv,
                        help='required flag when \'pywb record mode\' is enabled')
    args = parser.parse_args()

    # Read .txt file, output to list
    url_list = read_file(args.url_list)

    # Where to read from and to; default is entire list
    if args.file_start:
        START = args.file_start
    else:
        START = 0
    if args.file_end:
        END = args.file_end
    else:
        END = len(url_list)
    # Change list depending on given START:END parameters
    url_list = url_list[START:END]

    # Select browser
    if args.chrome:
        BROWSER = 'google-chrome'
    if args.firefox:
        BROWSER = 'firefox'

    # Set vars to build pywb URL
    if args.pywb:
        COLLECTION = args.collection
        PORT = args.port

    print(len(url_list), 'URLs read from .txt file')
    print('Start point:', START, '\nEnd point:', END)
    time.sleep(5)

    # Loop through list, opening URLs in browser
    for url in url_list[START:END]:
        # If args.pywb, build pywb URL for recording, else open URL without modifying URL
        if args.pywb:
            print(
                f'Opening: http://localhost:{PORT}/{COLLECTION}/record/{url}')
            webbrowser.get(BROWSER).open(
                f'http://localhost:{PORT}/{COLLECTION}/record/{url}')
        else:
            print(f'Opening: {url}')
            webbrowser.get(BROWSER).open(url)


def read_file(url_list):
    """Load the .txt file and return list"""
    with open(url_list, 'r') as f:
        lines_file = [line.strip() for line in f]
    return lines_file


if __name__ == '__main__':
    main()
