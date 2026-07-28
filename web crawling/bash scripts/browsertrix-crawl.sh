#!/usr/bin/env bash
#
# Generic Browsertrix Crawler wrapper - "simple domain crawl" from the
# handbook (admin-guides/web-archiving/browsertrix.html): crawls whatever
# domain(s) are listed in a seed file, validates the result against the seed
# file with web_archive_validator.py, and runs one patch crawl (depth: 1,
# same collection) for anything missing/non-200.
#
# Browser profile creation is NOT automated - it's an interactive step (you
# have to actually click through cookie banners etc. in a VNC browser
# window). First run without a profile present (and without --no-profile)
# will print the exact command to create one and stop; re-run this script
# once that's done. Not every site needs one - pass --no-profile to skip it
# entirely.
#
# Usage:
#   ./browsertrix-crawl.sh --seed-file seedFile.txt
#   ./browsertrix-crawl.sh --sitemap https://www.ccab.org.uk/sitemap.xml
#   ./browsertrix-crawl.sh --sitemap https://www.ccab.org.uk/sitemap.xml --no-profile
#
# Flags:
#   --seed-file PATH       URL list to crawl (default: sites/<label>/seedFile.txt)
#   --seed URL             a single URL to crawl - repeatable (--seed url1 --seed url2 ...); writes
#                          them into --seed-file, so validation/patch-crawl still work normally
#   --sitemap URL          sitemap (or sitemap index) URL; bootstraps --seed-file if it doesn't exist yet
#   --label NAME           workspace/collection name (default: derived from --sitemap or first seed URL's host)
#   --profile PATH         use an existing profile.tar.gz (copied into the workspace if elsewhere)
#   --no-profile           skip the browser profile entirely - not every site needs one
#   --profile-url URL      URL used only in the printed create-login-profile instructions (default: derived)
#   --workers N            Browsertrix worker count (default: 6)
#   --validator-script PATH  override location of web_archive_validator.py (default: alongside this script)
#   --sitemap-script PATH    override location of sitemap_xml_to_txt_or_html.py (default: alongside this script)
#   --warc-processor-script PATH  override location of warc_processor.py (default: alongside this script)
#   --offline              don't fall back to downloading missing helper scripts from GitHub, or pulling the image
#   --skip-crawl           don't re-crawl (Browsertrix has no "already done" detection - a fresh
#                          docker run always re-crawls everything) - just re-run WACZ conversion
#                          + validation + patch-crawl-if-needed against what's already in archive/

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRIPTS_REPO_RAW="https://raw.githubusercontent.com/icaew-digital-archive/digital-archiving-scripts/22db0b1a14dbcfa64231931ddec12dbad7672136"
VALIDATOR_URL="$SCRIPTS_REPO_RAW/web%20crawling/web_archive_validator.py"
SITEMAP_SCRIPT_URL="$SCRIPTS_REPO_RAW/sitemap%20tools/sitemap_xml_to_txt_or_html.py"
WARC_PROCESSOR_URL="$SCRIPTS_REPO_RAW/web%20crawling/warc_processor.py"
IMAGE="webrecorder/browsertrix-crawler:1.5.11"

# web_archive_validator.py needs 'warcio'+'tqdm'; sitemap_xml_to_txt_or_html.py
# needs 'requests' (only used if --sitemap bootstrap actually runs);
# warc_processor.py needs 'warcio' (already covered) plus the separate 'wacz'
# CLI tool (pip install wacz - it's invoked as a subprocess, not imported).
VENV_DIR="$SCRIPT_DIR/venv"
VENV_PY="$VENV_DIR/bin/python3"

# ---- Defaults ------------------------------------------------------------

SEED_FILE=""
SEED_URLS=()
SITEMAP_INDEX=""
LABEL=""
PROFILE_OVERRIDE=""
NEED_PROFILE=true
PROFILE_URL=""
WORKERS=6
VALIDATOR_SCRIPT=""
SITEMAP_SCRIPT=""
WARC_PROCESSOR_SCRIPT=""
OFFLINE=false
SKIP_CRAWL=false

# ---- Arg parsing ----------------------------------------------------------

