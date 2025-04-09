# Digital Archiving Scripts

A comprehensive collection of scripts and tools for digital archiving, web crawling, and file management tasks.

## Directory Structure

### file-management/

Contains scripts for managing and organizing digital files:

- `empty_folder_finder.py`: Recursively scans directories to identify completely empty folders, with support for exclusion patterns and detailed logging
- `delete_files_and_empty_folders_from_list.py`: Utility for removing files and empty folders based on a provided list
- `checksum_duplicate_finder.py`: Identifies duplicate files using checksum comparison, supporting multiple algorithms (SHA1, MD5, SHA256) and parallel processing

### web crawling/

Contains tools for web archiving and crawling:

- `web_archive_validator.py`: Validates web archive files and checks their integrity
- `extract_qa.py`: Extracts and processes quality assurance data from web archives
- `wget_log_reader.py`: Analyzes and processes wget download logs
- `crt-scraper.py`: Web scraping utility for certificate transparency logs
- `browsertrix-crawler files and scripts/`: Configuration and scripts for browsertrix-crawler

### sitemap tools/

Contains utilities for working with sitemaps:

- `sitemap_monitor.py`: Monitors sitemap changes and updates
- `python_emailer.py`: Email notification system for sitemap changes
- `sitemap_xml_to_txt_or_html.py`: Converts XML sitemaps to plain text or HTML format

### pypreservica scripts/

Contains scripts for interacting with Preservica's API:

- `a_get_metadata.py`: Retrieves and processes metadata from Preservica assets (including fixity values)
- `b_delete_metadata.py`: Removes metadata from Preservica assets
- `c_add_metadata_from_csv.py`: Bulk metadata addition from CSV files
- `d_update_xip_from_csv.py`: Updates XIP metadata from CSV data
- `download_preservica_assets.py`: Downloads assets from Preservica

### video platform export scripts/

Contains tools for handling video platform exports and processing

### downloading items from internet archive/

Contains scripts for downloading and processing content from the Internet Archive

### archived scripts/

Contains older versions and deprecated scripts
