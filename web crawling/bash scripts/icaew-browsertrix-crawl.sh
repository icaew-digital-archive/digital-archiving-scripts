#!/usr/bin/env bash
#
# Wrapper for the ICAEW.com Browsertrix Crawler crawl (see handbook:
# admin-guides/web-archiving/browsertrix.html). Unlike the generic
# browsertrix-crawl.sh, this hardcodes ICAEW's real custom scope (icaew.com +
# cdn/regulation subdomains, train/volunteer restricted to blog/article paths)
# and its custom behaviours JS - Browsertrix handles all of that in one
# config/invocation, so (unlike the wget scripts) there's no need for
# separate legs here.
#
# Validates the result against the seed file with web_archive_validator.py,
# and runs one patch crawl (depth: 1, same collection) for anything
# missing/non-200.
#
# Browser profile creation is NOT automated - it's an interactive step (you
# have to actually log in and click through cookie banners in a VNC-style
# browser window at http://localhost:9223/). Both the logged-in and --public
# crawls need their own profile (the public one just skips the login/banner
# steps) - first run without one present will print the exact command and
# the manual steps to follow, then stop; re-run this script once that's done.
#
# Usage:
#   ./icaew-browsertrix-crawl.sh --sitemap https://www.icaew.com/sitemap_corporate.xml
#   ./icaew-browsertrix-crawl.sh --sitemap https://www.icaew.com/sitemap_corporate.xml --public   # icaew-com-public collection, no login needed
#   ./icaew-browsertrix-crawl.sh              # reuses an existing seedFile.txt as-is if you already have one
#
# Flags:
#   --seed-file PATH     URL list to crawl (default: seedFile.txt)
#   --seed URL           a single URL to add - repeatable (--seed url1 --seed url2 ...);
#                        appends+dedupes into --seed-file, never overwrites it
#   --sitemap URL        sitemap (or sitemap index) URL; bootstraps --seed-file if missing
#   --public             use the icaew-com-public collection/profile/config - still needs
#                        its own profile, just without logging in
#   --workers N          Browsertrix worker count (default: 6)
#   --validator-script PATH        override location of web_archive_validator.py
#   --sitemap-script PATH          override location of sitemap_xml_to_txt_or_html.py
#   --warc-processor-script PATH   override location of warc_processor.py
#   --offline            don't fall back to downloading missing helper scripts from GitHub, or pulling the image
#   --skip-crawl         don't re-crawl (Browsertrix has no "already done" detection - a fresh
#                        docker run always re-crawls everything) - just re-run WACZ conversion
#                        + validation + patch-crawl-if-needed against what's already in archive/

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRIPTS_REPO_RAW="https://raw.githubusercontent.com/icaew-digital-archive/digital-archiving-scripts/22db0b1a14dbcfa64231931ddec12dbad7672136"
VALIDATOR_URL="$SCRIPTS_REPO_RAW/web%20crawling/web_archive_validator.py"
SITEMAP_SCRIPT_URL="$SCRIPTS_REPO_RAW/sitemap%20tools/sitemap_xml_to_txt_or_html.py"
WARC_PROCESSOR_URL="$SCRIPTS_REPO_RAW/web%20crawling/warc_processor.py"
CUSTOM_BEHAVIORS_URL="$SCRIPTS_REPO_RAW/browsertrix-crawler%20files%20and%20scripts/icaew-com-behaviors-v2.js"
IMAGE="webrecorder/browsertrix-crawler:1.5.11"

# web_archive_validator.py needs 'warcio'+'tqdm'; sitemap_xml_to_txt_or_html.py
# needs 'requests' (only used if --sitemap bootstrap actually runs);
# warc_processor.py needs 'warcio' (already covered) plus the separate 'wacz'
# CLI tool (pip install wacz - it's invoked as a subprocess, not imported).
VENV_DIR="$SCRIPT_DIR/venv"
VENV_PY="$VENV_DIR/bin/python3"

# ---- Defaults ------------------------------------------------------------

SEED_FILE="seedFile.txt"
SEED_URLS=()
SITEMAP_INDEX=""
PUBLIC=false
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
    --public) PUBLIC=true; shift ;;
    --workers) WORKERS="$2"; shift 2 ;;
    --validator-script) VALIDATOR_SCRIPT="$2"; shift 2 ;;
    --sitemap-script) SITEMAP_SCRIPT="$2"; shift 2 ;;
    --warc-processor-script) WARC_PROCESSOR_SCRIPT="$2"; shift 2 ;;
    --offline) OFFLINE=true; shift ;;
    --skip-crawl) SKIP_CRAWL=true; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

[[ -z "$VALIDATOR_SCRIPT" ]] && VALIDATOR_SCRIPT="$SCRIPT_DIR/web_archive_validator.py"
[[ -z "$SITEMAP_SCRIPT" ]] && SITEMAP_SCRIPT="$SCRIPT_DIR/sitemap_xml_to_txt_or_html.py"
[[ -z "$WARC_PROCESSOR_SCRIPT" ]] && WARC_PROCESSOR_SCRIPT="$SCRIPT_DIR/warc_processor.py"