while [[ $# -gt 0 ]]; do
  case "$1" in
    --seed-file) SEED_FILE="$2"; shift 2 ;;
    --seed) SEED_URLS+=("$2"); shift 2 ;;
    --sitemap) SITEMAP_INDEX="$2"; shift 2 ;;
    --label) LABEL="$2"; shift 2 ;;
    --profile) PROFILE_OVERRIDE="$2"; shift 2 ;;
    --no-profile) NEED_PROFILE=false; shift ;;
    --profile-url) PROFILE_URL="$2"; shift 2 ;;
    --workers) WORKERS="$2"; shift 2 ;;
    --validator-script) VALIDATOR_SCRIPT="$2"; shift 2 ;;
    --sitemap-script) SITEMAP_SCRIPT="$2"; shift 2 ;;
    --warc-processor-script) WARC_PROCESSOR_SCRIPT="$2"; shift 2 ;;
    --offline) OFFLINE=true; shift ;;
    --skip-crawl) SKIP_CRAWL=true; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

# ---- Derive --label before the seed file necessarily exists ---------------

if [[ -z "$LABEL" ]]; then
  if [[ -n "$SITEMAP_INDEX" ]]; then
    SITEMAP_HOST="$(sed -E 's#^[a-zA-Z]+://##; s#/.*##' <<< "$SITEMAP_INDEX")"
    LABEL="$(tr '.' '-' <<< "${SITEMAP_HOST#www.}")"
  elif [[ "${#SEED_URLS[@]}" -gt 0 ]]; then
    HOST="$(sed -E 's#^[a-zA-Z]+://##; s#/.*##' <<< "${SEED_URLS[0]}")"
    LABEL="$(tr '.' '-' <<< "${HOST#www.}")"
  elif [[ -s "$SEED_FILE" ]]; then
    FIRST_URL="$(grep -m1 -E '^https?://' "$SEED_FILE")"
    [[ -z "$FIRST_URL" ]] && { echo "No http(s) URL found in $SEED_FILE" >&2; exit 1; }
    HOST="$(sed -E 's#^[a-zA-Z]+://##; s#/.*##' <<< "$FIRST_URL")"
    LABEL="$(tr '.' '-' <<< "${HOST#www.}")"
  else
    echo "Can't derive --label: provide --label, --seed-file (existing), --seed, or --sitemap" >&2
    exit 1
  fi
fi

WORKDIR="sites/$LABEL"
[[ -z "$SEED_FILE" ]] && SEED_FILE="$WORKDIR/seedFile.txt"
[[ -z "$VALIDATOR_SCRIPT" ]] && VALIDATOR_SCRIPT="$SCRIPT_DIR/web_archive_validator.py"
[[ -z "$SITEMAP_SCRIPT" ]] && SITEMAP_SCRIPT="$SCRIPT_DIR/sitemap_xml_to_txt_or_html.py"
[[ -z "$WARC_PROCESSOR_SCRIPT" ]] && WARC_PROCESSOR_SCRIPT="$SCRIPT_DIR/warc_processor.py"

mkdir -p "$WORKDIR/crawls/profiles" "$WORKDIR/crawls/collections"

CRAWL_CONFIG="$WORKDIR/crawl-config.yaml"
PATCH_CONFIG="$WORKDIR/patch-crawl-config.yaml"
PROFILE_PATH="$WORKDIR/crawls/profiles/profile.tar.gz"
LOG_FILE="$WORKDIR/${LABEL}-browsertrix.log"

if [[ -z "$PROFILE_URL" ]]; then
  if [[ -n "$SITEMAP_INDEX" ]]; then
    PROFILE_URL="https://$(sed -E 's#^[a-zA-Z]+://##; s#/.*##' <<< "$SITEMAP_INDEX")/"
  elif [[ "${#SEED_URLS[@]}" -gt 0 ]]; then
    PROFILE_URL="https://$(sed -E 's#^[a-zA-Z]+://##; s#/.*##' <<< "${SEED_URLS[0]}")/"
  elif [[ -s "$SEED_FILE" ]]; then
    FIRST_URL="$(grep -m1 -E '^https?://' "$SEED_FILE")"
    PROFILE_URL="https://$(sed -E 's#^[a-zA-Z]+://##; s#/.*##' <<< "$FIRST_URL")/"
  fi
fi

# ---- Prerequisite checks -------------------------------------------------

command -v docker >/dev/null || { echo "docker not found" >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 not found" >&2; exit 1; }
command -v zip >/dev/null || { echo "zip not found" >&2; exit 1; }
if ! $OFFLINE; then
  command -v curl >/dev/null || { echo "curl not found (needed for GitHub fallback download / image pull check; pass --offline to skip)" >&2; exit 1; }
fi

ensure_script() {
  local path="$1" url="$2" label="$3"
  [[ -s "$path" ]] && return 0

  if $OFFLINE; then
    echo "$label not found at $path (--offline set, not downloading)" >&2
    exit 1
  fi

  echo "=== $label not found at $path - downloading from GitHub ===" >&2
  mkdir -p "$(dirname "$path")"
  if ! curl -sf -o "$path" "$url"; then
    rm -f "$path"
    echo "Failed to download $label from $url" >&2
    exit 1
  fi
  echo "=== Downloaded $label to $path - NOTE: upstream may be behind any local fixes ===" >&2
}

ensure_venv() {
  if [[ ! -x "$VENV_PY" ]]; then
    if $OFFLINE; then
      echo "No venv at $VENV_DIR and --offline set - can't create one" >&2
      exit 1
    fi
    echo "=== No venv at $VENV_DIR - creating one ===" >&2
    python3 -m venv "$VENV_DIR"
  fi

  if ! "$VENV_PY" -c "import warcio, tqdm" >/dev/null 2>&1; then
    if $OFFLINE; then
      echo "venv at $VENV_DIR is missing 'warcio'/'tqdm' and --offline set - can't install" >&2
      exit 1
    fi
    echo "=== Installing 'warcio' and 'tqdm' into $VENV_DIR ===" >&2
    "$VENV_DIR/bin/pip" install --quiet "warcio==1.8.1" "tqdm==4.68.4"
  fi
}

ensure_requests() {
  if ! "$VENV_PY" -c "import requests" >/dev/null 2>&1; then
    if $OFFLINE; then
      echo "venv at $VENV_DIR is missing 'requests' and --offline set - can't install" >&2
      exit 1
    fi
    echo "=== Installing 'requests' into $VENV_DIR ===" >&2
    "$VENV_DIR/bin/pip" install --quiet "requests==2.34.2"
  fi
}

ensure_wacz() {
  if ! "$VENV_DIR/bin/wacz" --help >/dev/null 2>&1; then
    if $OFFLINE; then
      echo "venv at $VENV_DIR is missing the 'wacz' CLI and --offline set - can't install" >&2
      exit 1
    fi
    echo "=== Installing 'wacz' into $VENV_DIR ===" >&2
    "$VENV_DIR/bin/pip" install --quiet "wacz==0.5.0"
  fi
}

ensure_script "$VALIDATOR_SCRIPT" "$VALIDATOR_URL" "web_archive_validator.py"
ensure_script "$WARC_PROCESSOR_SCRIPT" "$WARC_PROCESSOR_URL" "warc_processor.py"
ensure_venv
ensure_wacz

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  if $OFFLINE; then
    echo "Docker image $IMAGE not present locally and --offline set - can't pull" >&2
    exit 1
  fi
  echo "=== Pulling $IMAGE ===" >&2
  docker pull "$IMAGE"
fi

# ---- Optional: add --seed URL(s) to the seed file -------------------------
#
# Appends and dedupes rather than overwriting, so this never clobbers an
# existing seed file (e.g. one already built via --sitemap on a prior run).
# Once written, this is just a normal seed file - validation and the one
# patch-crawl-if-needed step work exactly as with a hand-built seedFile.txt.

if [[ "${#SEED_URLS[@]}" -gt 0 ]]; then
  printf '%s\n' "${SEED_URLS[@]}" >> "$SEED_FILE"
  sort -u -o "$SEED_FILE" "$SEED_FILE"
  echo "=== Seed file updated from --seed: now $(wc -l < "$SEED_FILE") URL(s) ===" >&2
fi

# ---- Optional: bootstrap seedFile.txt from a sitemap (or sitemap index) --

if [[ ! -s "$SEED_FILE" && -n "$SITEMAP_INDEX" ]]; then
  ensure_script "$SITEMAP_SCRIPT" "$SITEMAP_SCRIPT_URL" "sitemap_xml_to_txt_or_html.py"
  ensure_requests
  echo "=== Building $SEED_FILE from sitemap: $SITEMAP_INDEX ===" >&2
  "$VENV_PY" "$SITEMAP_SCRIPT" "$SITEMAP_INDEX" --deduplicate --to_file "$SEED_FILE"
  echo "=== Seed file built: $(wc -l < "$SEED_FILE") URLs ===" >&2
fi

if [[ ! -s "$SEED_FILE" ]]; then
  echo "Missing or empty required file: $SEED_FILE (provide --seed-file directly, or pass --sitemap to build it)" >&2
  exit 1
fi

# ---- Browser profile: can't automate, it's interactive -------------------
# Not every site needs one - pass --no-profile to skip this entirely.

if $NEED_PROFILE; then
  if [[ -n "$PROFILE_OVERRIDE" ]]; then
    cp -n "$PROFILE_OVERRIDE" "$PROFILE_PATH" 2>/dev/null
  fi

  if [[ ! -s "$PROFILE_PATH" ]]; then
    ABS_PROFILE_DIR="$(cd "$WORKDIR/crawls/profiles" && pwd)"
    cat >&2 <<EOF
=== No browser profile at $PROFILE_PATH ===
This step needs a human. Run this:

  docker run -p 6080:6080 -p 9223:9223 \\
      -v $ABS_PROFILE_DIR:/crawls/profiles/ \\
      -it $IMAGE \\
      create-login-profile --url "$PROFILE_URL"

Then: open Chrome and navigate to http://localhost:9223/, accept any cookie
banner, log in if the site needs it, then click "Create Profile". Re-run
this script afterwards - it'll find the profile and continue (or pass
--no-profile if this site doesn't need one).
EOF
    exit 1
  fi
fi

# ---- Generate crawl-config.yaml if missing (simple domain crawl) --------

if [[ ! -s "$CRAWL_CONFIG" ]]; then
  {
    echo "# For additional configuration options, see https://crawler.docs.browsertrix.com/user-guide/yaml-crawl-config/"
    echo "# Generated by browsertrix-crawl.sh - simple domain crawl for $LABEL"
    echo
    $NEED_PROFILE && echo "profile: /crawls/profiles/profile.tar.gz"
    cat <<EOF
seedFile: /app/seedFile.txt
collection: $LABEL
screencastPort: 9037

allowHashUrls: true
workers: $WORKERS
text:
  - to-warc
diskUtilization: 0

scopeType: "domain"
EOF
  } > "$CRAWL_CONFIG"
  echo "=== Generated $CRAWL_CONFIG ===" >&2
fi

# ---- Run the crawl ---------------------------------------------------

ABS_WORKDIR_CRAWLS="$(cd "$WORKDIR/crawls" && pwd)"
ABS_SEED_FILE="$(cd "$(dirname "$SEED_FILE")" && pwd)/$(basename "$SEED_FILE")"

run_crawl() {
  local config="$1"
  local abs_config
  abs_config="$(cd "$(dirname "$config")" && pwd)/$(basename "$config")"
  docker run -p 9037:9037 \
    -v "$ABS_WORKDIR_CRAWLS:/crawls" \
    -v "$abs_config:/app/crawl-config.yaml" \
    -v "$ABS_SEED_FILE:/app/seedFile.txt" \
    "$IMAGE" crawl --config /app/crawl-config.yaml 2>&1 | tee -a "$LOG_FILE"
}

open_monitor() {
  command -v xdg-open >/dev/null || return 0
  ( sleep 3 && xdg-open "http://localhost:9037/" >/dev/null 2>&1 ) &
}

COLLECTION_DIR="$WORKDIR/crawls/collections/$LABEL"

# ---- Convert archive/ WARC segments to WACZ with warc_processor.py -------
#
# Reads directly from archive/, the crawler's own per-worker WARC output -
# NOT Browsertrix's own combineWARC output (deliberately disabled above),
# which was just a second, redundant on-disk copy of the same records, and
# NOT the whole collection dir either, which would also pick up the
# (now-absent) combined parts and any previously-created .wacz.

run_warc_processor() {
  local archive_dir="$COLLECTION_DIR/archive"
  if [[ ! -d "$archive_dir" ]] || [[ -z "$(ls -A "$archive_dir" 2>/dev/null)" ]]; then
    echo "=== No archive/ WARC segments found at $archive_dir - skipping WACZ conversion ===" >&2
    return 0
  fi

  # Use Browsertrix's own page list rather than wacz's own --detect-pages
  # heuristic (which only catches pages matching its referrer-chain logic,
  # not the full seed list). But strip the embedded "text" field first -
  # having full extracted text inline on every page entry (tens of KB each,
  # times tens of thousands of pages) bloats pages.jsonl into hundreds of MB
  # of *uncompressed* data the player has to fetch and parse before it can
  # even show the page list, which caused real loading problems in
  # replayweb.page. The text itself isn't lost - it's still captured
  # separately as its own WARC resource record (`text: [to-warc]` in the
  # crawl config), so a full-text index can be regenerated from the WARC
  # later if replay tooling gets better at handling this at scale.
  local pages_file="$COLLECTION_DIR/pages/pages.jsonl"
  local extra_pages_file="$COLLECTION_DIR/pages/extraPages.jsonl"
  local page_args=()

  strip_text_field() {
    "$VENV_PY" -c "
import json, sys
with open(sys.argv[1]) as f_in, open(sys.argv[2], 'w') as f_out:
    for line in f_in:
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        obj.pop('text', None)
        if 'hasText' in obj:
            obj['hasText'] = False
        f_out.write(json.dumps(obj) + '\n')
" "$1" "$2"
  }

  if [[ -s "$pages_file" ]]; then
    local stripped_pages="$COLLECTION_DIR/.pages-stripped.jsonl"
    strip_text_field "$pages_file" "$stripped_pages"
    page_args+=(--pages "$stripped_pages" --copy-pages)

    if [[ -s "$extra_pages_file" ]]; then
      local stripped_extra="$COLLECTION_DIR/.extraPages-stripped.jsonl"
      strip_text_field "$extra_pages_file" "$stripped_extra"
      page_args+=(--extra-pages "$stripped_extra")
    fi
  fi

  echo "=== Converting archive/ WARC segments to WACZ for $LABEL ===" >&2
  PATH="$VENV_DIR/bin:$PATH" "$VENV_PY" "$WARC_PROCESSOR_SCRIPT" \
    --input "$archive_dir" \
    --output "$COLLECTION_DIR/$WACZ_NAME.wacz" \
    "${page_args[@]}" \
    --verbose

  rm -f "$COLLECTION_DIR/.pages-stripped.jsonl" "$COLLECTION_DIR/.extraPages-stripped.jsonl"
}

if $SKIP_CRAWL; then
  echo "=== --skip-crawl set - not re-crawling, going straight to validation ===" >&2
else
  echo "=== Crawling $LABEL (monitor at http://localhost:9037) ===" >&2
  open_monitor
  run_crawl "$CRAWL_CONFIG"
fi

# ---- Validate, patch once if needed --------------------------------------
#
# WACZ conversion is deferred to the very end (after any patch crawl) -
# run_validator reads straight from archive/, not the WACZ, so there's no
# need to build it before we know whether a patch crawl is even needed.
# Building it twice (once here, again after patching) would waste the most
# expensive step in the whole pipeline on a WACZ that's about to be replaced.

run_validator() {
  # Validate against archive/ directly - NOT the whole collection dir, which
  # would also pick up any leftover combined parts/.wacz from before this
  # was fixed to skip Browsertrix's own combineWARC output.
  local archive_dir="$COLLECTION_DIR/archive"
  if [[ ! -d "$archive_dir" ]] || [[ -z "$(ls -A "$archive_dir" 2>/dev/null)" ]]; then
    echo "No archive/ WARC segments found at $archive_dir to validate against" >&2
    return 1
  fi
  "$VENV_PY" "$VALIDATOR_SCRIPT" "$SEED_FILE" "$archive_dir" --output-dir "$WORKDIR"
}

extract_urls() {
  "$VENV_PY" -c "
import csv, sys
for fname in sys.argv[1:]:
    with open(fname) as f:
        r = csv.reader(f)
        next(r, None)
        for row in r:
            if row:
                print(row[0])
" "$@"
}

echo "=== Validating $LABEL against $SEED_FILE ===" >&2
if ! run_validator; then
  echo "=== ERROR: validation failed - stopping here rather than risk reporting false success. Check the output above (often an out-of-memory kill on very large crawls), then re-run this script - the crawl itself doesn't need repeating, only validation. ===" >&2
  exit 1
fi

missing_csv="$(ls -t "$WORKDIR"/missing_urls_*.csv 2>/dev/null | head -1)"
non200_csv="$(ls -t "$WORKDIR"/non_200_urls_*.csv 2>/dev/null | head -1)"

if [[ -z "$missing_csv" || -z "$non200_csv" ]]; then
  echo "=== ERROR: validation reported success but expected CSV files are missing - stopping rather than guessing ===" >&2
  exit 1
fi

PATCH_SEED_FILE="$WORKDIR/patch-seedFile.txt"
extract_urls "$missing_csv" "$non200_csv" | sort -u > "$PATCH_SEED_FILE"

if [[ -s "$PATCH_SEED_FILE" ]]; then
  patch_count=$(wc -l < "$PATCH_SEED_FILE")
  echo "=== $patch_count URL(s) missing/non-200 - running one patch crawl (depth: 1, same collection) ===" >&2

  cp "$CRAWL_CONFIG" "$PATCH_CONFIG"
  echo "depth: 1" >> "$PATCH_CONFIG"

  ABS_SEED_FILE="$(cd "$(dirname "$PATCH_SEED_FILE")" && pwd)/$(basename "$PATCH_SEED_FILE")"
  open_monitor
  run_crawl "$PATCH_CONFIG"

  echo "=== Re-validating $LABEL after patch crawl ===" >&2
  if ! run_validator; then
    echo "=== ERROR: re-validation after patch crawl failed - stopping here rather than risk reporting false success ===" >&2
    exit 1
  fi
else
  echo "=== All URLs accounted for, no patch crawl needed ===" >&2
fi

# ---- Convert archive/ to WACZ now that we know the final state (after any
# patch crawl) - only ever built once per run. -----------------------------
#
# Dated so the .wacz itself carries the same convention as the QA zip (e.g.
# 20260722-some-label.wacz), rather than the undated $LABEL.wacz used
# internally elsewhere in this script for paths ($COLLECTION_DIR/...).

WACZ_NAME="$(date +%Y%m%d)-${LABEL}"
run_warc_processor

# ---- Package seed files + latest CSV reports (not the WACZ/collection, --
# those stay in place under $COLLECTION_DIR for direct use) ----------------

PACKAGE_NAME="$(date +%Y%m%d)-${LABEL}-browsertrix-qa"
PACKAGE_DIR="$WORKDIR/$PACKAGE_NAME"
mkdir -p "$PACKAGE_DIR"

cp "$SEED_FILE" "$PACKAGE_DIR/" 2>/dev/null
[[ -s "$PATCH_SEED_FILE" ]] && cp "$PATCH_SEED_FILE" "$PACKAGE_DIR/"

for pattern in matching_urls_ missing_urls_ non_200_urls_; do
  latest="$(ls -t "$WORKDIR/${pattern}"*.csv 2>/dev/null | head -1)"
  [[ -n "$latest" ]] && cp "$latest" "$PACKAGE_DIR/"
done

( cd "$WORKDIR" && zip -r "${PACKAGE_NAME}.zip" "$PACKAGE_NAME" >/dev/null )
rm -rf "$PACKAGE_DIR"

echo "=== Done: $WORKDIR/${PACKAGE_NAME}.zip has seed files + CSV reports; $COLLECTION_DIR/$WACZ_NAME.wacz has the WACZ ===" >&2
