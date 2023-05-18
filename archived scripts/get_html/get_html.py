#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A tool which visits pages from a list of URLs and saves the HTML content to
a Python dictionary.

This dictionary of {URL:HTML content} can later be used to inspect/scrape HTML 
elements.

Outputs to json, pickle or terminal (default).
"""

import argparse
import getpass
import json
import pickle

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


def main():
    parser = argparse.ArgumentParser(
        description='A tool which visits a list of URLs and saves the HTML content to a Python dictionary. Outputs to json, pickle or terminal (default).')
    # Requires at least one list of URLs
    parser.add_argument(
        'url_list', help='.txt file containing list of URLs to visit')
    # Optional argument to give option to provide authentication credentials
    parser.add_argument('--authenticate', action='store_true',
                        help='gives option to provide authentication credentials')
    # Optional argument to give start point of URLs to visit
    parser.add_argument('--file_start', type=int,
                        help='start point of .txt file to read')
    # Optional argument to give end point of URLs to visit
    parser.add_argument('--file_end', type=int,
                        help='end point of .txt file to read')
    # Optional save dict to json file
    parser.add_argument('--to_json', help='file path to .json file output')
    # Optional save dict to pickle file
    parser.add_argument('--to_pickle', help='file path to .pkl file output')
    args = parser.parse_args()

    # Read file into list
    url_list = read_file(args.url_list)

    # Where to read from and to; default is entire list
    if args.file_start:
        start = args.file_start
    else:
        start = 0
    if args.file_end:
        end = args.file_end
    else:
        end = len(url_list)
    # Change list depending on given start:end parameters
    url_list = url_list[start:end]

    # Logged in session
    if args.authenticate:
        username = input('Username: ')
        password = getpass.getpass('Password: ')
        session_login_page = input('Session login page: ')
        # Add credentials to payload
        payload = {'Username': username,
                   'Password': password, }
        # Return dict from logged in session
        dict_page_html = session(url_list, session_login_page, payload)
    # Regular session
    else:
        # Return dict from regular session
        dict_page_html = scrape_loop(url_list)

    # Determine output, json, pickle, or terminal output
    if args.to_json or args.to_pickle:
        if args.to_json:
            with open(args.to_json, 'w') as f:
                json.dump(dict_page_html, f)
        if args.to_pickle:
            with open(args.to_pickle, 'wb') as f:
                pickle.dump(dict_page_html, f)
    else:
        # Print dictionary
        for k, v in dict_page_html.items():
            print('URL: ' + k, '\nHTML content:\n\n' + v.strip() + '\n')


def read_file(url_list):
    """Load the .txt file and return list"""
    with open(url_list, 'r') as f:
        lines_file = [line.strip() for line in f]
    return lines_file


def session(url_list, session_login_page, payload):
    """Submit credentials to login"""
    # Set headers / emulate a real browser
    with requests.Session() as sess:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) \
                AppleWebKit/537.36 (KHTML, like Gecko) \
                    Chrome/50.0.2661.102 Safari/537.36'}
        res = sess.get(session_login_page, headers=headers)
        # Get validation token by parsing HTML
        signin = BeautifulSoup(res.text, 'html.parser')
        tok = signin.find_all('input')
        # Add token to payload
        payload['__RequestVerificationToken'] = tok[-1]["value"]
        # Submit login details to login page
        res = sess.post(session_login_page, data=payload, headers=headers)
        # Run main scrape loop in the logged in session
        dict_page_html = scrape_loop(url_list, sess=sess)
        return dict_page_html


def scrape_loop(url_list, sess=False):
    """Main loop for looping through URLs in list. Building dictionary of
    pages (key) and HTML content (values)"""
    dict_page_html = {}
    for i in tqdm(url_list):
        try:
            if sess == False:
                page = requests.get(i)
            else:
                page = sess.get(i)
            # Update dictionary with new key:value pairs
            dict_page_html.update({i: page.text})
        except Exception as e:
            print(e)
    return dict_page_html


if __name__ == '__main__':
    main()
