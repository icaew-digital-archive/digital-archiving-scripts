# downloading items from internet archive

Utilities for downloading content from the Internet Archive Wayback Machine.

---

## `ia_cdx_json_to_txt.py`

Convert a CDX Internet Archive API JSON file to a plain-text list of wget-compatible Wayback Machine URLs. Deduplicates by digest hash (more reliable than the CDX API's own collapse option).

**Step 1 — fetch the CDX JSON:**
```bash
wget 'http://web.archive.org/cdx/search/cdx?url=example.com&matchType=domain&output=json' -O cdx.json
```

Add filters as needed — e.g. media/document files only:
```bash
wget 'http://web.archive.org/cdx/search/cdx?url=example.com&matchType=domain&output=json&filter=mimetype:application.*' -O cdx.json
```

**Step 2 — convert to URL list:**
```bash
python ia_cdx_json_to_txt.py cdx.json [--output cdx.txt]
```

**Step 3 — download with wget:**
```bash
wget -i cdx.txt                               # media / binary files
wget --mirror --convert-links --adjust-extension --page-requisites --no-parent --restrict-file-names=windows -nH -i cdx.txt  # full site mirror
```

| Argument | Description |
|---|---|
| `json_file` | CDX JSON file from the IA API (positional) |
| `--output` | Output text file (default: `cdx.txt`) |
| `--display-flag` | Wayback Machine display flag (default: `if_`) |
| `--no-dedup` | Include URLs with duplicate digest hashes |

### Display flags

The `if_` flag retrieves the raw archived file without Wayback Machine toolbar injection. See [Wayback Machine display flags](https://en.wikipedia.org/wiki/Help:Using_the_Wayback_Machine#Specific_archive_copy) for other options.

### CDX API reference

Full documentation: <https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server>
