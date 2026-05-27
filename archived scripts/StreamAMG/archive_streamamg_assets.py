import requests
import xml.etree.ElementTree as ET
import csv
import os
import sys
import json
import argparse
from urllib.parse import urlparse
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuration constants
SECRET = "5c990ebbaed151a0319cdb13d6466a92"
PARTNER_ID = "3000931"
DEFAULT_ARCHIVE_DIR = "/media/digital-archivist/Elements"  # Default archive directory

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # Base delay in seconds
RETRY_DELAY_MAX = 30  # Maximum delay in seconds
TIMEOUT = 30  # Request timeout in seconds

def create_session_with_retry(max_retries=None, timeout=None):
    """Create a requests session with retry logic"""
    session = requests.Session()
    
    # Use provided values or defaults
    retry_count = max_retries if max_retries is not None else MAX_RETRIES
    request_timeout = timeout if timeout is not None else TIMEOUT
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=retry_count,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        backoff_factor=RETRY_DELAY_BASE,
        raise_on_status=False
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def get_ks(max_retries=None, timeout=None):
    """Get Kaltura session token with retry logic"""
    session = create_session_with_retry(max_retries, timeout)
    url = "https://mp.streamamg.com/api_v3/"
    
    # Use provided values or defaults
    retry_count = max_retries if max_retries is not None else MAX_RETRIES
    request_timeout = timeout if timeout is not None else TIMEOUT
    
    files = {
        "clientTag": (None, "testme"),
        "service": (None, "session"),
        "action": (None, "start"),
        "secret": (None, SECRET),
        "type": (None, "2"),
        "partnerId": (None, PARTNER_ID),
    }
    
    for attempt in range(retry_count + 1):
        try:
            print(f"  Attempting to get authentication token (attempt {attempt + 1}/{retry_count + 1})...")
            response = session.post(url, files=files, timeout=request_timeout)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            ks = root.find("result").text if root.find("result") is not None else None
            
            if ks:
                print(f"  ✓ Authentication successful!")
                return ks
            else:
                raise ValueError("KS value not found in the response")
                
        except (requests.exceptions.RequestException, ValueError, ET.ParseError) as e:
            if attempt < retry_count:
                delay = min(RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 1), RETRY_DELAY_MAX)
                print(f"  ✗ Attempt {attempt + 1} failed: {e}")
                print(f"  Waiting {delay:.1f} seconds before retry...")
                time.sleep(delay)
            else:
                print(f"  ✗ All {retry_count + 1} attempts failed")
                raise ValueError(f"Failed to get authentication token after {retry_count + 1} attempts: {e}")
    
    raise ValueError("Failed to get authentication token")

def get_single_entry_metadata(ks, entry_id, max_retries=None, timeout=None):
    """Fetch metadata for a single entry from the StreamAMG API"""
    session = create_session_with_retry(max_retries, timeout)
    
    # Use provided values or defaults
    retry_count = max_retries if max_retries is not None else MAX_RETRIES
    request_timeout = timeout if timeout is not None else TIMEOUT
    
    # Try different service names for media entries
    service_names = ["media", "baseEntry", "baseentry"]
    
    for service_name in service_names:
        url = "https://mp.streamamg.com/api_v3/"
        
        files = {
            "ks": (None, ks),
            "clientTag": (None, "testme"),
            "service": (None, service_name),
            "action": (None, "get"),
            "entryId": (None, entry_id),
        }
        
        for attempt in range(retry_count + 1):
            try:
                print(f"  Attempting to fetch entry metadata (attempt {attempt + 1}/{retry_count + 1})...")
                response = session.post(url, files=files, timeout=request_timeout)
                response.raise_for_status()
                
                if "SERVICE_DOES_NOT_EXISTS" not in response.text:
                    root = ET.fromstring(response.text)
                    result = root.find("result")
                    if result is not None:
                        # Convert XML to dictionary-like structure
                        entry_data = {}
                        for child in result:
                            entry_data[child.tag] = child.text
                        
                        # Add the entry ID
                        entry_data['id'] = entry_id
                        
                        print(f"  ✓ Successfully fetched entry metadata")
                        return entry_data
                break  # Service doesn't exist, try next service
                
            except (requests.exceptions.RequestException, ET.ParseError) as e:
                if attempt < retry_count:
                    delay = min(RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 1), RETRY_DELAY_MAX)
                    print(f"  ✗ Attempt {attempt + 1} failed: {e}")
                    print(f"  Waiting {delay:.1f} seconds before retry...")
                    time.sleep(delay)
                else:
                    print(f"  ✗ All {retry_count + 1} attempts failed")
                    break
        
        if service_name == service_names[-1]:  # Last service tried
            raise ValueError(f"Failed to fetch entry {entry_id} metadata after trying all services")
    
    raise ValueError(f"Failed to fetch entry {entry_id} metadata")

