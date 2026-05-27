import os
import argparse

def extract_entry_id_from_url(url):
    """Extract the entry ID from the URL."""
    try:
        return url.split("/entryId/")[1].split("/")[0]
    except IndexError:
        return None

def extract_entry_id_from_filename(filename):
    """Extract the entry ID from the filename."""
    try:
        # Corrected logic to handle '0_abc123xyz' format
        return filename.split('_')[0] + '_' + filename.split('_')[1]
    except IndexError:
        return None

def get_video_files(folder_path):
    """Get the list of video files in the specified folder."""
    return [f for f in os.listdir(folder_path) if f.endswith('.mp4')]

def find_missing_videos(url_file, folder_path):
    """Compare URLs with video files to find missing ones."""
    # Read URLs from the input file
    with open(url_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    # Parse entry IDs from the URLs
    expected_entry_ids = {extract_entry_id_from_url(url) for url in urls if extract_entry_id_from_url(url)}
    
    # Get the video files in the folder
    video_files = get_video_files(folder_path)
    
    # Extract entry IDs from the video filenames
    downloaded_entry_ids = {extract_entry_id_from_filename(file) for file in video_files}
    
    # Find missing entry IDs
    missing_entry_ids = expected_entry_ids - downloaded_entry_ids
    
    # Map missing entry IDs back to URLs
    missing_urls = [url for url in urls if extract_entry_id_from_url(url) in missing_entry_ids]
    
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
