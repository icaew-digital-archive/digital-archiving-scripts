import requests
import xml.etree.ElementTree as ET
import csv
import os
import sys
import argparse

# Configuration constants
SECRET = "5c990ebbaed151a0319cdb13d6466a92"
PARTNER_ID = "3000931"

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
        "expiry": (None, "604800")
    }
    
    response = requests.post(url, files=files)
    root = ET.fromstring(response.text)
    ks = root.find("result").text if root.find("result") is not None else None
    
    if not ks:
        raise ValueError("KS value not found in the response")
    return ks

def collect_video_urls(ks, entry_id, specific_flavor=None):
    """Collect video URLs for a media entry using the flavorAsset API"""
    service_names = ["flavorAsset", "flavorasset", "flavor"]
    
    flavor_assets = []
    working_service = None
    
    for service_name in service_names:
        url = "https://mp.streamamg.com/api_v3/"
        
        files = {
            "ks": (None, ks),
            "clientTag": (None, "testme"),
            "service": (None, service_name),
            "action": (None, "getByEntryId"),
            "entryId": (None, entry_id),
        }
        
        response = requests.post(url, files=files)
        
        if "SERVICE_DOES_NOT_EXISTS" not in response.text:
            root = ET.fromstring(response.text)
            assets = root.findall(".//item")
            if assets:
                flavor_assets = assets
                working_service = service_name
                break
    
    if not flavor_assets:
        return {}
    
    # Filter flavors if specific flavor is requested
    if specific_flavor is not None:
        filtered_assets = []
        for asset in flavor_assets:
            flavor_params_id = asset.find("flavorParamsId").text if asset.find("flavorParamsId") is not None else "unknown"
            if str(flavor_params_id) == str(specific_flavor):
                filtered_assets.append(asset)
        
        if not filtered_assets:
            return {}
        
        flavor_assets = filtered_assets
    
    urls = {}
    
    for asset in flavor_assets:
        asset_id = asset.find("id").text if asset.find("id") is not None else None
        flavor_params_id = asset.find("flavorParamsId").text if asset.find("flavorParamsId") is not None else "unknown"
        
        if not asset_id:
            continue
        
        # Get download URL for the flavor asset
        download_url_api = "https://mp.streamamg.com/api_v3/"
        download_url_files = {
            "ks": (None, ks),
            "clientTag": (None, "testme"),
            "service": (None, working_service),
            "action": (None, "getDownloadUrl"),
            "id": (None, asset_id),
        }
        
        url_response = requests.post(download_url_api, files=download_url_files)
        
        if url_response.status_code == 200:
            root = ET.fromstring(url_response.text)
            download_url = root.find("result").text if root.find("result") is not None else None
            
            if download_url:
                urls[flavor_params_id] = download_url
    
    return urls

def collect_thumbnail_urls(ks, entry_id):
    """Collect thumbnail URLs for a media entry using the thumbAsset API"""
    service_names = ["thumbAsset", "thumbasset", "thumbnail"]
    
    thumb_assets = []
    working_service = None
    
    for service_name in service_names:
        url = "https://mp.streamamg.com/api_v3/"
        
        files = {
            "ks": (None, ks),
            "clientTag": (None, "testme"),
            "service": (None, service_name),
            "action": (None, "list"),
            "filter:objectType": (None, "KalturaAssetFilter"),
            "filter:entryIdEqual": (None, entry_id),
        }
        
        response = requests.post(url, files=files)
        
        if "SERVICE_DOES_NOT_EXISTS" not in response.text:
            root = ET.fromstring(response.text)
            assets = root.findall(".//item")
            if assets:
                thumb_assets = assets
                working_service = service_name
                break
    
    if not thumb_assets:
        return []
    
    urls = []
    
    for asset in thumb_assets:
        asset_id = asset.find("id").text if asset.find("id") is not None else None
        
        if not asset_id:
            continue
        
        # Construct browser-usable GET URL for the thumbnail
        serve_url = f"https://mp.streamamg.com/api_v3/?service={working_service}&action=serve&thumbAssetId={asset_id}&ks={ks}"
        urls.append(serve_url)
    
    return urls