if $PUBLIC; then
  COLLECTION="icaew-com-public"
  CRAWL_CONFIG="crawl-config-public.yaml"
  PATCH_CONFIG="patch-crawl-config-public.yaml"
  PROFILE_TARGET_URL="https://www.icaew.com/"
else
  COLLECTION="icaew-com-logged-in"
  CRAWL_CONFIG="crawl-config.yaml"
  PATCH_CONFIG="patch-crawl-config.yaml"
  PROFILE_TARGET_URL="https://my.icaew.com/security/Account/Login"
fi

# Always the tool's own default filename - public and logged-in crawls each
# run from their own project folder (icaew-com-public/, icaew-com-private/),
# so there's no collision to avoid by renaming it.
PROFILE_PATH="crawls/profiles/profile.tar.gz"

LOG_FILE="${COLLECTION}-browsertrix.log"

mkdir -p crawls/profiles crawls/collections

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
# Appends and dedupes rather than overwriting - seedFile.txt here is usually
# a large, separately-curated file, so --seed should add to it, not replace it.

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
  "$VENV_PY" "$SITEMAP_SCRIPT" "$SITEMAP_INDEX" --deduplicate --to_file "$SEED_FILE" \
    --exclude_strings "sprint-test-pages" "active-members"
  echo "=== Seed file built: $(wc -l < "$SEED_FILE") URLs ===" >&2
fi

if [[ ! -s "$SEED_FILE" ]]; then
  echo "Missing or empty required file: $SEED_FILE (provide it directly, or pass --sitemap to build it)" >&2
  exit 1
fi

# ---- Always include the ICAEW logo SVG in the seed list -------------------
#
# Hardcoded rather than relying on it showing up via --seed/--sitemap/an
# existing curated seed file - added unconditionally (deduped, so re-runs
# don't create repeat entries) so it's always captured regardless of what
# else is or isn't in $SEED_FILE.

echo "https://cdn.icaew.com/v1/production/img/fe-global/logo__icaew.svg" >> "$SEED_FILE"
sort -u -o "$SEED_FILE" "$SEED_FILE"

# ---- Browser profile: can't automate, it's interactive -------------------
#
# Both the logged-in and --public crawls need their own profile - the
# handbook's public variant still creates one (for cookie consent), it just
# skips the login and app-banner steps.

if [[ ! -s "$PROFILE_PATH" ]]; then
  ABS_PROFILE_DIR="$(cd crawls/profiles && pwd)"
  {
    echo "=== No browser profile at $PROFILE_PATH ==="
    echo "This step needs a human. Run this:"
    echo
    echo "  docker run -p 6080:6080 -p 9223:9223 \\"
    echo "      -v $ABS_PROFILE_DIR:/crawls/profiles/ \\"
    echo "      -it $IMAGE \\"
    echo "      create-login-profile --url \"$PROFILE_TARGET_URL\""
    echo
    echo "Then, in order:"
    echo "  1. Open Chrome and navigate to http://localhost:9223/"
    echo "  2. Click \"Allow all cookies\""
    echo "  3. Disable Brave shields"
    if ! $PUBLIC; then
      echo "  4. Login with your credentials"
      echo "  5. Disable Brave shields again (if prompted)"
      echo "  6. Close the \"Discover the latest MyICAEW App\" banner"
      echo "  7. Navigate to a page with a StreamAMG video player, e.g."
      echo "     https://www.icaew.com/for-current-aca-students/training-agreement/your-online-training-file-guide/online-training-file-videos"
      echo "  8. Verify that the video element loads correctly"
      echo "  9. Click \"Create Profile\""
    else
      echo "  4. Navigate to a page with a StreamAMG video player, e.g."
      echo "     https://www.icaew.com/for-current-aca-students/training-agreement/your-online-training-file-guide/online-training-file-videos"
      echo "  5. Verify that the video element loads correctly"
      echo "  6. Click \"Create Profile\""
    fi
    echo
    echo "Then re-run this script - it'll find the profile and continue."
  } >&2
  exit 1
fi

# ---- Generate crawl-config.yaml if missing (ICAEW's real custom scope) --

if [[ ! -s "$CRAWL_CONFIG" ]]; then
  {
    echo "# For additional configuration options, see https://crawler.docs.browsertrix.com/user-guide/yaml-crawl-config/"
    echo "# Generated by icaew-browsertrix-crawl.sh"
    echo
    echo "profile: /crawls/profiles/$(basename "$PROFILE_PATH")"
    cat <<EOF
seedFile: /app/seedFile.txt
collection: $COLLECTION
screencastPort: 9037
customBehaviors: $CUSTOM_BEHAVIORS_URL

allowHashUrls: true
workers: $WORKERS
text:
  - to-warc
diskUtilization: 0

scopeType: "custom"
include:
  - ^(http(s)?:\/\/)?(www\.)?(cdn\.|regulation\.)?icaew\.com.*\$
  - ^(http(s)?:\/\/)?(www\.)?(train|volunteer)\.icaew\.com(\/)?(blog.*)?\$
exclude:
  - ^.*(l|L)(o|O)(g|G)(o|O)(f|F)(f|F).*\$
  - ^(http(s)?:\/\/)?(www\.)?icaew\.com\/search.*\$
  - ^(http(s)?:\/\/)?(www\.)?.*\/member(s|ship)\/active-members.*\$
  - ^(http(s)?:\/\/)?(www\.)?.*sprint-test-pages.*\$
EOF
  } > "$CRAWL_CONFIG"
  echo "=== Generated $CRAWL_CONFIG ===" >&2
