#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Uses Semaphore's CLSClient to auto-classify documents and sorts by topic score.

The script can upload to Semaphore from a specified directory (argument: "directory").
The script can also download from Preservica first using a Preservica folder reference with the optional "--preservica_ref" flag.

usage: semaphore-helper.py [-h] [--preservica_ref PRESERVICA_REF] directory
"""

import argparse
import subprocess
import re
import os
from dotenv import load_dotenv

MAX_TOPICS = 10
SEMAPHORE_THRESHOLD = '48'
INCLUDE_SCORING = False

# Load configuration from environment variables
load_dotenv(override=True)
SEMAPHORE_JAVA_CLIENT = os.getenv('SEMAPHORE_JAVA_CLIENT')
SEMAPHORE_CLOUD_API_KEY = os.getenv('SEMAPHORE_CLOUD_API_KEY')
SEMAPHORE_URL = os.getenv('SEMAPHORE_URL')
PYPRESERVICA_DOWNLOAD_SCRIPT = os.getenv('PYPRESERVICA_DOWNLOAD_SCRIPT')


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Process files with Semaphore\'s CLSClient')
    parser.add_argument('--preservica_ref',
                        help='Preservica reference', default=None)
    parser.add_argument('directory', help='Directory path')
    return parser.parse_args()


def download_files(preservica_ref, directory):
    print(f"Preservica reference: {preservica_ref}")

    download_command = [
        'python3', PYPRESERVICA_DOWNLOAD_SCRIPT, '--preservica_folder_ref', preservica_ref, directory]
    result = subprocess.run(
        download_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode == 0:
        print(f"Files downloaded successfully to {directory}")
    else:
        print(f"Download failed. Error message:\n{result.stderr}")
        exit()


def process_file(file_path):
    print(file_path)

    semantic_command = f'java -jar "{SEMAPHORE_JAVA_CLIENT}" --cloud-api-key={SEMAPHORE_CLOUD_API_KEY} --url={SEMAPHORE_URL} --threshold={SEMAPHORE_THRESHOLD} "{file_path}"'

    result = subprocess.run(semantic_command, shell=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode == 0:
        # Process Semantic Classification result
        process_semantic_result(result.stdout)
    else:
        print(
            f"Semantic Classification failed. Error message:\n{result.stderr}")


def process_semantic_result(output):
    # Pre-process string to only consider the response between the following strs
    # Define the start and end strings
    start_str = '<SYSTEM name="Template" value="default"/>'
    end_str = '<ARTICLE>'

    # Use regular expression to find the text between start and end
    result = re.search(
        f'{re.escape(start_str)}(.*?){re.escape(end_str)}', output, re.DOTALL)
    output = result.group(1).strip()

    # Process the Semantic Classification result
    pattern = r'<META name="Generic_UPWARD" value="(.*?)"[^>]*? score="(.*?)"'
    matches = re.findall(pattern, output)

    matches = sorted(set(matches), key=lambda x: float(x[1]), reverse=True)

    for match in matches[:MAX_TOPICS]:
        value, score = match
        if INCLUDE_SCORING:
            print(f"{value} ({score})")
        else:
            print(f"{value}")
    print()


def main():
    args = parse_arguments()
    preservica_ref = args.preservica_ref
    directory = args.directory

    if preservica_ref:
        download_files(preservica_ref, directory)

    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        process_file(file_path)


if __name__ == "__main__":
    main()
