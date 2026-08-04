# Browsertrix crawling: `browsertrix-crawl.sh`, `icaew-browsertrix-crawl.sh`, and `icaew-template-browsertrix-crawl.sh`

These scripts replace the manual Browsertrix Crawler workflow of running
several long `docker` commands by hand and separately converting WARC
files to WACZ - instead you run one script.

- **`browsertrix-crawl.sh`** - generic, works against any site ("simple
  domain crawl": crawls everything in a seed file's domain(s))
- **`icaew-browsertrix-crawl.sh`** - hardcoded for icaew.com's actual custom
  crawl scope (icaew.com + cdn/regulation subdomains, train/volunteer
  restricted to blog/article paths) and its custom behaviour script - full
  archival crawl, with retries/validation/patch crawl/QA reporting
- **`icaew-template-browsertrix-crawl.sh`** - a much lighter-weight sibling for quickly
  testing how specific page URLs render (e.g. a new page design) before
  committing to a full crawl. No discovery, no validation, no patch crawl -
  see "Template crawls" below.

All three live in the same folder and are self-contained - copy any one
file into an empty folder and it will fetch everything else it needs (the
template script needs nothing beyond Docker itself).

---

## Part 1: Quick start (for beginners)

### What you need before you start

Open a terminal. `docker`, `python3`, `zip`, and `curl` need to already be
installed. You do **not** need to install anything else yourself, and you
do **not** need to already have the Browsertrix Docker image - the script
pulls it automatically the first time.

### The one thing that can't be automated: the browser profile

Most crawls need a "browser profile" - a saved browser session (cookies,
logged-in state, "accept all cookies" already clicked) that Browsertrix
replays during the crawl. Creating one requires an actual human clicking
through a real browser window, so it can't be scripted.

The first time you run either script, if no profile exists yet, it will
stop and print the exact command to create one, something like:

```
docker run -p 6080:6080 -p 9223:9223 \
    -v /path/to/crawls/profiles:/crawls/profiles/ \
    -it webrecorder/browsertrix-crawler:1.5.11 \
    create-login-profile --url "https://www.example.com/"
```

Run that command yourself, then open **`http://localhost:9223/`** in your
own browser (not 6080 - that's a different port the container also exposes,
but 9223 is the one you actually visit) and follow the steps below, then
re-run the original script - it'll find the profile and continue.

For a generic site (`browsertrix-crawl.sh`), the steps are just: accept any
cookie banner, log in if the site needs it, then click "Create Profile" (or
skip the whole thing with `--no-profile` if the site needs neither).

For icaew.com (`icaew-browsertrix-crawl.sh`), follow these exact steps:

**Logged-in crawl** (default):
1. Open Chrome and navigate to `http://localhost:9223/`
2. Click "Allow all cookies"
3. Disable Brave shields
4. Login with your credentials
5. Disable Brave shields again (if prompted)
6. Close the "Discover the latest MyICAEW App" banner
7. Navigate to a page with a StreamAMG video player, e.g.
   `https://www.icaew.com/for-current-aca-students/training-agreement/your-online-training-file-guide/online-training-file-videos`
8. Verify that the video element loads correctly
9. Click "Create Profile"

**Public crawl** (`--public`) - same as above, minus the login and banner
steps:
1. Open Chrome and navigate to `http://localhost:9223/`
2. Click "Allow all cookies"
3. Disable Brave shields
4. Navigate to a page with a StreamAMG video player (same URL as above)
5. Verify that the video element loads correctly
6. Click "Create Profile"

Note that `--public` still creates its own profile (just without logging
in) - it doesn't skip profile creation entirely. It's a genuinely separate
profile from the logged-in one, kept as its own `profile.tar.gz` in the
public crawl's own project folder (`icaew-com-public/` vs `icaew-com-private/`),
so you'll need to go through this walkthrough once for each mode you use.
`browsertrix-crawl.sh`'s `--no-profile` is the only flag that actually skips
profile creation altogether, for sites that need neither cookies nor login.

### Crawling a new site you haven't crawled before

1. Make a new empty folder and copy `browsertrix-crawl.sh` into it.
2. Run (using a sitemap, if the site has one):

   ```bash
   ./browsertrix-crawl.sh --sitemap https://www.example.com/sitemap.xml
   ```

3. First run will likely stop asking you to create a profile (see above,
   or pass `--no-profile` if the site needs no login/cookie-banner
   handling). Do that, then re-run the same command.
4. Wait - it downloads what it needs, crawls, converts the result to a
   WACZ file, checks the result against your seed list, and (if anything's
   missing) automatically runs one more "patch" crawl to try and catch it.
5. When it finishes, you'll have:
   - `sites/<label>/crawls/collections/<label>/<date>-<label>.wacz` - the
     actual archived copy, ready to open in
     [replayweb.page](https://replayweb.page/) or ingest into Preservica.
   - `sites/<label>/<date>-<label>-browsertrix-qa.zip` - the seed file and
     CSV reports (which pages matched, which were missing, which came back
     non-200), for your own records.

### Crawling icaew.com specifically

1. Copy `icaew-browsertrix-crawl.sh` into a folder
2. Run:

   ```bash
   ./icaew-browsertrix-crawl.sh --sitemap https://www.icaew.com/sitemap_corporate.xml
   ```

3. First run will ask you to create a profile (see the exact steps above) -
   whether you're doing the default logged-in crawl or the public one
   (`--public`), you'll need to walk through the profile creation once for
   whichever mode you're using.
4. When it finishes: the WACZ is at
   `crawls/collections/icaew-com-logged-in/<date>-ICAEW-com-logged-in.wacz`
   (or `icaew-com-public`/`<date>-ICAEW-com-public.wacz` if you used
   `--public`), and the QA zip is
   `<date>-icaew-com-logged-in-browsertrix-qa.zip` in the same folder you
   ran the script from.

### Testing a specific page before a full crawl (template crawls)

If you just want to check how one or two specific pages render - e.g. a
newly designed page template - before running a full crawl, use
`icaew-template-browsertrix-crawl.sh` instead. It's much simpler: no discovery, no
validation, no patch crawl, just "crawl exactly these URLs and stop."

1. Copy `icaew-template-browsertrix-crawl.sh` into a folder.
2. Run, giving it the specific page(s) you want to test:

   ```bash
   ./icaew-template-browsertrix-crawl.sh --seed https://www.icaew.com/some-new-page-design/
   ```

   Add more `--seed` flags for additional pages.
3. First run will ask you to create a profile - same walkthrough as above.
   If you've already created one for `icaew-browsertrix-crawl.sh`'s
   logged-in crawl, this script reuses that same profile directly, no need
   to create a separate one.
4. When it finishes, open `crawls/collections/template-test/template-test.wacz`
   in [replayweb.page](https://replayweb.page/) and look at whether the
   page(s) rendered the way you expect.

### If it stops and prints an error

Read the last few lines of output - both scripts explain what's missing (a
program, a file, the profile, network access) and what to do about it.

### Stopping a crawl in progress

The actual crawling happens inside a Docker container, not directly in the
script - so stopping the script doesn't always stop the crawl.

- **If the script is running in the same terminal window you're looking
  at**: press `Ctrl+C`. This is usually enough - the signal reaches the
  container and it stops.
- **If that doesn't work, or the script was killed some other way**
  (closed the terminal, killed the process from another window, it was
  running in the background): the container can be left running on its own.
  Check for it and stop it manually:

  ```bash
  docker ps
  ```

  Look for a line with `webrecorder/browsertrix-crawler` in it and note its
  container ID (the short string in the first column), then:

  ```bash
  docker stop <container-id>
  ```

  Run `docker ps` again afterwards to confirm nothing browsertrix-related is
  still listed. If you have other unrelated containers running for other
  work, leave those alone - only stop the browsertrix one.

Once it's actually stopped, don't just re-run the script plain - that starts
a brand new full crawl from scratch (Browsertrix doesn't know anything was
interrupted). Add `--skip-crawl` if all you need is to check/re-validate
what's already in `archive/` from before the interruption; only drop
`--skip-crawl` if you actually want to crawl again from the top.

---

## Part 2: What these scripts actually do

### Overview of the pipeline

1. **Check prerequisites** - `docker`, `python3`, `zip`, and (unless
   `--offline`) `curl`.
2. **Fetch helper scripts if missing** - `web_archive_validator.py` (checks
   a WACZ/WARC against a seed list) and `warc_processor.py` (combines WARCs
   and converts to WACZ) are downloaded, if missing locally, from a pinned
   commit of
   [icaew-digital-archive/digital-archiving-scripts](https://github.com/icaew-digital-archive/digital-archiving-scripts)
   (currently `22db0b1a14`) rather than a floating branch, so a brand-new
   checkout always gets the exact same known-working copy instead of
   whatever `main` happens to look like that day. An existing local copy is
   never overwritten.
3. **Set up a Python venv** - both helper scripts need packages
   (`warcio`, `tqdm`, and the `wacz` command-line tool) that don't come with
   plain Python. A `venv/` folder is created next to the script the first
   time it's needed, and pinned versions (`warcio==1.8.1`, `tqdm==4.68.4`,
   `wacz==0.5.0`) are installed into it - this only touches packages that
   are actually missing, never reinstalls or upgrades what's already there.
4. **Pull the Docker image** - `webrecorder/browsertrix-crawler:1.5.11` is
   pulled automatically if not already present.
5. **Set up seeds** - same priority order as the wget scripts: `--seed`
   URLs are appended into the seed file (deduplicated, never overwriting);
   then `--sitemap` builds one if it's still missing (this needs the
   `requests` package, pinned to `2.34.2`, added to the same venv on
   demand). For
   `icaew-browsertrix-crawl.sh` specifically, this step also excludes
   `sprint-test-pages` and `active-members` URLs at the sitemap-conversion
   stage (`sitemap_xml_to_txt_or_html.py ... --exclude_strings
   "sprint-test-pages" "active-members"`, matching the documented example) -
   without this, those URLs would sit in the seed file, get correctly
   skipped during the crawl by the scope's exclude regex, and then show up
   as false-positive "missing" entries in the QA report, since the
   validator only knows what's in the seed file, not what was deliberately
   out of scope.
6. **Check for a browser profile** - see "the one thing that can't be
   automated" above. This is a hard stop, not a retry loop - there's no way
   to script a human logging in.
7. **Generate `crawl-config.yaml` if missing** - the YAML file Browsertrix
   actually reads. Only generated once; if you've hand-edited it since,
   your edits are left alone.
8. **Run the crawl** - `docker run ... crawl --config crawl-config.yaml`,
   unless `--skip-crawl` was passed (see "Re-running without re-crawling"
   below). A browser tab is opened automatically after a few seconds
   (`http://localhost:9037`) so you can watch it live, if you want.
9. **Validate** - `web_archive_validator.py` compares `archive/` (the
   crawler's own per-worker WARC output) against the seed file, writing
   matching/missing/non-200 CSVs. See "Why validation reads archive/
   directly" below.
10. **Patch crawl, once, if needed** - if anything came back missing or
    non-200, a second crawl runs automatically using the same config plus
    `depth: 1` (crawl the missing URLs plus one hop, to catch e.g. linked
    PDFs, without re-discovering the whole site) into the *same* collection,
    then re-validates against the now-larger `archive/`.
11. **Convert to WACZ** - once, using the final state of `archive/` after
    any patch crawl. See "Why WACZ conversion happens last" below.
12. **Package QA artifacts** - the seed file, any patch seed file, and the
    latest CSV reports are zipped together. The WACZ and full collection
    are left where they are, not included in this zip.

### Why validation reads `archive/` directly

`archive/` is the crawler's own per-worker WARC output - the ground truth,
written as the crawl happens, before any combining/packaging. Both
`web_archive_validator.py` and `warc_processor.py` are pointed at it
directly, and `combineWARC` is deliberately left **off** in the generated
config. This wasn't the original design - it's the result of a real
incident worth knowing about:

The scripts used to leave `combineWARC: true` on (Browsertrix's own
built-in WARC-combining feature) and validate against the combined output
it produced. That turned out to create **three copies of the same crawl on
disk**: the original per-worker segments in `archive/`, Browsertrix's own
combined copy of them at the collection root (`<collection>_0.warc.gz`,
etc. - pure repackaging, not new data), and then `warc_processor.py`'s
*own* re-combination of those into a temporary file before WACZ conversion.
For a full ICAEW crawl this meant roughly 20GB of real data turned into
~117GB on disk, validation took three times longer than necessary, and
extracting the final combined WARC out of a multi-GB WACZ (to check it)
read the whole thing into memory in one go and got killed by the Linux OOM
killer partway through - which, because the script had no failure check at
the time, was silently swallowed and nearly reported false success with an
empty QA zip.

Fixed by: turning `combineWARC` off entirely, pointing both
`web_archive_validator.py` and `warc_processor.py` straight at `archive/`,
and patching `web_archive_validator.py`'s own WACZ-extraction code to
stream (`shutil.copyfileobj`) instead of reading whole files into memory
(defensive - the normal code path no longer touches this at all, but it's
a real bug if anything ever points the validator at a `.wacz` directly).
Both scripts now also check the validator's exit status explicitly and
stop with a clear error rather than risk reporting success after a crash.

### Why WACZ conversion happens last

WACZ conversion (`wacz create`, via `warc_processor.py`) is the single most
expensive step in the whole pipeline - tens of minutes for a full ICAEW
crawl. Since validation and the patch crawl both work directly against
`archive/` and never touch the WACZ, there's no reason to build it before
you know whether a patch crawl is even going to happen. Building it once
up front and then *again* after patching (its original design) wastes that
expensive step entirely on a WACZ that's about to be replaced. It's now
built exactly once, right before packaging, from the final state of
`archive/` after any patch crawl has run.

`warc_processor.py` uses Browsertrix's own page list rather than `wacz`'s
own `--detect-pages` heuristic detection, which only catches pages matching
its own referrer-chain logic - in testing, a 118-page crawl came back as
only ~30 detected pages this way. Browsertrix's own crawl already writes an
accurate, complete page list to `pages/pages.jsonl` and
`pages/extraPages.jsonl` (seed pages *and* discovered non-seed pages like
linked PDFs) - **with full text already extracted from the rendered page**,
more accurate than `wacz`'s own post-hoc text extraction from raw
(pre-JavaScript) HTML. So these scripts pass those files straight through
to `wacz create` via `--pages`/`--extra-pages`/`--copy-pages`, bypassing its
detection and re-extraction entirely.

Also fixed along the way: the current `wacz` PyPI package requires the
`create` subcommand (`wacz create -o ...`); the original `warc_processor.py`
(as published upstream) builds the older flat form (`wacz -o ...`) with no
subcommand, which fails outright against current installs.

All of these fixes (the `create` subcommand, `--pages`/`--extra-pages`/
`--copy-pages` support, and the streaming extraction patch) have since been
merged into `digital-archiving-scripts`' `main` branch (PR #48, merged
2026-07-22). These scripts don't track `main` directly, though - the
GitHub fetch is pinned to that exact commit (`22db0b1a14`), confirmed to
match these local copies byte-for-byte at pin time, so a brand-new
checkout can't silently regress if `main` changes again later. Bump the
pinned commit deliberately (and re-diff against the local copies here)
if you ever need to pull in a newer upstream fix.

### Re-running without re-crawling

Browsertrix has no "this collection is already fully crawled" detection -
a fresh `docker run ... crawl` against an existing collection always starts
a brand new full crawl, seed list and all. If you just need to re-run
validation/WACZ-conversion (e.g. validation crashed last time, or you
patched the script and want to re-check without waiting through another
multi-hour crawl), pass `--skip-crawl`: it skips straight to validating
whatever's already in `archive/`, and still runs the one-patch-crawl-if-
needed step normally if gaps are found.

### `browsertrix-crawl.sh` specifics

- **`scopeType: "domain"`** - crawls whatever domain(s) appear in the seed
  file, no custom include/exclude scoping. For anything more specific (e.g.
  restricting a subdomain to certain paths), you'd currently need to hand-edit
  the generated `crawl-config.yaml` before the first crawl runs (it's only
  auto-generated if missing).
- **`--label`** works exactly like in `wget-crawl.sh` - names the
  `sites/<label>/` workspace (seed file, profile, `crawl-config.yaml`,
  collection) so multiple sites never collide. Auto-derived from
  `--sitemap`/`--seed`/`--seed-file`'s host if not set.
- **`--no-profile`** skips the profile requirement outright for sites that
  need no login or cookie-banner handling.
- **`--profile PATH`** lets you point at an existing profile from
  elsewhere, which gets copied into the workspace.
- **`--skip-crawl`** re-runs validation/WACZ-conversion against whatever's
  already in `sites/<label>/crawls/collections/<label>/archive/` without
  triggering a new crawl - see "Re-running without re-crawling" above.

### `icaew-browsertrix-crawl.sh` specifics

Unlike the wget pair, there's only ever **one** crawl leg here - Browsertrix
can express ICAEW's whole scope (icaew.com + cdn/regulation, train/volunteer
blog-only, several exclude patterns for logout/search/membership/test pages)
in a single `scopeType: "custom"` config with `include`/`exclude` regex,
rather than needing several separate invocations the way wget did. The
generated config's regex patterns are a byte-for-byte match of the scope
patterns in the pre-existing hand-written `crawl-config.yaml` this project
already had.

