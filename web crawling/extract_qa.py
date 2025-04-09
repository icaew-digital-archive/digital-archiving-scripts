#!/usr/bin/env python3
"""
Extract Quality Assurance (QA) data from WACZ web archive files.

This script processes WACZ (Web Archive Collection Zipped) files to extract and analyze
QA comparison data stored in the archive's WARC files. It specifically looks for QA
information in "info" WARC files and converts it into a structured CSV format.

The script extracts various metrics for each archived page, including:
- URL of the archived page
- Screenshot match status
- Text match status
- Resource counts (crawl and replay)
- Status information
- Timestamp
- Source file information

Usage:
    python extract_qa.py input.wacz [output.csv]

Arguments:
    input.wacz    Path to the input WACZ file
    output.csv    Optional path for the output CSV file (defaults to input filename with .csv extension)

Example:
    python extract_qa.py archive.wacz
    python extract_qa.py archive.wacz results.csv

Exit Codes:
    0 - Success
    1 - Input file not found
    2 - Invalid WACZ structure (missing archive folder)
    3 - No info WARC files found
"""

import os
import gzip
import json
import tempfile
import pandas as pd
from zipfile import ZipFile
from warcio.archiveiterator import ArchiveIterator
import argparse


def log(message: str, icon: str = ""):
    print(f"{icon + ' ' if icon else ''}{message}")


def extract_qa(input_file: str, output_file: str = None):
    """Extract QA JSON records from info WARC files inside a WACZ archive."""
    if not os.path.exists(input_file):
        log(f"File not found: {input_file}", "❌")
        return 1

    if output_file is None:
        output_file = os.path.splitext(input_file)[0] + ".csv"

    log(f"Unzipping WACZ: {input_file}", "📦")

    with tempfile.TemporaryDirectory() as temp_dir:
        with ZipFile(input_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        archive_path = os.path.join(temp_dir, "archive")
        if not os.path.isdir(archive_path):
            log("No 'archive/' folder found in WACZ.", "❌")
            return 2

        log(f"Found archive folder: {archive_path}", "📁")

        data = []
        warc_files = [f for f in os.listdir(archive_path) if f.startswith(
            "info") and f.endswith(".warc.gz")]

        if not warc_files:
            log("No info-*.warc.gz files found.", "⚠️")
            return 3

        log(f"Processing {len(warc_files)} WARC file(s)...", "🔍")

        for fname in warc_files:
            full_path = os.path.join(archive_path, fname)
            log(f"Processing {fname}", "📖")

            try:
                with gzip.open(full_path, "rb") as stream:
                    for record in ArchiveIterator(stream):
                        if (
                            record.rec_type == "resource" and
                            record.content_type == "application/json"
                        ):
                            uri = record.rec_headers.get_header(
                                "WARC-Target-URI")
                            if not uri or not uri.startswith("urn:pageinfo:"):
                                continue

                            try:
                                payload = record.content_stream().read()
                                json_data = json.loads(payload.decode("utf-8"))

                                comparison = json_data.get("comparison", {})
                                rc = comparison.get("resourceCounts", {})

                                data.append({
                                    "url": json_data.get("url"),
                                    "screenshot_match": comparison.get("screenshotMatch"),
                                    "text_match": comparison.get("textMatch"),
                                    "crawl_good": rc.get("crawlGood"),
                                    "crawl_bad": rc.get("crawlBad"),
                                    "replay_good": rc.get("replayGood"),
                                    "replay_bad": rc.get("replayBad"),
                                    "status": json_data.get("status"),
                                    "timestamp": record.rec_headers.get_header("WARC-Date"),
                                    "source_file": fname
                                })

                            except Exception as e:
                                log(
                                    f"⚠️ Failed to parse JSON in {fname}: {e}")
            except Exception as e:
                log(f"❌ Could not read {fname}: {e}")

        if not data:
            log("No QA data found in WACZ.", "⚠️")
        else:
            df = pd.DataFrame(data).sort_values("url")
            df.to_csv(output_file, index=False)
            log(f"Extracted {len(df)} QA records.", "✅")
            log(f"Saved to {output_file}", "📁")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Extract QA comparison data from a WACZ file into a CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python extract_qa.py archive.wacz
    python extract_qa.py archive.wacz results.csv
        """
    )

    parser.add_argument(
        "input",
        help="Path to the input WACZ file"
    )
    parser.add_argument(
        "output",
        nargs="?",
        help="Optional path to output CSV file"
    )

    args = parser.parse_args()
    return extract_qa(args.input, args.output)


if __name__ == "__main__":
    exit(main())
