#!/usr/bin/env python3
"""
This script fetches and processes SSL/TLS certificate information from the crt.sh website 
based on a specified domain (icaew.com in this case). It performs the following tasks:

1. Sends a GET request to fetch the HTML content of the crt.sh page.
2. Parses the HTML content using BeautifulSoup to extract the "Matching Identities" 
   from the table containing certificate data.
3. Removes duplicate entries from the extracted identities to generate a unique list.
4. Writes the sorted list of unique matching identities to a text file 
   ("unique_matching_identities.txt").

Dependencies:
- requests: for sending HTTP requests.
- BeautifulSoup (from bs4): for parsing HTML content.

"""

import argparse
import requests
from bs4 import BeautifulSoup
import time

# Function to fetch and extract unique matching identities


def fetch_and_extract_unique_matching_identities(url, max_retries=3, retry_delay=5):
    """
    Fetch and extract unique matching identities with retry logic for rate limiting.
    
    Args:
        url: The URL to fetch from
        max_retries: Maximum number of retry attempts for 429 errors
        retry_delay: Initial delay in seconds between retries (doubles each retry)
    
    Returns:
        List of unique matching identities, or None if all retries failed
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for attempt in range(max_retries):
        # Send a GET request to fetch the HTML content
        response = requests.get(url, headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            break
        elif response.status_code in (429, 503):
            # Retry on rate limiting (429) or service unavailable (503)
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                status_msg = "Rate limited" if response.status_code == 429 else "Service unavailable"
                print(
                    f"{status_msg} ({response.status_code}). Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
                continue
            else:
                status_name = "Too Many Requests" if response.status_code == 429 else "Service Unavailable"
                print(
                    f"Failed to fetch data from {url} after {max_retries} attempts. Status Code: {response.status_code} ({status_name})")
                print("Please wait a few minutes and try again.")
                return None
        else:
            print(
                f"Failed to fetch data from {url}, Status Code: {response.status_code}")
            return None
    
    if response.status_code != 200:
        return None

    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all table rows (tr)
    rows = soup.find_all('tr')

    # Extract the values in the "Matching Identities" column
    matching_identities = []
    for row in rows[1:]:  # Skip the header row
        cells = row.find_all('td')
        if len(cells) > 5:  # Ensure there are enough columns in the row
            matching_identity = cells[5].get_text(strip=True)
            matching_identities.append(matching_identity)

    # Remove duplicates by converting to a set and back to a list
    unique_matching_identities = list(set(matching_identities))

    # Sort the list for better readability
    unique_matching_identities.sort()

    print(f"Found {len(unique_matching_identities)} unique matching identities")
    return unique_matching_identities

# Function to write the list to a text file


def write_list_to_file(filename, data_list):
    with open(filename, 'w') as file:
        for item in data_list:
            file.write(f"{item}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch unique SSL/TLS certificate identities for a domain from crt.sh.",
        epilog="Example: python crt-scraper.py icaew.com --output icaew_certs.txt",
    )
    parser.add_argument("domain", help="Domain to query on crt.sh (e.g. icaew.com)")
    parser.add_argument(
        "--output",
        default="unique_matching_identities.txt",
        metavar="OUTPUT_FILE",
        help="Output text file (default: unique_matching_identities.txt)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        metavar="N",
        help="Maximum number of retry attempts on rate-limit errors (default: 3)",
    )
    args = parser.parse_args()

    query_url = f"https://crt.sh/?q={args.domain}"
    unique_identities = fetch_and_extract_unique_matching_identities(query_url, max_retries=args.retries)

    if unique_identities is not None:
        if len(unique_identities) > 0:
            write_list_to_file(args.output, unique_identities)
            print(f"Unique matching identities have been written to {args.output}")
        else:
            print("No matching identities found in the response.")
    else:
        print("Failed to fetch data. No file written.")
