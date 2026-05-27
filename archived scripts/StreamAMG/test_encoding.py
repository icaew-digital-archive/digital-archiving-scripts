#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script to identify the correct encoding for StreamAMG API responses.
This will help you determine what encoding to use in the main script.
"""

import requests
import chardet
import xml.etree.ElementTree as ET

# Configuration constants
SECRET = "5c990ebbaed151a0319cdb13d6466a92"
PARTNER_ID = "3000931"

def test_encoding():
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
        "expiry": (None, "604800")
    }

    # Make the POST request
    response = requests.post(url, files=files)
    
    if response.status_code != 200:
        print(f"API request failed with status code: {response.status_code}")
        return

    print("=== ENCODING ANALYSIS ===")
    print(f"Response status code: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    print(f"Content-Type header: {response.headers.get('content-type', 'Not found')}")
    print(f"Response encoding detected by requests: {response.encoding}")
    
    # Analyze the raw content
    print(f"\n=== CONTENT ANALYSIS ===")
    print(f"Content length: {len(response.content)} bytes")
    
    # Use chardet to detect encoding
    detected = chardet.detect(response.content)
    print(f"chardet detection: {detected}")
    
    # Test different encodings
    encodings_to_test = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'ascii']
    
    print(f"\n=== ENCODING TESTS ===")
    for encoding in encodings_to_test:
        try:
            decoded = response.content.decode(encoding)
            print(f"✓ {encoding}: Successfully decoded {len(decoded)} characters")
            
            # Try to parse as XML
            try:
                root = ET.fromstring(decoded)
                print(f"  ✓ XML parsing successful with {encoding}")
                
                # Show a sample of the content
                result = root.find("result")
                if result is not None and result.text:
                    sample = result.text[:100] + "..." if len(result.text) > 100 else result.text
                    print(f"  Sample content: {repr(sample)}")
                break
                
            except ET.ParseError as e:
                print(f"  ✗ XML parsing failed with {encoding}: {e}")
                
        except UnicodeDecodeError as e:
            print(f"✗ {encoding}: Decode error - {e}")
    
    print(f"\n=== RECOMMENDATION ===")
    if detected['encoding']:
        confidence = detected['confidence']
        if confidence > 0.8:
            print(f"Use FORCE_ENCODING = '{detected['encoding']}' (confidence: {confidence:.2f})")
        else:
            print(f"Low confidence in chardet detection. Try manual encoding.")
    else:
        print("No encoding detected. Try common encodings like 'utf-8' or 'latin-1'")

if __name__ == "__main__":
    test_encoding() 