def sanitize_filename(filename):
    """Sanitize filename for safe file system usage"""
    # Remove or replace problematic characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename

def download_file(url, filepath, description="", max_retries=None, timeout=None):
    """Download a file from URL to filepath with retry logic"""
    session = create_session_with_retry(max_retries, timeout)
    
    # Use provided values or defaults
    retry_count = max_retries if max_retries is not None else MAX_RETRIES
    request_timeout = timeout if timeout is not None else TIMEOUT
    
    for attempt in range(retry_count + 1):
        try:
            print(f"  Downloading {description} (attempt {attempt + 1}/{retry_count + 1})...")
            print(f"    URL: {url}")
            
            response = session.get(url, stream=True, timeout=request_timeout)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"    ✓ Downloaded: {os.path.basename(filepath)}")
            return True
            
        except (requests.exceptions.RequestException, IOError) as e:
            if attempt < retry_count:
                delay = min(RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 1), RETRY_DELAY_MAX)
                print(f"    ✗ Attempt {attempt + 1} failed: {e}")
                print(f"    Waiting {delay:.1f} seconds before retry...")
                time.sleep(delay)
            else:
                print(f"    ✗ Failed to download {description} after {retry_count + 1} attempts: {e}")
                return False
    
    return False

def download_captions(ks, entry_id, entry_name, captions_dir, max_retries=None, timeout=None):
    """Download captions for a media entry with retry logic"""
    session = create_session_with_retry(max_retries, timeout)
    
    # Use provided values or defaults
    retry_count = max_retries if max_retries is not None else MAX_RETRIES
    request_timeout = timeout if timeout is not None else TIMEOUT
    
    # Try different service names for captions
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
        
        for attempt in range(retry_count + 1):
            try:
                response = session.post(url, files=files, timeout=request_timeout)
                response.raise_for_status()
                
                if "SERVICE_DOES_NOT_EXISTS" not in response.text:
                    root = ET.fromstring(response.text)
                    assets = root.findall(".//item")
                    if assets:
                        caption_assets = assets
                        working_service = service_name
                        break
                break  # Service doesn't exist, try next service
                
            except (requests.exceptions.RequestException, ET.ParseError) as e:
                if attempt < retry_count:
                    delay = min(RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 1), RETRY_DELAY_MAX)
                    print(f"    Caption API attempt {attempt + 1} failed: {e}")
                    print(f"    Waiting {delay:.1f} seconds before retry...")
                    time.sleep(delay)
                else:
                    print(f"    Caption API failed after {retry_count + 1} attempts: {e}")
                    break
        
        if working_service:
            break
    
    if not caption_assets:
        return 0
    
    downloaded_count = 0
    
    for asset in caption_assets:
        asset_id = asset.find("id").text if asset.find("id") is not None else None
        language = asset.find("language").text if asset.find("language") is not None else "unknown"
        file_ext = asset.find("fileExt").text if asset.find("fileExt") is not None else "unknown"
        
        if not asset_id:
            continue
        
        # Construct a browser-usable GET URL for the caption
        serve_url = f"https://mp.streamamg.com/api_v3/?service={working_service}&action=serve&captionAssetId={asset_id}&ks={ks}"
        print(f"      Download URL: {serve_url}")

        # Download the caption content
        download_url = "https://mp.streamamg.com/api_v3/"
        download_files = {
            "ks": (None, ks),
            "clientTag": (None, "testme"),
            "service": (None, working_service),
            "action": (None, "serve"),
            "captionAssetId": (None, asset_id),
        }
        
        print(f"    Downloading caption {asset_id} (language: {language}, format: {file_ext})...")
        print(f"      API Call: {working_service}.serve(captionAssetId={asset_id})")
        
        for attempt in range(retry_count + 1):
            try:
                caption_response = session.post(download_url, files=download_files, timeout=request_timeout)
                caption_response.raise_for_status()
                
                if caption_response.status_code == 200:
                    # Determine file extension
                    if file_ext.lower() in ['vtt', 'webvtt']:
                        ext = '.vtt'
                    elif file_ext.lower() in ['srt']:
                        ext = '.srt'
                    elif file_ext.lower() in ['dfxp', 'ttml', 'xml']:
                        ext = '.xml'
                    else:
                        ext = f'.{file_ext}' if file_ext != 'unknown' else '.txt'
                    
                    # Create filename
                    safe_name = sanitize_filename(entry_name)
                    filename = f"{entry_id}_{safe_name}{ext}"
                    filepath = os.path.join(captions_dir, filename)
                    
                    # Save the caption file
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(caption_response.text)
                    
                    downloaded_count += 1
                    break  # Success, exit retry loop
                    
            except (requests.exceptions.RequestException, IOError) as e:
                if attempt < retry_count:
                    delay = min(RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 1), RETRY_DELAY_MAX)
                    print(f"      Caption download attempt {attempt + 1} failed: {e}")
                    print(f"      Waiting {delay:.1f} seconds before retry...")
                    time.sleep(delay)
                else:
                    print(f"      Failed to download caption after {retry_count + 1} attempts: {e}")
                    break
    
    return downloaded_count

