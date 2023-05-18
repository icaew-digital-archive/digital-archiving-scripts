#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This script produces wget requestable URLs from the json file output from the CDX Internet Archive API. It also allows for better duplicate removal based on digests compared with the standard API filter/collapse option.
For example it will convert this json object into a Wayback Machine URL: 
["com,spacejam)/", "19961227161755", "http://spacejam.com:80/", "text/html", "200", "A6NF77CKEPAV6LT6P4P7UBUGA5DHCC54", "495"]
to
https://web.archive.org/web/19961227161755if_/http://spacejam.com:80/

The CDX Internet Archive API is explained here: https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
wget documentation is here: https://www.gnu.org/software/wget/manual/wget.html

An example wget request from the CDX Internet Archive API that creates a json file: wget 'http://web.archive.org/cdx/search/cdx?url=spacejam.com&matchType=domain&output=json' -O cdx.json
Additional filters can be applied to the CDX API request if needed. An example filter by mimeType (media files only, PDFs, DOCs etc.): http://web.archive.org/cdx/search/cdx?url=spacejam.com&output=json&matchType=domain&filter=mimetype:application.*

Downloading material from the Internet Archive Wayback Machine can be performed using these example commands:
wget -i <txt file output from this script> [better suited for media file downloads]
OR
wget --mirror --convert-links --adjust-extension --page-requisites --no-parent --restrict-file-names=windows -nH -i <txt file output from this script> [better suited to the download of webpages]
"""

import json

JSON_FILE_INPUT = "cdx.json"
TXT_FILE_OUTPUT = "cdx.txt"
display_flag = "if_"  # The use of display flags is explained here - https://en.wikipedia.org/wiki/Help:Using_the_Wayback_Machine#Specific_archive_copy
filter_duplicate_digests = True  # If set to true, only URLs with unique digest hashes are added to the web_archive_urls list
seen_digest = []
web_archive_urls = []

with open(JSON_FILE_INPUT) as jsonFile:
    jsonObject = json.load(jsonFile)
    jsonFile.close()

for i in range(len(jsonObject))[1:]:  # The '[1:]' skips the header of the jsonObject

    web_archive_url = f"https://web.archive.org/web/{jsonObject[i][1]}{display_flag}/{jsonObject[i][2]}"

    if filter_duplicate_digests:
        if jsonObject[i][5] not in seen_digest:
            seen_digest.append(jsonObject[i][5])
            web_archive_urls.append(web_archive_url)
            print(web_archive_url)
    else:
        web_archive_urls.append(web_archive_url)

print(f"Number of web archive URLs: {len(web_archive_urls)}")

with open(TXT_FILE_OUTPUT, "w") as f:
    for web_archive_url in web_archive_urls:
        if web_archive_url == web_archive_urls[len(web_archive_urls) - 1]:
            f.write(f"{web_archive_url}")
        else:
            f.write(f"{web_archive_url}\n")
