# wget crawling: `wget-crawl.sh` and `icaew-wget-crawl.sh`

These two scripts replace the manual wget workflow of copying long `wget`
commands by hand - instead you run one script and it handles setup,
retries, validation, and packaging for you.

- **`wget-crawl.sh`** - generic, works against any site
- **`icaew-wget-crawl.sh`** - hardcoded for icaew.com's specific three-leg
  crawl (icaew.com, subdomains, optional media)

Both live in the same folder and are self-contained - copy either one file
into an empty folder and it will fetch everything else it needs.

---

## Part 1: Quick start (for beginners)

### What you need before you start

Open a terminal. These need to already be installed (ask if you're not
sure): `wget`, `python3`, `zip`, `curl`. You do **not** need to install
anything else yourself - the scripts do that.

### Crawling a new site you haven't crawled before

1. Make a new empty folder and copy `wget-crawl.sh` into it.
2. Open a terminal in that folder.
3. Run one command. If the site has a sitemap (most do - check
   `https://the-site.com/sitemap.xml`):

   ```bash
   ./wget-crawl.sh --url https://www.example.com/ --sitemap https://www.example.com/sitemap.xml
   ```

   If the site needs a login first (rare for a first pass), also add
   `--cookies cookies.txt` (see "Cookies" below).

4. Wait. The script will print what it's doing as it goes - downloading
   helper files, building a list of pages, then crawling.
5. When it finishes, look for a file named like
   `20260708-example-com-wget.zip` in that folder. That's the finished,
   packaged result - ready for Preservica ingest.

That's it for the simple case. If something goes wrong, the script's error
messages are written to explain what's missing and how to fix it - read the
last few lines of output.

### Crawling icaew.com specifically

1. Copy `icaew-wget-crawl.sh` into a folder that also has a `cookies.txt`
   file (exported from your browser while logged into icaew.com - see the
   "Cookies" section below).
