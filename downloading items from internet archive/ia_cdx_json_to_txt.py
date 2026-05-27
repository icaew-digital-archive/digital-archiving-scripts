#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Convert CDX Internet Archive API JSON output to wget-compatible Wayback Machine URLs.

Handles duplicate removal based on digest hashes (more reliable than the CDX API's
own collapse option). Output is a plain text file of URLs, one per line.

Fetch the CDX JSON with wget first, e.g.:
  wget 'http://web.archive.org/cdx/search/cdx?url=example.com&matchType=domain&output=json' -O cdx.json

Then run this script:
  python ia_cdx_json_to_txt.py cdx.json

Download the resulting URLs with wget:
  wget -i cdx.txt                              # media / binary files
  wget --mirror --convert-links -nH -i cdx.txt  # full site mirror

CDX API docs: https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
Display flags: https://en.wikipedia.org/wiki/Help:Using_the_Wayback_Machine#Specific_archive_copy
"""

import argparse
import json
import sys


def convert(json_file, output_file, display_flag, dedup):
    with open(json_file) as f:
        records = json.load(f)

    seen_digests = set()
    urls = []

    for record in records[1:]:  # skip the header row
        timestamp, original, digest = record[1], record[2], record[5]
        url = f"https://web.archive.org/web/{timestamp}{display_flag}/{original}"

        if dedup:
            if digest in seen_digests:
                continue
            seen_digests.add(digest)

        urls.append(url)
        print(url)

    with open(output_file, "w") as f:
        f.write("\n".join(urls))

    print(f"\n{len(urls)} URLs written to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert CDX Internet Archive API JSON to wget-compatible Wayback Machine URLs.",
        epilog="Example: python ia_cdx_json_to_txt.py cdx.json --output cdx.txt",
    )
    parser.add_argument("json_file", help="CDX JSON file from the Internet Archive API")
    parser.add_argument(
        "--output",
        default="cdx.txt",
        metavar="OUTPUT_FILE",
        help="Output text file of URLs (default: cdx.txt)",
    )
    parser.add_argument(
        "--display-flag",
        default="if_",
        metavar="FLAG",
        help="Wayback Machine display flag appended to timestamps (default: if_)",
    )
    parser.add_argument(
        "--no-dedup",
        action="store_false",
        dest="dedup",
        help="Include duplicate digest hashes (default: deduplicate)",
    )
    args = parser.parse_args()
    convert(args.json_file, args.output, args.display_flag, args.dedup)
