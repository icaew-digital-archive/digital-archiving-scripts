import argparse
import json
import os
import sys
import time
from pathlib import Path
from xml.etree import ElementTree
import requests

def main():
    parser = argparse.ArgumentParser(description='Monitor changes to Sitemap')
    parser.add_argument('--sitemap', nargs='+', required=True, help='Sitemap URLs to monitor')
    parser.add_argument('-or', '--outputremoved', action='store_true', help='Show removed URLs')
    parser.add_argument('-on', '--outputnew', action='store_true', help='Show new URLs')
    parser.add_argument('-fa', '--filterand', nargs='*', help='Filter new URLs - all keywords must be present')
    parser.add_argument('-fo', '--filteror', nargs='*', help='Filter new URLs - at least one keyword must be present')
    args = parser.parse_args()

    sitemap_memory = "./sitemap_memory.json"
    latest_sitemap_urls = fetch_sitemap_urls(args.sitemap)
    previous_sitemap_urls = load_or_initialize_sitemap_memory(sitemap_memory, latest_sitemap_urls)

    new_urls, removed_urls = compare_sitemaps(latest_sitemap_urls, previous_sitemap_urls)

    display_sitemap_summary(sitemap_memory, latest_sitemap_urls, previous_sitemap_urls, new_urls, removed_urls)

    if args.outputremoved:
        print("Removed URLs:")
        print("\n".join(removed_urls) if removed_urls else "None")

    if args.outputnew:
        print("New URLs:")
        print("\n".join(new_urls) if new_urls else "None")

    if args.filterand or args.filteror:
        filter_words = args.filterand if args.filterand else args.filteror
        filtered_urls = filter_urls(new_urls, filter_words, bool(args.filterand))
        print('Filtered new URLs:', len(filtered_urls))
        print("\n".join(filtered_urls) if filtered_urls else "None")

    if new_urls or removed_urls:
        save_sitemap_memory(sitemap_memory, latest_sitemap_urls)
        print("Sitemap memory updated.")

def fetch_sitemap_urls(sitemap_urls):
    """Fetch URLs from the provided sitemap links, handling XML namespaces."""
    all_urls = []
    for sitemap in sitemap_urls:
        try:
            response = requests.get(sitemap)
            response.raise_for_status()
            tree = ElementTree.fromstring(response.content)
            
            # Handle XML namespaces
            namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = [url_element.text for url_element in tree.findall(".//ns:loc", namespaces)]
            
            if not urls:
                print(f"No URLs found in sitemap: {sitemap}")
            else:
                print(f"Fetched {len(urls)} URLs from sitemap: {sitemap}")
            
            all_urls.extend(urls)
        except (requests.RequestException, ElementTree.ParseError) as e:
            print(f"Error fetching or parsing sitemap {sitemap}: {e}")
            sys.exit(1)
    return all_urls



def load_or_initialize_sitemap_memory(sitemap_memory, latest_sitemap_urls):
    """Load previous sitemap memory or initialize it if not found."""
    if Path(sitemap_memory).exists():
        with open(sitemap_memory, 'r') as f:
            return json.load(f)
    
    print("No previous sitemap memory found. Initializing with the latest sitemap.")
    save_sitemap_memory(sitemap_memory, latest_sitemap_urls)
    print("Sitemap memory initialized.")
    sys.exit(0)

def compare_sitemaps(latest_sitemap_urls, previous_sitemap_urls):
    """Compare two sitemap URL lists and return new and removed URLs."""
    latest_set, previous_set = set(latest_sitemap_urls), set(previous_sitemap_urls)
    return list(latest_set - previous_set), list(previous_set - latest_set)

def filter_urls(urls, filter_words, require_all):
    """Filter URLs based on keywords."""
    if require_all:
        return [url for url in urls if all(word in url for word in filter_words)]
    return [url for url in urls if any(word in url for word in filter_words)]

def display_sitemap_summary(memory_path, latest_urls, previous_urls, new_urls, removed_urls):
    """Display summary of sitemap changes."""
    print(f"Sitemap last modified: {get_file_modification_time(memory_path)}")
    print(f"Current sitemap URL count: {len(latest_urls)}")
    print(f"Saved sitemap URL count: {len(previous_urls)}")
    print(f"New URLs: {len(new_urls)}")
    print(f"Removed URLs: {len(removed_urls)}")

def get_file_modification_time(file_path):
    """Return the last modification time of a file."""
    return time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(file_path)))

def save_sitemap_memory(sitemap_memory, urls):
    """Save sitemap URLs to a JSON file."""
    with open(sitemap_memory, 'w') as f:
        json.dump(urls, f, indent=4)

if __name__ == '__main__':
    main()