2. Run:

   ```bash
   ./icaew-wget-crawl.sh --sitemap https://www.icaew.com/sitemap_corporate.xml
   ```

   This builds `seedFile.txt` automatically the first time (you don't need
   to have one already - see "Building a seed file" below for how this
   works, or if you already have a curated `seedFile.txt` you can just run
   `./icaew-wget-crawl.sh` with no arguments and it'll be used as-is).

   Add `--with-media` if you also want the (much slower) media crawl:

   ```bash
   ./icaew-wget-crawl.sh --sitemap https://www.icaew.com/sitemap_corporate.xml --with-media
   ```

3. When it finishes, look for `20260708-ICAEW-com-logged-in-wget.zip`.

### Cookies

Both scripts need a `cookies.txt` file if the site requires being logged
in. The easiest way to get one: install the "Get cookies.txt LOCALLY"
browser extension, log into the site normally in your browser, click the
extension, export, and save the result as `cookies.txt` in your crawl
folder. `wget-crawl.sh` only uses cookies if you pass `--cookies
cookies.txt`; `icaew-wget-crawl.sh` always expects one (since icaew.com
needs a login).

### Building a seed file

A "seed file" is just a plain text file with one URL per line - the list of
pages to crawl. You don't have to write this by hand:

- If the site has a sitemap, pass `--sitemap https://the-site.com/sitemap.xml`
  and the script builds the file for you automatically.
- If you only want a handful of specific pages, use `--seed` instead, once
  per URL:

  ```bash
  ./wget-crawl.sh --url https://www.example.com/ \
      --seed https://www.example.com/page-one \
      --seed https://www.example.com/page-two
  ```

- Otherwise, point at an existing file with `--seed-file path/to/file.txt`.

### If it stops and prints an error

Read the last line or two of output - both scripts are written to explain
*what's* missing (a file, a program, network access) and what to do about
it, rather than just failing silently.

---

## Part 2: What these scripts actually do

### Overview of the pipeline

Both scripts follow the same shape:

1. **Check prerequisites** - `wget`, `python3`, `zip`, and (unless
   `--offline`) `curl`, must be installed.
2. **Fetch helper scripts if missing** - `wget_log_reader.py` (parses the
   wget log to work out which URLs succeeded/failed) and
   `sitemap_xml_to_txt_or_html.py` (turns a sitemap into a seed file) are
   downloaded, if not already sitting next to the script, from a pinned
   commit of
   [icaew-digital-archive/digital-archiving-scripts](https://github.com/icaew-digital-archive/digital-archiving-scripts)
   (currently `22db0b1a14`) rather than a floating branch. An existing
   local copy is never overwritten.
3. **Set up seeds** - in this order of priority: `--seed` URLs are appended
   into the seed file (deduplicated, never overwriting existing content);
   then, if the seed file is still missing, `--sitemap` is used to build one
   (this step creates a Python virtual environment (`venv/`) next to the
   script and installs the `requests` package, pinned to `2.34.2`, into it,
   since the sitemap script needs it - `wget_log_reader.py` needs no extra
   packages at all).
   For `icaew-wget-crawl.sh` specifically, this step also excludes
   `sprint-test-pages` and `active-members` URLs at the sitemap-conversion
   stage (matching the documented example), so they never end up in the
   seed file in the first place - without this, they'd be listed as
   expected, get correctly skipped during the crawl by the reject-regex,
   and then show up as false-positive "missing" entries in the QA report.
4. **Crawl with retries** - runs the actual `wget` command up to 3 times
   (configurable via `--retries`). Retries work by re-running the *exact
   same* command with `--no-clobber`: anything already saved to disk gets
   skipped, so each retry only spends time on URLs that are still missing or
   failed - not a full re-crawl.
5. **Score the result** - after each attempt, `wget_log_reader.py` compares
   the wget log against the seed file and reports matching / missing /
   non-200 / redirected URLs, writing four timestamped CSVs. The retry loop
   stops early once nothing is missing or non-200.
6. **Package the output** - the crawled site folder(s), the full log, the
   final CSV reports, and a copy of the seed file are zipped up together.
   `cookies.txt` is deliberately never included in the zip - it's a live
   session credential, not archival content.

### `wget-crawl.sh` specifics

- **Two crawl modes**: non-recursive (`-i seedfile`, the default - crawls
  exactly the URLs listed) or `--recursive` (crawls an entire domain
  starting from `--url`, no seed file needed at all).
- **`--label`** names the per-site workspace (`sites/<label>/`) where
  everything for that site lives - its seed file, log, CSVs, and crawl
  output, kept separate from any other site you crawl with the same script.
  Auto-derived from the site's hostname if you don't set it.
- **`--wait`** (default `1` second, randomized ±50%) throttles every single
  HTTP request wget makes - including each individual image/CSS/JS file a
  page pulls in, not just each page. A site's `robots.txt` `Crawl-delay`
  value is usually meant for page-to-page pacing, not per-asset pacing, so
  treat it as an upper bound rather than copying it in directly - a
  page-heavy site with `--wait` set too high can add hours to a crawl for
  little practical benefit.
- **`--domains`** / **`--reject-regex`** let you widen crawl scope (e.g. to
  a CDN subdomain) or exclude paths (e.g. logout links), matching wget's own
  `--domains`/`--reject-regex` flags directly.

### `icaew-wget-crawl.sh` specifics

Runs three separate legs in one invocation:

| Leg | Mode | Scope |
|---|---|---|
| `icaew-com` | non-recursive, seed-list driven | whatever's in `seedFile.txt` |
| `subdomains` | recursive | `regulation.icaew.com` in full; `train`/`volunteer.icaew.com` restricted to `/blog` paths |
| `media` (optional, `--with-media`) | recursive | all of `icaew.com`, discovering linked media not in the seed list - much larger and slower |

Each leg gets its own reject-regex (excluding logout pages, and for the main
leg, membership/active-members pages too) and its own log file. The
`subdomains` leg has no seed file to score against (there's no canonical
URL list for those subdomains yet), so it runs its retries but skips the
CSV scoring step - `SUBDOMAINS_URL_LIST` in the script can be pointed at one
if you build it (e.g. with `sitemap_xml_to_txt_or_html.py` against each
subdomain's own sitemap).

`--wait` defaults to `0.5` here rather than `1` - icaew.com's `robots.txt`
doesn't request any delay at all, so this is discretionary courtesy rather
than a requirement, and at the icaew-com leg's scale (~29,000 requests) even
small increases add up: every extra `0.1` seconds here is roughly 48 more
minutes.

### The GitHub download fallback, in more detail

`wget_log_reader.py` and `sitemap_xml_to_txt_or_html.py` are pulled from a
pinned commit of the `digital-archiving-scripts` repo
(`22db0b1a14dbcfa64231931ddec12dbad7672136`) if not found locally, rather
than the floating `main` branch. This used to point at `main` directly,
which meant a brand-new checkout could silently get a version *behind*
local fixes made during development of these scripts (this actually
happened - `main` was missing a memory-safety fix to
`web_archive_validator.py`, on the browsertrix side, until PR #48 merged it
upstream on 2026-07-22). Pinning to a specific commit means upstream
changes - good or bad - no longer affect these scripts until someone
deliberately updates the pinned SHA and re-verifies against the local
copies. Use `--offline` to disable the fallback entirely and fail fast
instead if a script is missing.

### Flag reference

Run `head -35 wget-crawl.sh` or `head -25 icaew-wget-crawl.sh` at any time
to see the full up-to-date flag list in the script's own header comment -
that's the authoritative reference, kept in sync with the code itself
rather than duplicated here where it could drift out of date.
