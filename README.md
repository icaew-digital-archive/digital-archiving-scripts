# digital-archiving-scripts

A collection of Python scripts for digital archiving tasks — Preservica integration, web crawling and archive validation, video platform exports, file management, and sitemap monitoring.

---

## Setup

Most scripts share a common set of dependencies. Install from the repo root:

```bash
pip install -r requirements.txt
```

**Preservica scripts** also require a `.env` file in the directory you run them from — see [`pypreservica scripts/README.md`](pypreservica%20scripts/README.md).

---

## Directories

| Directory | Contents |
|---|---|
| [`archived scripts/`](archived%20scripts/README.md) | Retired and work-in-progress scripts, superseded by scripts elsewhere in the repo |
| [`csv-tools/`](csv-tools/README.md) | Merge and score metadata CSVs |
| [`downloading items from internet archive/`](downloading%20items%20from%20internet%20archive/README.md) | Convert CDX JSON to wget-compatible Wayback Machine URL lists |
| [`file-management/`](file-management/README.md) | Checksum deduplication, bulk deletion, empty folder removal |
| [`pypreservica scripts/`](pypreservica%20scripts/README.md) | Full Preservica API workflow: export, delete, add, and update metadata; download and move assets |
| [`sitemap tools/`](sitemap%20tools/README.md) | Monitor sitemaps for changes; extract URL lists from XML sitemaps |
| [`thumbnails/`](thumbnails/README.md) | Scheduled job that replaces inherited folder thumbnails with a standard folder icon |
| [`video platform export scripts/`](video%20platform%20export%20scripts/README.md) | Batch video downloads; exploratory Vimeo and YouTube API scripts |
| [`web crawling/`](web%20crawling/README.md) | Process and validate WARC/WACZ archives; analyse wget logs; scrape crt.sh |
| [`web crawling/browsertrix-crawler files and scripts/`](web%20crawling/browsertrix-crawler%20files%20and%20scripts/README.md) | Custom JS behaviours for Browsertrix Crawler; crawl log helpers |

---

## Root-level notebooks

| Notebook | Purpose |
|---|---|
| `whisperx_pypreservica_parallelised.ipynb` | Transcribe audio/video assets from Preservica using WhisperX |

`generate_folder_descriptions.py`, `generate_meaningful_descriptions.py`, and `metadata_extraction_wrapper.py` were previously root-level scripts — they now live in [`archived scripts/`](archived%20scripts/README.md).
