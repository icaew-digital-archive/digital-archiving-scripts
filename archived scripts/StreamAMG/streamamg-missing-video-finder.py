import os
import argparse

def parse_entry_id_from_url(url):
    """Extract the entry ID from the URL."""
    try:
        return url.split("/entryId/")[1].split("/")[0]
    except IndexError:
        return None

def get_all_files(folder_path):
    """Get the list of all files in the specified folder."""
    return [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

def find_missing_videos(url_file, folder_path):
    """Compare URLs with video files to find missing ones."""
    # Read URLs from the input file
    with open(url_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    # Parse entry IDs from the URLs
    expected_entry_ids = {parse_entry_id_from_url(url) for url in urls if parse_entry_id_from_url(url)}
    
    # Get all files in the folder
    all_files = get_all_files(folder_path)
    
    # Match entry IDs against filenames
    downloaded_entry_ids = set()
    for filename in all_files:
        # Look for entryId in the filename
        for entry_id in expected_entry_ids:
            if entry_id and entry_id in filename:
                downloaded_entry_ids.add(entry_id)
    
    # Find missing entry IDs
    missing_entry_ids = expected_entry_ids - downloaded_entry_ids
    
    # Map missing entry IDs back to URLs
    missing_urls = [url for url in urls if parse_entry_id_from_url(url) in missing_entry_ids]
    
    return missing_urls

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Check missing video downloads.")
    parser.add_argument("url_file", help="Path to the text file containing video URLs.")
    parser.add_argument("folder_path", help="Path to the folder containing downloaded videos.")
    args = parser.parse_args()

    # Find missing videos
    missing_videos = find_missing_videos(args.url_file, args.folder_path)
    
    # Output the results
    if missing_videos:
        print("Missing video URLs:")
        for url in missing_videos:
            print(url)
    else:
        print("All videos are downloaded.")

if __name__ == "__main__":
    main()

