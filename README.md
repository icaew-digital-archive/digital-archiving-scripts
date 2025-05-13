# digital-archiving-scripts

A collection of scripts to help with various digital archiving tasks.

## Main Scripts

### Web Crawling and Validation
- `web crawling/wget_log_reader.py`: Script for reading and analyzing wget log files
- `web crawling/web_archive_validator.py`: Validates web archive files
- `web crawling/crt-scraper.py`: Web scraping utility
- `web crawling/extract_qa.py`: QA extraction utility for web archives

### Preservica Integration
- `pypreservica scripts/`: Contains scripts for interacting with Preservica's API:
  - `a_get_metadata.py`: Retrieves metadata from Preservica
  - `b_delete_metadata.py`: Deletes metadata from Preservica assets
  - `c_add_metadata_from_csv.py`: Adds metadata from CSV files
  - `d_update_xip_from_csv.py`: Updates XIP metadata from CSV
  - `download_preservica_assets.py`: Downloads assets from Preservica

### Other Utilities
- `semaphore-helper.py`: Uses Semaphore's CLSClient to auto-classify documents and sorts by topic score

## Directory Structure

### archived scripts/
Contains older or archived versions of scripts

### browsertrix-crawler files and scripts/
Contains scripts and configurations for browsertrix-crawler

### downloading items from internet archive/
Contains scripts for downloading and processing content from the Internet Archive

### file-management/
Contains scripts for managing and organizing files

### sitemap tools/
Contains tools for working with sitemaps, including:
- Script to produce a plain list of URLs from an XML sitemap (outputs to .txt, .html, or terminal)