def download_thumbnails(ks, entry_id, entry_name, thumbnails_dir, max_retries=None, timeout=None):
    """Download thumbnails for a media entry using the thumbAsset API with retry logic"""
    session = create_session_with_retry(max_retries, timeout)
    
    # Use provided values or defaults
    retry_count = max_retries if max_retries is not None else MAX_RETRIES
    request_timeout = timeout if timeout is not None else TIMEOUT
    
    # Try different service names for thumbnails
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
        
        for attempt in range(retry_count + 1):
            try:
                response = session.post(url, files=files, timeout=request_timeout)
                response.raise_for_status()
                
                if "SERVICE_DOES_NOT_EXISTS" not in response.text:
                    root = ET.fromstring(response.text)
                    assets = root.findall(".//item")
                    if assets:
                        thumb_assets = assets
                        working_service = service_name
                        break
                break  # Service doesn't exist, try next service
                
            except (requests.exceptions.RequestException, ET.ParseError) as e:
                if attempt < retry_count:
                    delay = min(RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 1), RETRY_DELAY_MAX)
                    print(f"    Thumbnail API attempt {attempt + 1} failed: {e}")
                    print(f"    Waiting {delay:.1f} seconds before retry...")
                    time.sleep(delay)
                else:
                    print(f"    Thumbnail API failed after {retry_count + 1} attempts: {e}")
                    break
        
        if working_service:
            break
    
    if not thumb_assets:
        return 0
    
    downloaded_count = 0
    
    for asset in thumb_assets:
        asset_id = asset.find("id").text if asset.find("id") is not None else None
        width = asset.find("width").text if asset.find("width") is not None else "unknown"
        height = asset.find("height").text if asset.find("height") is not None else "unknown"
        file_ext = asset.find("fileExt").text if asset.find("fileExt") is not None else "jpg"
        
        if not asset_id:
            continue
        
        # Construct a browser-usable GET URL for the thumbnail
        serve_url = f"https://mp.streamamg.com/api_v3/?service={working_service}&action=serve&thumbAssetId={asset_id}&ks={ks}"
        print(f"      Download URL: {serve_url}")

        # Download the thumbnail using serve action
        download_url = "https://mp.streamamg.com/api_v3/"
        download_files = {
            "ks": (None, ks),
            "clientTag": (None, "testme"),
            "service": (None, working_service),
            "action": (None, "serve"),
            "thumbAssetId": (None, asset_id),
        }
        
        print(f"    Downloading thumbnail {asset_id} ({width}x{height})...")
        print(f"      API Call: {working_service}.serve(thumbAssetId={asset_id})")
        
        for attempt in range(retry_count + 1):
            try:
                thumb_response = session.post(download_url, files=download_files, timeout=request_timeout)
                thumb_response.raise_for_status()
                
                if thumb_response.status_code == 200:
                    # Create filename with dimensions
                    safe_name = sanitize_filename(entry_name)
                    filename = f"{entry_id}_{safe_name}_{width}x{height}.{file_ext}"
                    filepath = os.path.join(thumbnails_dir, filename)
                    
                    # Save the thumbnail file
                    with open(filepath, 'wb') as f:
                        f.write(thumb_response.content)
                    
                    downloaded_count += 1
                    break  # Success, exit retry loop
                    
            except (requests.exceptions.RequestException, IOError) as e:
                if attempt < retry_count:
                    delay = min(RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 1), RETRY_DELAY_MAX)
                    print(f"      Thumbnail download attempt {attempt + 1} failed: {e}")
                    print(f"      Waiting {delay:.1f} seconds before retry...")
                    time.sleep(delay)
                else:
                    print(f"      Failed to download thumbnail after {retry_count + 1} attempts: {e}")
                    break
    
    return downloaded_count

