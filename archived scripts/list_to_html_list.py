#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
List from .txt file to HTML unordered list of links.
"""


def main():
    urls = read_file('test_files/templates.txt')
    to_html(urls, 'test_files/template_html_table.html')


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


def read_file(url_list):
    """Load the .txt file and return list"""
    with open(url_list, 'r') as f:
        lines_file = [line.strip() for line in f]
    return lines_file


if __name__ == '__main__':
    main()
