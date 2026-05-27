import requests
import xml.etree.ElementTree as ET
import os
import sys

# Configuration constants
SECRET = "5c990ebbaed151a0319cdb13d6466a92"
PARTNER_ID = "3000931"
CAPTIONS_DIR = "captions"  # Directory to save downloaded captions

def get_ks():
    """Get Kaltura session token"""
    url = "https://mp.streamamg.com/api_v3/"
    
    files = {
        "clientTag": (None, "testme"),
        "service": (None, "session"),
        "action": (None, "start"),
        "secret": (None, SECRET),
        "type": (None, "2"),
        "partnerId": (None, PARTNER_ID),
    }
    
    response = requests.post(url, files=files)
    root = ET.fromstring(response.text)
    ks = root.find("result").text if root.find("result") is not None else None
    
    if not ks:
        raise ValueError("KS value not found in the response")
    return ks

def get_entry_info(ks, entry_id):
    """Get basic entry information including name/title"""
    url = "https://mp.streamamg.com/api_v3/"
    
    files = {
        "ks": (None, ks),
        "clientTag": (None, "testme"),
        "service": (None, "media"),
        "action": (None, "get"),
        "entryId": (None, entry_id),
    }
    
    response = requests.post(url, files=files)
    root = ET.fromstring(response.text)
    
    # Extract name or title
    name = root.find(".//name")
    title = root.find(".//title")
    
    entry_name = None
    if name is not None and name.text:
        entry_name = name.text
    elif title is not None and title.text:
        entry_name = title.text
    
    return entry_name

def download_captions(ks, entry_id, entry_name=None):
    """Download captions for a specific media entry"""
    # Create captions directory if it doesn't exist
    if not os.path.exists(CAPTIONS_DIR):
        os.makedirs(CAPTIONS_DIR)
    
    # Sanitize entry name for filename
    if entry_name:
        safe_name = "".join(c for c in entry_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
    else:
        safe_name = entry_id
    
    # Try different service names for captions
    service_names = ["caption_captionasset", "caption", "captionAsset", "captionasset", "captions"]
    
    caption_assets = []
    working_service = None
    
    for service_name in service_names:
        print(f"  Trying service name: {service_name}")
        
        # First, get the caption assets for this entry
        url = "https://mp.streamamg.com/api_v3/"
        
        files = {
            "ks": (None, ks),
            "clientTag": (None, "testme"),
            "service": (None, service_name),
            "action": (None, "list"),
            "filter:objectType": (None, "KalturaAssetFilter"),
            "filter:entryIdEqual": (None, entry_id),
        }
        
        print(f"  Requesting caption assets for entry {entry_id}...")
        response = requests.post(url, files=files)
        
        # Debug: Print response status and content
        print(f"  Caption list response status: {response.status_code}")
        print(f"  Caption list response content: {response.text[:500]}...")  # First 500 chars
        
        # Check if this service worked
        if "SERVICE_DOES_NOT_EXISTS" not in response.text:
            root = ET.fromstring(response.text)
            assets = root.findall(".//item")
            if assets:
                caption_assets = assets
                working_service = service_name
                print(f"  Success! Found {len(assets)} caption(s) using service '{service_name}'")
                break
            else:
                print(f"  Service '{service_name}' exists but no captions found")
        else:
            print(f"  Service '{service_name}' does not exist")
    
    if not caption_assets:
        print(f"No captions found for entry {entry_id} with any service")
        return 0
    
    print(f"Found {len(caption_assets)} caption(s) for entry {entry_id}")
    
    downloaded_count = 0
    
    # Download each caption
    for i, asset in enumerate(caption_assets):
        asset_id = asset.find("id").text if asset.find("id") is not None else None
        language = asset.find("language").text if asset.find("language") is not None else "unknown"
        format_type = asset.find("format").text if asset.find("format") is not None else "unknown"
        file_ext = asset.find("fileExt").text if asset.find("fileExt") is not None else "unknown"
        
        print(f"  Processing caption asset {i+1}: ID={asset_id}, Language={language}, Format={format_type}, FileExt={file_ext}")
        
        if not asset_id:
            continue
        
        # Download the caption content using the working service
        download_url = "https://mp.streamamg.com/api_v3/"
        download_files = {
            "ks": (None, ks),
            "clientTag": (None, "testme"),
            "service": (None, working_service),
            "action": (None, "serve"),
            "captionAssetId": (None, asset_id),
        }
        
        print(f"  Downloading caption content for asset {asset_id}...")
        caption_response = requests.post(download_url, files=download_files)
        
        print(f"  Download response status: {caption_response.status_code}")
        print(f"  Download response content preview: {caption_response.text[:200]}...")
        
        if caption_response.status_code == 200:
            # Determine file extension based on fileExt from API response
            if file_ext.lower() in ['vtt', 'webvtt']:
                ext = '.vtt'
            elif file_ext.lower() in ['srt']:
                ext = '.srt'
            elif file_ext.lower() in ['dfxp', 'ttml', 'xml']:
                ext = '.xml'
            else:
                ext = f'.{file_ext}' if file_ext != 'unknown' else '.txt'
            
            # Create filename - use video ID prefix + video name with correct extension
            filename = f"{entry_id}_{safe_name}{ext}"
            filepath = os.path.join(CAPTIONS_DIR, filename)
            
            # Save the caption file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(caption_response.text)
            
            print(f"  Downloaded: {filename}")
            downloaded_count += 1
        else:
            print(f"  Failed to download caption {asset_id}: {caption_response.status_code}")
    
    return downloaded_count

def read_video_ids(filename):
    """Read video IDs from a text file"""
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        return []
    
    with open(filename, 'r') as f:
        # Read lines and strip whitespace, filter out empty lines
        video_ids = [line.strip() for line in f.readlines() if line.strip()]
    
    return video_ids

def main():
    # Check if video IDs file is provided
    if len(sys.argv) != 2:
        print("Usage: python download_captions.py <video_ids_file.txt>")
        print("Example: python download_captions.py video_ids.txt")
        sys.exit(1)
    
    video_ids_file = sys.argv[1]
    
    # Read video IDs from file
    video_ids = read_video_ids(video_ids_file)
    
    if not video_ids:
        print("No video IDs found in the file.")
        sys.exit(1)
    
    print(f"Found {len(video_ids)} video ID(s) to process")
    print("=" * 50)
    
    try:
        # Get Kaltura session
        print("Getting authentication token...")
        ks_value = get_ks()
        print("Authentication successful!")
        print("=" * 50)
        
        total_downloaded = 0
        
        # Process each video ID
        for i, video_id in enumerate(video_ids, 1):
            print(f"Processing video {i}/{len(video_ids)}: {video_id}")
            
            # Get entry info for better filename
            try:
                entry_name = get_entry_info(ks_value, video_id)
                if entry_name:
                    print(f"  Entry name: {entry_name}")
            except Exception as e:
                print(f"  Warning: Could not get entry info: {e}")
                entry_name = None
            
            # Download captions
            downloaded = download_captions(ks_value, video_id, entry_name)
            total_downloaded += downloaded
            
            print("-" * 50)
        
        print(f"Download complete! Total captions downloaded: {total_downloaded}")
        print(f"Captions saved to: {os.path.abspath(CAPTIONS_DIR)}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 