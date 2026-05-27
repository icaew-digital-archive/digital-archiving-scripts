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
| [`csv-tools/`](csv-tools/README.md) | Merge and score metadata CSVs |
| [`downloading items from internet archive/`](downloading%20items%20from%20internet%20archive/README.md) | Convert CDX JSON to wget-compatible Wayback Machine URL lists |
| [`file-management/`](file-management/README.md) | Checksum deduplication, bulk deletion, empty folder removal |
| [`pypreservica scripts/`](pypreservica%20scripts/README.md) | Full Preservica API workflow: export, delete, add, and update metadata; download and move assets |
| [`sitemap tools/`](sitemap%20tools/README.md) | Monitor sitemaps for changes; extract URL lists from XML sitemaps |
| [`video platform export scripts/`](video%20platform%20export%20scripts/README.md) | Batch video downloads; exploratory Vimeo and YouTube API scripts |
| [`web crawling/`](web%20crawling/README.md) | Process and validate WARC/WACZ archives; analyse wget logs; scrape crt.sh |
| [`browsertrix-crawler files and scripts/`](browsertrix-crawler%20files%20and%20scripts/README.md) | Custom JS behaviours for Browsertrix Crawler; crawl log helpers |

---

## Root-level scripts

### `generate_folder_descriptions.py`

Generate simple human-readable descriptions for ICAEW Digital Archive folders from a Preservica CSV export. Adds a `description` column and writes a companion `.txt` file.

```bash
python generate_folder_descriptions.py <export.csv> [--output output.csv]
```

### `generate_meaningful_descriptions.py`

Like the above but uses a built-in knowledge base of ICAEW folder types (AGM Papers, Business Confidence Monitor, Technical Releases, etc.) to write richer, contextual descriptions.

```bash
python generate_meaningful_descriptions.py <export.csv> [--output output.csv]
```

### `metadata_extraction_wrapper.py`

Orchestrate a full metadata extraction workflow: download Preservica assets → convert documents → extract metadata to CSV.

```bash
python metadata_extraction_wrapper.py \
    [--preservica-folder-ref <ID>] \
    [--output-dir <dir>] \
    [--csv-file <output.csv>] \
    [--skip-download]
```

| Argument | Description |
|---|---|
| `--preservica-folder-ref` | Preservica folder ID to download |
| `--output-dir` | Working directory for downloads and processing |
| `--csv-file` | Output CSV filename |
| `--skip-download` | Skip the download step; work with files already on disk |

---

## Root-level notebooks

| Notebook | Purpose |
|---|---|
| `whisperx_pypreservica_parallelised.ipynb` | Transcribe audio/video assets from Preservica using WhisperX |
| `zip_srt_files.ipynb` | Batch-zip SRT subtitle files |
