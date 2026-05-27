import requests
import xml.etree.ElementTree as ET
import csv

# Configuration constants
SECRET = ""
PARTNER_ID = "3000931"
PAGE_INDEX = "4"
CSV_FILE = "media_list_page4.csv"

# Step 1: First API call to extract `ks` value
def get_ks():
    # Define the endpoint URL
    url = "https://mp.streamamg.com/api_v3/"

    # Define the form data for the first request
    files = {
        "clientTag": (None, "testme"),
        "service": (None, "session"),
        "action": (None, "start"),
        "secret": (None, SECRET),
        "type": (None, "2"),
        "partnerId": (None, PARTNER_ID),
    }

    # Make the POST request
    response = requests.post(url, files=files)

    # Parse the response to extract the `ks` value
    root = ET.fromstring(response.text)
    ks = root.find("result").text if root.find("result") is not None else None
    if not ks:
        raise ValueError("KS value not found in the response")
    return ks

# Step 2: Second API call using the extracted `ks` value
def list_media(ks):
    # Define the endpoint URL
    url = "https://mp.streamamg.com/api_v3/"

    # Define the form data for the second request
    files = {
        "ks": (None, ks),
        "clientTag": (None, "testme"),
        "service": (None, "media"),
        "action": (None, "list"),
        "pager:objectType": (None, "KalturaFilterPager"),
        "pager:pageSize": (None, "500"),
        "pager:pageIndex": (None, PAGE_INDEX),
    }

    # Make the POST request
    response = requests.post(url, files=files)

    # Parse the XML response
    root = ET.fromstring(response.text)

    # Extract media entries
    media_entries = root.findall(".//item")
    if not media_entries:
        raise ValueError("No media entries found in the response")

    # Gather all unique tags
    all_tags = set()
    for item in media_entries:
        all_tags.update(child.tag for child in item)

    # Open the CSV file for writing
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # Write the header row
        headers = list(all_tags)
        writer.writerow(headers)

        # Write data rows
        for item in media_entries:
            row = []
            for tag in headers:
                value = item.find(tag).text if item.find(tag) is not None else ""
                row.append(value)
            writer.writerow(row)

    print(f"Media list with all tags saved to {CSV_FILE}")

# Execute the requests
try:
    ks_value = get_ks()
    print("Extracted KS Value:", ks_value)
    list_media(ks_value)
except Exception as e:
    print(f"An error occurred: {e}")