fi

# ---- Run the crawl ---------------------------------------------------

ABS_CRAWLS_DIR="$(cd crawls && pwd)"
ABS_SEED_FILE="$(cd "$(dirname "$SEED_FILE")" && pwd)/$(basename "$SEED_FILE")"

run_crawl() {
  local config="$1"
  local abs_config
  abs_config="$(cd "$(dirname "$config")" && pwd)/$(basename "$config")"
  docker run -p 9037:9037 \
    -v "$ABS_CRAWLS_DIR:/crawls" \
    -v "$abs_config:/app/crawl-config.yaml" \
    -v "$ABS_SEED_FILE:/app/seedFile.txt" \
    "$IMAGE" crawl --config /app/crawl-config.yaml 2>&1 | tee -a "$LOG_FILE"
}

open_monitor() {
  command -v xdg-open >/dev/null || return 0
  ( sleep 3 && xdg-open "http://localhost:9037/" >/dev/null 2>&1 ) &
}

COLLECTION_DIR="crawls/collections/$COLLECTION"

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

  echo "=== Converting archive/ WARC segments to WACZ for $COLLECTION ===" >&2
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
  echo "=== Crawling $COLLECTION (monitor at http://localhost:9037) ===" >&2
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
  "$VENV_PY" "$VALIDATOR_SCRIPT" "$SEED_FILE" "$archive_dir" --output-dir .
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

echo "=== Validating $COLLECTION against $SEED_FILE ===" >&2
if ! run_validator; then
  echo "=== ERROR: validation failed - stopping here rather than risk reporting false success. Check the output above (often an out-of-memory kill on very large crawls), then re-run this script - the crawl itself doesn't need repeating, only validation. ===" >&2
  exit 1
fi

missing_csv="$(ls -t missing_urls_*.csv 2>/dev/null | head -1)"
non200_csv="$(ls -t non_200_urls_*.csv 2>/dev/null | head -1)"

if [[ -z "$missing_csv" || -z "$non200_csv" ]]; then
  echo "=== ERROR: validation reported success but expected CSV files are missing - stopping rather than guessing ===" >&2
  exit 1
fi

PATCH_SEED_FILE="patch-seedFile.txt"
extract_urls "$missing_csv" "$non200_csv" | sort -u > "$PATCH_SEED_FILE"

if [[ -s "$PATCH_SEED_FILE" ]]; then
  patch_count=$(wc -l < "$PATCH_SEED_FILE")
  echo "=== $patch_count URL(s) missing/non-200 - running one patch crawl (depth: 1, same collection) ===" >&2

  cp "$CRAWL_CONFIG" "$PATCH_CONFIG"
  echo "depth: 1" >> "$PATCH_CONFIG"

  ABS_SEED_FILE="$(cd "$(dirname "$PATCH_SEED_FILE")" && pwd)/$(basename "$PATCH_SEED_FILE")"
  open_monitor
  run_crawl "$PATCH_CONFIG"

  echo "=== Re-validating $COLLECTION after patch crawl ===" >&2
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
# Dated + "ICAEW-com" capitalised so the .wacz itself carries the same
# convention as the QA zip (e.g. 20260722-ICAEW-com-logged-in.wacz), rather
# than the lowercase, undated $COLLECTION.wacz used internally elsewhere in
# this script for paths (crawls/collections/$COLLECTION/...).

WACZ_NAME="$(date +%Y%m%d)-ICAEW-com-${COLLECTION#icaew-com-}"
run_warc_processor

# ---- Package seed files + latest CSV reports (not the WACZ/collection, --
# those stay in place under $COLLECTION_DIR for direct use) ----------------

PACKAGE_NAME="$(date +%Y%m%d)-${COLLECTION}-browsertrix-qa"
PACKAGE_DIR="$PACKAGE_NAME"
mkdir -p "$PACKAGE_DIR"

cp "$SEED_FILE" "$PACKAGE_DIR/" 2>/dev/null
[[ -s "$PATCH_SEED_FILE" ]] && cp "$PATCH_SEED_FILE" "$PACKAGE_DIR/"

for pattern in matching_urls_ missing_urls_ non_200_urls_; do
  latest="$(ls -t "${pattern}"*.csv 2>/dev/null | head -1)"
  [[ -n "$latest" ]] && cp "$latest" "$PACKAGE_DIR/"
done

zip -r "${PACKAGE_NAME}.zip" "$PACKAGE_DIR" >/dev/null
rm -rf "$PACKAGE_DIR"

echo "=== Done: ${PACKAGE_NAME}.zip has seed files + CSV reports; $COLLECTION_DIR/$WACZ_NAME.wacz has the WACZ ===" >&2