def collect_caption_urls(ks, entry_id):
    """Collect caption URLs for a media entry"""
    service_names = ["caption_captionasset", "caption", "captionAsset", "captionasset", "captions"]
    
    caption_assets = []
    working_service = None
    
    for service_name in service_names:
        url = "https://mp.streamamg.com/api_v3/"
        
        files = {
            "ks": (None, ks),
            "clientTag": (None, "testme"),
            "service": (None, service_name),
            "action": (None, "list"),
            "filter:objectType": (None, "KalturaAssetFilter"),
            "filter:entryIdEqual": (None, entry_id),
        }
        
        response = requests.post(url, files=files)
        
        if "SERVICE_DOES_NOT_EXISTS" not in response.text:
            root = ET.fromstring(response.text)
            assets = root.findall(".//item")
            if assets:
                caption_assets = assets
                working_service = service_name
                break
    
    if not caption_assets:
        return []
    
    urls = []
    
    for asset in caption_assets:
        asset_id = asset.find("id").text if asset.find("id") is not None else None
        
        if not asset_id:
            continue
        
        # Construct browser-usable GET URL for the caption
        serve_url = f"https://mp.streamamg.com/api_v3/?service={working_service}&action=serve&captionAssetId={asset_id}&ks={ks}"
        urls.append(serve_url)
    
    return urls

def collect_entry_urls(ks, row, specific_flavor=None):
    """Collect all URLs for a single media entry"""
    entry_id = row.get('id')
    entry_name = row.get('name') or row.get('title', 'Unknown')
    
    if not entry_id:
        return None
    
    print(f"Collecting URLs for: {entry_name} (ID: {entry_id})")
    
    # Collect video URLs
    video_urls = collect_video_urls(ks, entry_id, specific_flavor)
    video_url_flavor0 = video_urls.get('0', '') if video_urls else ''
    
    # Collect thumbnail URLs
    thumbnail_urls = collect_thumbnail_urls(ks, entry_id)
    
    # Collect caption URLs
    caption_urls = collect_caption_urls(ks, entry_id)
    
    # Format URLs for CSV
    thumbnail_urls_str = '; '.join(thumbnail_urls) if thumbnail_urls else ''
    caption_urls_str = '; '.join(caption_urls) if caption_urls else ''
    
    return {
        'id': entry_id,
        'title': entry_name.strip() if entry_name else '',
        'video_url_flavor0': video_url_flavor0,
        'thumbnail_urls': thumbnail_urls_str,
        'caption_urls': caption_urls_str
    }

def main():
    parser = argparse.ArgumentParser(
        description="Collect StreamAMG URLs and output to CSV without downloading files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect all URLs for all videos
  python collect_streamamg_urls.py media_list_page1.csv --output urls.csv

  # Collect URLs for only flavor 1
  python collect_streamamg_urls.py media_list_page1.csv --output urls.csv --flavor 1
        """
    )
    
    parser.add_argument(
        'csv_file',
        help='Path to the CSV file containing media metadata'
    )
    
    parser.add_argument(
        '--output',
        required=True,
        help='Output CSV file path for collected URLs'
    )
    
    parser.add_argument(
        '--flavor',
        type=int,
        help='Collect only a specific flavor ID (e.g., --flavor 1). If not specified, collects all available flavors.'
    )
    
    args = parser.parse_args()
    
    csv_file = args.csv_file
    output_file = args.output
    specific_flavor = args.flavor
    
    if not os.path.exists(csv_file):
        print(f"Error: CSV file '{csv_file}' not found.")
        sys.exit(1)
    
    print(f"Starting StreamAMG URL collection...")
    if specific_flavor is not None:
        print(f"Flavor filter: Collecting only flavor ID {specific_flavor}")
    else:
        print(f"Flavor filter: Collecting all available flavors")
    print("=" * 60)
    
    try:
        # Get Kaltura session
        print("Getting authentication token...")
        ks_value = get_ks()
        print("Authentication successful!")
        print("=" * 60)
        
        # Collect URLs and write to CSV
        with open(csv_file, mode='r', encoding='utf-8-sig') as file, \
             open(output_file, mode='w', newline='', encoding='utf-8') as output:
            
            reader = csv.DictReader(file)
            writer = csv.DictWriter(output, fieldnames=['id', 'title', 'video_url_flavor0', 'thumbnail_urls', 'caption_urls'])
            writer.writeheader()
            
            total_entries = 0
            processed_entries = 0
            
            for row in reader:
                total_entries += 1
                print(f"\nProcessing entry {total_entries}: {row.get('name', 'Unknown')}")
                
                url_data = collect_entry_urls(ks_value, row, specific_flavor)
                if url_data:
                    writer.writerow(url_data)
                    processed_entries += 1
                    print(f"  ✓ Collected URLs")
                else:
                    print(f"  ✗ No URLs found")
                
                # Add a small delay to be respectful to the server
                import time
                time.sleep(1)
        
        print("\n" + "=" * 60)
        print(f"URL collection complete!")
        print(f"Total entries processed: {processed_entries}/{total_entries}")
        print(f"Output file: {output_file}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 