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

import requests
from bs4 import BeautifulSoup

# URL for fetching the data
url = "https://crt.sh/?q=icaew.com"

# Function to fetch and extract unique matching identities


def fetch_and_extract_unique_matching_identities(url):
    # Send a GET request to fetch the HTML content
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code != 200:
        print(
            f"Failed to fetch data from {url}, Status Code: {response.status_code}")
        return []

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

    return unique_matching_identities

# Function to write the list to a text file


def write_list_to_file(filename, data_list):
    with open(filename, 'w') as file:
        for item in data_list:
            file.write(f"{item}\n")


# Fetch and extract unique identities
unique_identities = fetch_and_extract_unique_matching_identities(url)

# Write the unique list to a text file
output_file = "unique_matching_identities.txt"
write_list_to_file(output_file, unique_identities)

print(f"Unique matching identities have been written to {output_file}")
