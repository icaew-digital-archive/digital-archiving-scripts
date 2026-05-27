import requests
import xml.etree.ElementTree as ET
import csv
import chardet

# Configuration constants
SECRET = "5c990ebbaed151a0319cdb13d6466a92"
PARTNER_ID = "3000931"
PAGE_INDEX = "2"
CSV_FILE = "media_list_page2.csv"

# Encoding configuration - set to None for auto-detection, or specify like 'utf-8', 'latin-1', etc.
# Run test_encoding.py first to determine the correct encoding for your API responses
FORCE_ENCODING = None  # Change this if you know the correct encoding

# Step 1: First API call to extract `ks` value
def get_ks():
    # Define the endpoint URL
    url = "https://mp.streamamg.com/api_v3/"

    # Define the form data for the first request, hardcoded expiry date
    files = {
        "clientTag": (None, "testme"),
        "service": (None, "session"),
        "action": (None, "start"),
        "secret": (None, SECRET),
        "type": (None, "2"),
        "partnerId": (None, PARTNER_ID),
        "expiry": (None, "604800")
    }

    # Make the POST request
    response = requests.post(url, files=files)
    
    if response.status_code != 200:
        raise ValueError(f"API request failed with status code: {response.status_code}")

    # Detect encoding and decode properly
    print(f"Response encoding detected by requests: {response.encoding}")
    
    if FORCE_ENCODING:
        # Use manually specified encoding
        print(f"Using forced encoding: {FORCE_ENCODING}")
        response_text = response.content.decode(FORCE_ENCODING, errors='replace')
    elif response.encoding == 'ISO-8859-1':
        # requests often defaults to ISO-8859-1 when it can't detect encoding
        detected = chardet.detect(response.content)
        encoding = detected['encoding'] if detected['encoding'] else 'utf-8'
        print(f"chardet detected encoding: {detected}")
        print(f"Using encoding: {encoding}")
        response_text = response.content.decode(encoding, errors='replace')
    else:
        response_text = response.text

    # Parse the response to extract the `ks` value
    root = ET.fromstring(response_text)
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
    
    if response.status_code != 200:
        raise ValueError(f"Media list API request failed with status code: {response.status_code}")

    # Detect encoding and decode properly
    print(f"Media list response encoding detected by requests: {response.encoding}")
    
    if FORCE_ENCODING:
        # Use manually specified encoding
        print(f"Using forced encoding: {FORCE_ENCODING}")
        response_text = response.content.decode(FORCE_ENCODING, errors='replace')
    elif response.encoding == 'ISO-8859-1':
        # requests often defaults to ISO-8859-1 when it can't detect encoding
        detected = chardet.detect(response.content)
        encoding = detected['encoding'] if detected['encoding'] else 'utf-8'
        print(f"Media list chardet detected encoding: {detected}")
        print(f"Using encoding: {encoding}")
        response_text = response.content.decode(encoding, errors='replace')
    else:
        response_text = response.text

    # Parse the XML response
    root = ET.fromstring(response_text)

    # Extract media entries
    media_entries = root.findall(".//item")
    if not media_entries:
        raise ValueError("No media entries found in the response")

    # Gather all unique tags
    all_tags = set()
    for item in media_entries:
        all_tags.update(child.tag for child in item)

    # Open the CSV file for writing
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)

        # Write the header row
        headers = list(all_tags)
        writer.writerow(headers)

        # Write data rows
        for item in media_entries:
            row = []
            for tag in headers:
                element = item.find(tag)
                if element is not None and element.text is not None:
                    # Clean the text and handle encoding issues
                    value = element.text.strip()
                    # Replace any problematic characters
                    value = value.replace('\x00', '').replace('\ufffd', '?')
                else:
                    value = ""
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

