#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A simple tool to produce a plain list of URLs from an XML sitemap, accepts
XML files or live sitemap URLs.
Includes basic filtering by 'contains strings' and 'exclude strings'. Outputs to .txt, .html or
terminal (default).
"""


import argparse
from pathlib import Path
from xml.etree import ElementTree

import requests


def main():
    parser = argparse.ArgumentParser(
        description='A simple tool to produce a plain list of URLs from an XML sitemap. Includes basic filtering by \'contains string\'. Outputs to .txt, .html or terminal (default).')
    # Requires at least one sitemap input (XML file or URL)
    parser.add_argument('sitemap_input', nargs='+',
                        help='sitemap input/s (XML file or URL)')
    # Optional filtering by 'contains string' argument, multiple arguments are treated as a Boolean OR search
    parser.add_argument('--contains_strings', nargs='+',
                        help='filter list output by \'contains string\', multiple arguments are treated as a Boolean OR search')
    # Optional filtering, exclude strings from output, multiple arguments are treated as a Boolean AND search
    parser.add_argument('--exclude_strings', nargs='+',
                        help='exclude strings from output, multiple arguments are treated as a Boolean AND search')
    # Optional save to .txt file
    parser.add_argument('--to_file', help='file path to .txt file output')
    # Optional save to .html file
    parser.add_argument('--to_html', help='file path to .html file output')
    args = parser.parse_args()

    # Get URLs into list
    sitemap_urls = get_sitemap_urls(args.sitemap_input)

    if args.contains_strings:
        sitemap_urls = filter_contains_str(sitemap_urls, args.contains_strings)

    if args.exclude_strings:
        sitemap_urls = filter_exclude_str(sitemap_urls, args.exclude_strings)

    if args.to_file or args.to_html:
        if args.to_file:
            to_file(sitemap_urls, args.to_file)
        if args.to_html:
            to_html(sitemap_urls, args.to_html)
    else:
        for i in sitemap_urls:
            print(i)


def to_html(sitemap_urls, filename):
    """Converts XML to a basic HTML where each URL is a hyperlink"""
    li_string = ''
    for url in sitemap_urls:
        li_string += f'<li><a href="{url}">{url}</a></li>\n'
    html = f'''<!DOCTYPE html>\n\
<html lang="en">\n\
<head>\n\
<meta charset="UTF-8">\n\
<meta name="viewport" content="width=device-width, initial-scale=1.0">\n\
<title></title>\n\
</head>\n\
<body>\n\
<ul>\n\
{li_string}\
</ul>\n\
</body>\n\
</html>'''
    with open(filename, 'w') as f:
        f.write(html)


def get_sitemap_urls(sitemap_urls):
    """Gets sitemap URLs from XML file or URL"""
    url_tree = []
    for sitemap in sitemap_urls:
        # Check if XML is local file
        if Path(sitemap).is_file():
            tree = ElementTree.parse(sitemap)
            root = tree.getroot()
            for i in range(len(root)):
                url_tree.append(root[i][0].text)
        # Else read XML from URL
        else:
            response = requests.get(sitemap)
            tree = ElementTree.fromstring(response.content)
            for i in range(len(tree)):
                url_tree.append(tree[i][0].text)
    return url_tree


def filter_contains_str(sitemap_urls, contains_string):
    # Uses set so each entry is unique
    filtered = set()
    for string in contains_string:
        for url in sitemap_urls:
            if string in url:
                filtered.add(url)
    # Sort the set after building set
    filtered = sorted(filtered)
    return filtered


def filter_exclude_str(sitemap_urls, exclude_string):
    """"Filter strings from sitemap based on exclude strings"""
    filtered = []
    for url in sitemap_urls:
        if not any(map(url.__contains__, exclude_string)):
            filtered.append(url)
    return filtered


def to_file(sitemap_urls, filename):
    """Write URL list to file"""
    with open(filename, 'w') as f:
        for i in sitemap_urls:
            if i == sitemap_urls[-1]:
                f.write(i)
            else:
                f.write(i+'\n')


if __name__ == '__main__':
    main()
