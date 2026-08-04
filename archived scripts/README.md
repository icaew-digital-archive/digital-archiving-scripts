# archived scripts

Retired, superseded, and work-in-progress scripts. Nothing here is guaranteed to run — some are early drafts of scripts now maintained elsewhere in the repo (e.g. `pypreservica scripts/`, `web crawling/`), some are one-off/rough tools, and a few are known-broken. Kept for reference only.

---

## Preservica metadata (superseded by `pypreservica scripts/`)

| File | Purpose |
|---|---|
| `a_get_metadata copy.py` | Earlier draft of `a_get_metadata.py` — export metadata to CSV from Preservica |
| `b_csv_to_opex_xml.py` | Convert CSV data to OPEX XML format |
| `b_delete_metadata_from_csv.py` | Delete metadata for assets/folders listed in a CSV file |
| `b_delete_metadata_from_parent.py` | Delete metadata from Preservica assets |
| `combined.py` / `combined-pre-template.py` | Earlier combined export-metadata-and-checksums script |
| `csv_validator.py` | Validate CSV metadata files against ICAEW formatting rules |
| `get_child_assets_to_csv.py` | List assets/folders under a folder reference; produces a CSV template for the `add`/`update`-from-CSV scripts |
| `get_local_asset_checksum_values.py` | Generate checksum values for local files |
| `get_preservica_asset_checksum_values.py` | Obtain checksum values from child assets in Preservica |
| `ingest-NOT-WORKING-NEEDS-BUCKET.py` | Upload files/folders to Preservica — **known broken**, needs a bucket |
| `metadata_add_testing.py` | Test script for adding metadata to a single Preservica asset |
| `metadata_extraction_wrapper.py` | Orchestrates download → convert → extract-to-CSV metadata workflow |
| `preservica_metadata_retrieval.py` | Rough script to pull the Title field from the metadata schema |
| `preservica_report.py` | Report on assets below a folder reference (path, title, reference, type, security tag, DC title) to CSV |
| `preservica_report_old.py` | Earlier, rougher version of the above |
| `preservica-archive-it-checksum-cross-reference.py` | Cross-references Archive-It (py-wasapi-client) MD5 manifests against Preservica checksums to find WARCs missing from Preservica |
| `report.py` | Archive growth / file-type / total-size report from Preservica, with CSV output and visualisations |
| `update_metadata_from_csv.py` | Update metadata on existing Preservica assets/folders from a CSV |
| `xml_to_csv.py` | Convert an XML file to CSV |

---

## Web archiving / crawl-log tools (superseded by `web crawling/`)

| File | Purpose |
|---|---|
| `jsonlreader.py` | Read and inspect JSONL log files produced by Browsertrix |
| `pages_json_log_validate.py` | Validate a Browsertrix `pages.json` crawl log |
| `wacz_validator.py` | Validate URLs against crawl data in a WACZ file |
| `warc-reader.py` / `warc_reader.ipynb` | Read a folder of WARC files and cross-reference content against a URL list; uses BS4 to search HTML for specific elements |
| `old browsertrix crawler driver/defaultDriver.js` | Old custom Browsertrix crawler driver script |

---

## Standalone web tools

| Path | Purpose |
|---|---|
| `browser_auto_open/browser_auto_open.py` | Opens a list of URLs in Chrome/Firefox — built for use with pywb record mode |
| `get_html/get_html.py` | Visits a list of URLs and saves HTML content to a dict, output as JSON/pickle/terminal |
| `os_path_to_url/os_path_to_url.py` | Converts a directory of files to "pseudo" URLs — for rebuilding URL paths from a downloaded/extracted zip |
| `web_scrape.ipynb` | Notebook that scrapes HTML content from `get_html.py`'s pickle output |
| `list_to_html_list.py` | Converts a `.txt` list of URLs to an HTML unordered list of links |

---

## Metadata / ingest formatting

| Path | Purpose |
|---|---|
| `excel2dc/excel2dc.py` (+ `template.xlsx`) | Reads an Excel spreadsheet, outputs `.metadata` XML files conforming to Preservica's metadata input |
| `XML metadata validation/xml_metadata_validation.py` (+ `oai_dc.xsd`) | Finds malformed XML `.metadata` files before Preservica ingest |
| `opex-scripts/a_files_to_csv.py` | List files in a directory and calculate checksums |
| `opex-scripts/b_csv_to_opex_xml.py` | Convert CSV data to OPEX XML format |
| `opex-scripts/c_folders_of_files_to_folder_opex_xml.py` | Generate a folder-level OPEX XML file from files in a folder |
| `opex-scripts/csv_file_rename.py` | Rename files based on a CSV mapping |
| `opex-scripts/semaphore-subject-import.py` | Process CSVs for Semaphore subject import |
| `opex-scripts/templates/` | OPEX XML templates used by the scripts above |
| `semaphore-helper.py` | Process files with Semaphore's CLSClient |

---

## StreamAMG / video archiving

Scripts for archiving video assets and captions from the StreamAMG platform.

| Path | Purpose |
|---|---|
| `StreamAMG/archive_streamamg_assets.py` | Download StreamAMG video assets |
| `StreamAMG/collect_streamamg_urls.py` | Collect StreamAMG URLs, output to CSV without downloading |
| `StreamAMG/streamamg_api_media_list_to_csv.py` | Dump the StreamAMG API media list to CSV |
| `StreamAMG/check_missing_videos.py` / `streamamg-missing-video-finder.py` | Check for/find video downloads missing against the media list |
| `StreamAMG/download_captions.py` | Download StreamAMG caption files |
| `StreamAMG/template_url_streamamg_download.py` | Template script for building StreamAMG download URLs from a list of entry IDs |
| `StreamAMG/test_encoding.py` | Scratch script for identifying correct response encoding from the StreamAMG API |
| `StreamAMG/python_scripts/` | Older duplicate copies of two of the scripts above |
| `StreamAMG/video_ids.txt` | Entry ID list used by the download scripts |
| `streamamg_archive/` | Sample output from a StreamAMG archive run (downloaded videos, `archive_summary.txt`, `topic-scrape.js`) |

**Note:** `StreamAMG/download_captions.py` and `StreamAMG/streamamg_api_media_list_to_csv.py` have the StreamAMG API secret and partner ID hardcoded in the file, and `StreamAMG/.env` is committed alongside them — treat these as compromised credentials rather than copying the pattern into new scripts.

---

## Misc

| Path | Purpose |
|---|---|
| `pdf decrypt/pdf_decrypt.py` | Decrypt a folder of PDFs using `pikepdf` |
| `unzip-nested-zip-files-and-remove-original-zip-files` | Bash one-liner: recursively unzips nested `.zip` files in place and deletes the originals |
| `whisperx_pypreservica.ipynb` | Earlier draft of the root-level WhisperX transcription notebook |
| `zip_srt_files.ipynb` | Batch-zip SRT subtitle files |
