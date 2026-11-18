# sitemap tools

Utilities for monitoring XML sitemaps and extracting URLs from them. Requires `requests` (`pip install requests`).

---

## `sitemap_monitor.py`

Monitor one or more XML sitemaps for changes. On first run, saves a baseline snapshot (`sitemap_memory.json`, in the current directory). On subsequent runs, compares against the snapshot and reports new and removed URLs.

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
| `--to_file PATH` | Save output to a `.txt` file |
| `--to_html PATH` | Save output to an `.html` file |
| `--deduplicate` | Remove duplicate URLs |

Without `--to_file` or `--to_html`, URLs are printed to stdout.

---

## `python_emailer.py`

Calls `sitemap_monitor.py` and emails the output via the Gmail API (DigitalOcean blocks SMTP). Configuration (`from_email`, `to_email`, `cc_emails`, sitemap URLs in `script_args`) is set directly in the file. Intended to be run on a schedule with cron.

### Gmail API (one-off)

In [Google Cloud Console](https://console.cloud.google.com), signed in as the sending account:

1. Create a project and enable the **Gmail API**.
2. **Branding**: fill in app name, support email, home page and privacy policy URLs.
3. **Audience**: External → **Publish app** (Testing mode expires tokens after 7 days).
4. **Clients**: Create client → **Desktop app** → download as `client_secret.json`.

Then, on a machine with a browser:

```bash
python3 gmail_authorise.py client_secret.json   # creates gmail_token.json
```

### Deploy to a droplet

```bash
./deploy.sh root@DROPLET_IP              # daily 08:00 UTC
./deploy.sh root@DROPLET_IP "0 8 * * 1"  # or a custom cron schedule
```

Copies the scripts and token to `~/sitemap-monitor/`, installs `requests` in a venv and adds the cron job. Safe to re-run after any change.

Test it:

```bash
ssh root@DROPLET_IP 'cd ~/sitemap-monitor && venv/bin/python python_emailer.py'
```

The first run only saves a baseline; new URLs are reported from the next run.

### Troubleshooting

- **Logs:** `~/sitemap-monitor/cron.log` on the droplet.
- **Token error (400 from oauth2.googleapis.com):** rerun `gmail_authorise.py`, then `deploy.sh`.
- **Wrong sender:** the token was approved by another Google account; reauthorise with the right one.

Never commit `client_secret.json` or `gmail_token.json`.
