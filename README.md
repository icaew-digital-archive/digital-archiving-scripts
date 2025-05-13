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
  - `get_local_asset_checksum_values.py`: Generates checksums for local assets
  - `get_preservica_asset_checksum_values.py`: Retrieves checksums from Preservica
  - `metadata_add_testing.py`: Testing utility for metadata operations
  - `report.py`: Reporting utility for Preservica assets
  - Additional scripts in `custom-metadata-test-WIP/` and `pypreservica-video-package-ingest/`

### Other Utilities
- `semaphore-helper.py`: Uses Semaphore's CLSClient to auto-classify documents and sorts by topic score

## Directory Structure

### archived scripts/
Contains older or archived versions of scripts

### browsertrix-crawler files and scripts/
Contains scripts and configurations for browsertrix-crawler

### csclient/
Contains scripts related to the CSClient functionality

### downloading items from internet archive/
Contains scripts for downloading and processing content from the Internet Archive

### file-management/
Contains scripts for managing and organizing digital files

### opex-scripts/
Contains scripts for handling OPEX (Open Preservation Exchange) operations

### sitemap tools/
Contains tools for working with sitemaps, including:
- Script to produce a plain list of URLs from an XML sitemap (outputs to .txt, .html, or terminal)

### test and archive files/
Contains test files and archived content

### video platform export scripts/
Scripts for handling video platform exports

## Environment Setup
- Uses Python virtual environment (venv)
- Environment variables stored in `.env`
- `.gitignore` configured for Python projects

## Notes
- Some scripts are marked as WIP (Work in Progress) and may be under development
- Check individual script directories for specific README files with detailed usage instructions