- **`--public`** switches the collection name to `icaew-com-public`, using
  its own config (`crawl-config-public.yaml`) - it does **not** skip profile
  creation, it just skips the login/banner steps in that profile's setup
  walkthrough. The profile itself is still just `profile.tar.gz` (the tool's
  own default name) - kept separate from the logged-in one only because
  each mode runs from its own project folder, not by renaming the file
  (matching the two collection names, `icaew-com-logged-in`/
  `icaew-com-public`, the original config already distinguished between).
- **Custom behaviours**: a site-specific JavaScript file
  (`icaew-com-behaviors-v4.js`) is referenced via `customBehaviors`, handling
  icaew.com-specific interactions during the crawl (cookie banners, etc.).
  Sourced from the same `digital-archiving-scripts` GitHub repo, pinned to
  the same commit as the other helper scripts.
- There's no per-site `sites/<label>/` workspace here - it works directly
  with `seedFile.txt`, `crawl-config.yaml`, and `crawls/` in whatever folder
  you run it from, matching `icaew-wget-crawl.sh`'s fixed-target style,
  since there's only ever one ICAEW to crawl.
- **`--skip-crawl`** re-runs validation/WACZ-conversion against whatever's
  already in `crawls/collections/<collection>/archive/` without triggering
  a new crawl - see "Re-running without re-crawling" above. Given a full
  ICAEW crawl can run for hours, this is the one to reach for if validation
  fails partway through, rather than re-crawling from scratch.

