# sitemap tools

Utilities for monitoring XML sitemaps and extracting URLs from them.

---

## `sitemap_monitor.py`

Monitor one or more XML sitemaps for changes. On first run, saves a baseline snapshot (`sitemap_memory.json`). On subsequent runs, compares against the snapshot and reports new and removed URLs.

```bash
python sitemap_monitor.py --sitemap <URL> [<URL>...] [options]
```

| Argument | Description |
|---|---|
| `--sitemap` | One or more sitemap URLs to monitor (required) |
| `-n` / `--show-new` | Print new URLs |
| `-r` / `--show-removed` | Print removed URLs |
| `--filter-all KEYWORD...` | Filter new URLs — all keywords must be present |
| `--filter-any KEYWORD...` | Filter new URLs — at least one keyword must be present |

**First run** initialises `sitemap_memory.json` and exits. Run again to see changes.

---

## `sitemap_xml_to_txt_or_html.py`

Extract URLs from XML sitemap files or URLs; optionally filter and output as `.txt` or `.html`.

```bash
python sitemap_xml_to_txt_or_html.py <sitemap> [<sitemap>...] [options]
```

| Argument | Description |
|---|---|
| `sitemap_input` | Sitemap file(s) or URL(s) (positional) |
| `--contains_strings` | Keep only URLs containing any of these strings (OR logic) |
| `--exclude_strings` | Remove URLs containing any of these strings |
| `--to_file` | Save output to a `.txt` file |
| `--to_html` | Save output to an `.html` file |
| `--deduplicate` | Remove duplicate URLs |

Without `--to_file` or `--to_html`, URLs are printed to stdout.

---

## `python_emailer.py`

Calls `sitemap_monitor.py` and emails the output. Configuration (email credentials, sitemap URLs, script path) is set directly in the file. Intended to be run on a schedule (e.g. cron).
