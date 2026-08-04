# web crawling

Scripts for processing, validating, and analysing web archive files (WARC/WACZ) and crawl logs.

---

## `web_archive_validator.py`

Validate a list of target URLs against crawl data in WARC or WACZ archive files. Produces three output CSVs: `matching_urls.csv`, `missing_urls.csv`, and `non_200_urls.csv`.

```bash
python web_archive_validator.py <url_list.txt> <archive.warc> [<archive2>...] [options]
```

| Argument | Description |
|---|---|
| `url_list` | File with target URLs, one per line (positional) |
| `archive_files` | WARC/WACZ files or directories to search (positional, repeatable) |
| `--output-dir` | Directory for output CSVs (default: current directory) |
| `--verbose` | Enable verbose output |
| `--log-file` | Log file path |

---

## `warc_processor.py`

Combine WARC files and convert to WACZ format with optional full-text indexing.

```bash
python warc_processor.py -i <input_dir> -o <output.wacz> [options]
```

| Argument | Description |
|---|---|
| `-i` / `--input` | Input directory or WARC file (required) |
| `-o` / `--output` | Output WACZ file path (required) |
| `-v` / `--verbose` | Verbose logging |
| `--debug` | Debug logging |
| `--keep-temp` | Keep the intermediate combined WARC file |
| `--detect-pages` | Enable/disable page detection (default: enabled) |
| `--text-index` | Generate a full-text search index |

---

## `combine_warcs.py`

Combine multiple WARC (or `.warc.gz`) files into a single WARC file.

```bash
python combine_warcs.py --input <dir_or_files> --output <combined.warc> [--verbose]
```

---

## `extract_qa.py`

Extract QA data from a WACZ web archive file to CSV.

```bash
python extract_qa.py <archive.wacz> [output.csv] [--filter-hash-urls]
```

| Argument | Description |
|---|---|
| `input.wacz` | Input WACZ file (positional) |
| `output.csv` | Output CSV path (default: `<input>.csv`) |
| `--filter-hash-urls` | Exclude URLs with hash fragments (`#`) |

Exit codes: `0` success, `1` file not found, `2` invalid WACZ, `3` no info WARC files found.

---

## `wget_log_reader.py`

Analyse a wget log file and compare crawled URLs against the original URL list. Produces timestamped CSV reports: `matching_urls_*.csv`, `missing_urls_*.csv`, `non_200_urls_*.csv`.

```bash
python wget_log_reader.py <log_file> <url_list>
```

---

## `fix_multiwacz.py`

Rebuild a spec-compliant WACZ from a Browsertrix multi-wacz wrapper (or a set of already-unwrapped shard files).

```bash
python fix_multiwacz.py --input <broken.wacz> [<shard2.wacz>...] (--output <fixed.wacz> | --replace-input) [options]
```

| Argument | Description |
|---|---|
| `--input` / `-i` | One or more input `.wacz` files: a multi-wacz wrapper and/or individual shard files (required) |
| `--output` / `-o` | Output path for the rebuilt WACZ (required unless `--replace-input`) |
| `--replace-input` | Back up the single input file (to `<name>.broken-multiwacz.bak`) and overwrite it in place |
| `--hash-type` | Hash algorithm for `datapackage.json`: `sha256` or `md5` (default: `sha256`) |
| `--title` / `--desc` / `--url` | Collection metadata to record in `datapackage.json` |
| `--keep-temp` | Keep the temporary working directory for inspection |
| `--verbose` / `-v` | Enable verbose logging |

---

## `crt-scraper.py`

Fetch unique SSL/TLS certificate identities for a domain from [crt.sh](https://crt.sh). Useful for enumerating subdomains before a crawl.

```bash
python crt-scraper.py <domain> [--output <file.txt>] [--retries N]
```

| Argument | Description |
|---|---|
| `domain` | Domain to query, e.g. `icaew.com` (positional) |
| `--output` | Output text file (default: `unique_matching_identities.txt`) |
| `--retries` | Max retry attempts on rate-limit errors (default: 3) |