### `icaew-template-browsertrix-crawl.sh` specifics

This one is deliberately much smaller than the other two - it has no
Python dependency at all (no venv, no `web_archive_validator.py`, no
`warc_processor.py`), since there's no validation or WACZ post-processing
step. Docker is the only prerequisite.

- **`scopeType: "page-spa"`** instead of `"custom"` or `"domain"` - crawls
  *only* the exact URLs in the seed file, with no link discovery at all.
  There's no include/exclude scope regex in the generated config, because
  there's nothing to scope - it never follows a link to begin with.
- **`--collection NAME`** (default `template-test`) lets you name a
  specific test run if you want to keep several apart; the default is
  meant to be disposable and reused across quick tests.
- Reuses the **same profile** as `icaew-browsertrix-crawl.sh`'s default
  logged-in crawl (`crawls/profiles/profile.tar.gz`) - if you've already
  created one for that script, this one picks it up directly, no separate
  walkthrough needed. There's no `--public` equivalent here.
- `generateWACZ: true` is left in the generated config as documented
  (unlike the other two scripts, which removed it in favour of the
  `warc_processor.py` conversion step) - since there's no validation step
  relying on an accurate page count/full-text here, the crawler's own
  built-in WACZ generation is simpler and sufficient for a quick visual
  check.
- Default seed file is `template-seedFile.txt`, not `seedFile.txt` - kept
  deliberately separate so running this alongside `icaew-browsertrix-crawl.sh`
  in the same folder never mixes up "the whole site's seed list" with "the
  handful of pages I'm currently testing."

### Flag reference

Run `head -35 browsertrix-crawl.sh`, `head -35 icaew-browsertrix-crawl.sh`,
or `head -30 icaew-template-browsertrix-crawl.sh` at any time to see the full up-to-date
flag list in the script's own header
comment - that's the authoritative reference, kept in sync with the code
itself rather than duplicated here where it could drift out of date.