def download_video_files(ks, entry_id, entry_name, videos_dir, specific_flavor=None, max_retries=None, timeout=None):
    """Download video files for a media entry using the flavorAsset API with retry logic"""
    session = create_session_with_retry(max_retries, timeout)
    
    # Use provided values or defaults
    retry_count = max_retries if max_retries is not None else MAX_RETRIES
    request_timeout = timeout if timeout is not None else TIMEOUT
    
    # Try different service names for flavor assets
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
        
        for attempt in range(retry_count + 1):
            try:
                response = session.post(url, files=files, timeout=request_timeout)
                response.raise_for_status()
                
                if "SERVICE_DOES_NOT_EXISTS" not in response.text:
                    root = ET.fromstring(response.text)
                    assets = root.findall(".//item")
                    if assets:
                        flavor_assets = assets
                        working_service = service_name
                        break
                break  # Service doesn't exist, try next service
                
            except (requests.exceptions.RequestException, ET.ParseError) as e:
                if attempt < retry_count:
                    delay = min(RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 1), RETRY_DELAY_MAX)
                    print(f"    Video API attempt {attempt + 1} failed: {e}")
                    print(f"    Waiting {delay:.1f} seconds before retry...")
                    time.sleep(delay)
                else:
                    print(f"    Video API failed after {retry_count + 1} attempts: {e}")
                    break
        
        if working_service:
            break
    
    if not flavor_assets:
        return 0
    
    # Filter flavors if specific flavor is requested
    if specific_flavor is not None:
        filtered_assets = []
        for asset in flavor_assets:
            flavor_params_id = asset.find("flavorParamsId").text if asset.find("flavorParamsId") is not None else "unknown"
            if str(flavor_params_id) == str(specific_flavor):
                filtered_assets.append(asset)
        
        if not filtered_assets:
            print(f"    ✗ No flavor {specific_flavor} found for this entry")
            return 0
        
        flavor_assets = filtered_assets
        print(f"    Filtering to flavor {specific_flavor} only")
    
    downloaded_count = 0
    
    for asset in flavor_assets:
        asset_id = asset.find("id").text if asset.find("id") is not None else None
        file_ext = asset.find("fileExt").text if asset.find("fileExt") is not None else "mp4"
        size = asset.find("size").text if asset.find("size") is not None else "unknown"
        flavor_params_id = asset.find("flavorParamsId").text if asset.find("flavorParamsId") is not None else "unknown"
        
        if not asset_id:
            continue
        
        # Get download URL for the flavor asset with retry logic
        download_url_api = "https://mp.streamamg.com/api_v3/"
        download_url_files = {
            "ks": (None, ks),
            "clientTag": (None, "testme"),
            "service": (None, working_service),
            "action": (None, "getDownloadUrl"),
            "id": (None, asset_id),
        }
        
        download_url = None
        for attempt in range(retry_count + 1):
            try:
                url_response = session.post(download_url_api, files=download_url_files, timeout=request_timeout)
                url_response.raise_for_status()
                
                if url_response.status_code == 200:
                    root = ET.fromstring(url_response.text)
                    download_url = root.find("result").text if root.find("result") is not None else None
                    if download_url:
                        break  # Success, exit retry loop
                    else:
                        print(f"    ✗ No download URL found for flavor asset {asset_id}")
                        break
                        
            except (requests.exceptions.RequestException, ET.ParseError) as e:
                if attempt < retry_count:
                    delay = min(RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 1), RETRY_DELAY_MAX)
                    print(f"    URL retrieval attempt {attempt + 1} failed: {e}")
                    print(f"    Waiting {delay:.1f} seconds before retry...")
                    time.sleep(delay)
                else:
                    print(f"    ✗ Failed to get download URL for flavor asset {asset_id} after {retry_count + 1} attempts: {e}")
                    break
        
        if download_url:
            print(f"  Downloading video file {asset_id} (flavor {flavor_params_id}, {size} bytes)...")
            print(f"    Download URL: {download_url}")
            
            # Download the video file from the URL with retry logic
            for attempt in range(retry_count + 1):
                try:
                    video_response = session.get(download_url, stream=True, timeout=request_timeout)
                    video_response.raise_for_status()
                    
                    if video_response.status_code == 200:
                        # Create filename
                        safe_name = sanitize_filename(entry_name)
                        filename = f"{entry_id}_{safe_name}_flavor{flavor_params_id}.{file_ext}"
                        filepath = os.path.join(videos_dir, filename)
                        
                        # Save the video file
                        with open(filepath, 'wb') as f:
                            for chunk in video_response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        print(f"    ✓ Downloaded: {filename}")
                        downloaded_count += 1
                        break  # Success, exit retry loop
                    else:
                        print(f"    ✗ Failed to download video {asset_id}: {video_response.status_code}")
                        break
                        
                except (requests.exceptions.RequestException, IOError) as e:
                    if attempt < retry_count:
                        delay = min(RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 1), RETRY_DELAY_MAX)
                        print(f"    Video download attempt {attempt + 1} failed: {e}")
                        print(f"    Waiting {delay:.1f} seconds before retry...")
                        time.sleep(delay)
                    else:
                        print(f"    ✗ Failed to download video {asset_id} after {retry_count + 1} attempts: {e}")
                        break
    
    return downloaded_count

def archive_media_entry(ks, row, archive_base_dir, specific_flavor=None, max_retries=None, timeout=None):
    """Archive a single media entry with all its assets"""
    entry_id = row.get('id')
    entry_name = row.get('name') or row.get('title', 'Unknown')
    download_url = row.get('downloadUrl')
    thumbnail_url = row.get('thumbnailUrl')
    
    if not entry_id:
        print(f"Skipping entry without ID")
        return False
    
    # Create entry-specific directory
    safe_name = sanitize_filename(entry_name)
    entry_dir = os.path.join(archive_base_dir, f"{entry_id}_{safe_name}")
    os.makedirs(entry_dir, exist_ok=True)
    
    print(f"Archiving: {entry_name} (ID: {entry_id})")
    
    success_count = 0
    
    # 1. Save metadata as JSON
    metadata_file = os.path.join(entry_dir, "metadata.json")
    try:
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(row, f, indent=2, ensure_ascii=False)
        print("  ✓ Saved metadata")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Failed to save metadata: {e}")
    
    # 2. Download video files using API
    videos_dir = os.path.join(entry_dir, "videos")
    os.makedirs(videos_dir, exist_ok=True)
    video_count = download_video_files(ks, entry_id, entry_name, videos_dir, specific_flavor, max_retries, timeout)
    if video_count > 0:
        print(f"  ✓ Downloaded {video_count} video file(s)")
        success_count += 1
    else:
        # Fallback to CSV download URL if API doesn't work
        if download_url:
            video_filename = f"{entry_id}_{safe_name}.mp4"
            video_filepath = os.path.join(videos_dir, video_filename)
            if download_file(download_url, video_filepath, "video (fallback)", max_retries, timeout):
                print("  ✓ Downloaded video (fallback)")
                success_count += 1
    
    # 3. Download thumbnails using API
    thumbnails_dir = os.path.join(entry_dir, "thumbnails")
    os.makedirs(thumbnails_dir, exist_ok=True)
    thumb_count = download_thumbnails(ks, entry_id, entry_name, thumbnails_dir, max_retries, timeout)
    if thumb_count > 0:
        print(f"  ✓ Downloaded {thumb_count} thumbnail(s)")
        success_count += 1
    else:
        # Fallback to CSV thumbnail URL if API doesn't work
        if thumbnail_url:
            thumbnail_filename = f"{entry_id}_{safe_name}_thumbnail.jpg"
            thumbnail_filepath = os.path.join(thumbnails_dir, thumbnail_filename)
            if download_file(thumbnail_url, thumbnail_filepath, "thumbnail (fallback)", max_retries, timeout):
                print("  ✓ Downloaded thumbnail (fallback)")
                success_count += 1
    
    # 4. Download captions
    captions_dir = os.path.join(entry_dir, "captions")
    os.makedirs(captions_dir, exist_ok=True)
    caption_count = download_captions(ks, entry_id, entry_name, captions_dir, max_retries, timeout)
    if caption_count > 0:
        print(f"  ✓ Downloaded {caption_count} caption(s)")
        success_count += 1
    
    print(f"  Archive complete: {success_count} assets saved")
    return True

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(
        description="Archive StreamAMG media assets from a CSV file or download a single asset by entry ID",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all flavors for all videos from CSV to default directory
  python archive_streamamg_assets.py --csv-file media_list_page1.csv

  # Download only flavor ID 1 for all videos from CSV
  python archive_streamamg_assets.py --csv-file media_list_page1.csv --flavor 1

  # Download to a custom directory
  python archive_streamamg_assets.py --csv-file media_list_page1.csv --output-dir /path/to/custom/folder

  # Download a single asset by entry ID
  python archive_streamamg_assets.py --entry-id 0_abc123def456

  # Download a single asset with specific flavor
  python archive_streamamg_assets.py --entry-id 0_abc123def456 --flavor 0

  # Download a single asset to custom directory
  python archive_streamamg_assets.py --entry-id 0_abc123def456 --output-dir /path/to/custom/folder
        """
    )
    
    parser.add_argument(
        '--csv-file',
        help='Path to the CSV file containing media metadata (required if not using --entry-id)'
    )
    
    parser.add_argument(
        '--entry-id',
        help='Download a single asset by its entry ID (required if not using --csv-file)'
    )
    
    parser.add_argument(
        '--flavor',
        type=int,
        help='Download only a specific flavor ID (e.g., --flavor 1). If not specified, downloads all available flavors.'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default=DEFAULT_ARCHIVE_DIR,
        help=f'Output directory for downloaded files (default: {DEFAULT_ARCHIVE_DIR})'
    )
    
    parser.add_argument(
        '--max-retries',
        type=int,
        default=MAX_RETRIES,
        help=f'Maximum number of retry attempts for failed requests (default: {MAX_RETRIES})'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=TIMEOUT,
        help=f'Request timeout in seconds (default: {TIMEOUT})'
    )
    
    args = parser.parse_args()
    
    csv_file = args.csv_file
    entry_id = args.entry_id
    specific_flavor = args.flavor
    archive_dir = args.output_dir
    
    # Get retry settings from command line arguments
    max_retries = args.max_retries
    timeout = args.timeout
    
    # Validate arguments
    if not csv_file and not entry_id:
        print("Error: Either --csv-file or --entry-id must be specified.")
        sys.exit(1)
    
    if csv_file and entry_id:
        print("Error: Cannot specify both --csv-file and --entry-id. Use one or the other.")
        sys.exit(1)
    
    if csv_file and not os.path.exists(csv_file):
        print(f"Error: CSV file '{csv_file}' not found.")
        sys.exit(1)
    
    # Create archive directory
    os.makedirs(archive_dir, exist_ok=True)
    
    print(f"Starting StreamAMG archive process...")
    print(f"Archive directory: {os.path.abspath(archive_dir)}")
    if specific_flavor is not None:
        print(f"Flavor filter: Downloading only flavor ID {specific_flavor}")
    else:
        print(f"Flavor filter: Downloading all available flavors")
    print("=" * 60)
    
    try:
        # Get Kaltura session
        print("Getting authentication token...")
        ks_value = get_ks(max_retries, timeout)
        print("Authentication successful!")
        print("=" * 60)
        
        if entry_id:
            # Download single entry
            print(f"Fetching metadata for entry ID: {entry_id}")
            try:
                entry_data = get_single_entry_metadata(ks_value, entry_id, max_retries, timeout)
                print(f"\nProcessing single entry: {entry_data.get('name', 'Unknown')}")
                
                if archive_media_entry(ks_value, entry_data, archive_dir, specific_flavor, max_retries, timeout):
                    print(f"\n✓ Successfully archived entry {entry_id}")
                else:
                    print(f"\n✗ Failed to archive entry {entry_id}")
                    
            except Exception as e:
                print(f"Error processing entry {entry_id}: {e}")
                sys.exit(1)
                
        else:
            # Process CSV file
            with open(csv_file, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                total_entries = 0
                processed_entries = 0
                
                for row in reader:
                    total_entries += 1
                    print(f"\nProcessing entry {total_entries}: {row.get('name', 'Unknown')}")
                    
                    if archive_media_entry(ks_value, row, archive_dir, specific_flavor, max_retries, timeout):
                        processed_entries += 1
                    
                    # Add a small delay to be respectful to the server
                    time.sleep(1)
        
        print("\n" + "=" * 60)
        print(f"Archive complete!")
        
        if entry_id:
            print(f"Single entry processed: {entry_id}")
        else:
            print(f"Total entries processed: {processed_entries}/{total_entries}")
            
        if specific_flavor is not None:
            print(f"Flavor filter applied: Only flavor ID {specific_flavor} was downloaded")
        else:
            print(f"All available flavors were downloaded")
        print(f"Archive location: {os.path.abspath(archive_dir)}")
        
        # Create a summary file
        summary_file = os.path.join(archive_dir, "archive_summary.txt")
        with open(summary_file, 'w') as f:
            f.write(f"StreamAMG Archive Summary\n")
            f.write(f"========================\n")
            f.write(f"Archive Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            if entry_id:
                f.write(f"Entry ID: {entry_id}\n")
                f.write(f"Source: Single entry download\n")
            else:
                f.write(f"Total Entries: {total_entries}\n")
                f.write(f"Processed Entries: {processed_entries}\n")
                f.write(f"Source CSV: {csv_file}\n")
            if specific_flavor is not None:
                f.write(f"Flavor Filter: Only flavor ID {specific_flavor}\n")
            else:
                f.write(f"Flavor Filter: All flavors\n")
        
        print(f"Summary saved to: {summary_file}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 