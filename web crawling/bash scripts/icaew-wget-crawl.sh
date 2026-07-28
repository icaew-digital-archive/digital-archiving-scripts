#!/usr/bin/env bash
#
# Wrapper for the ICAEW.com backup wget crawl (see handbook: admin-guides/web-archiving/wget.html).
# Runs each crawl leg with retry-on-failure, analyzes the logs, then packages
# everything into a single zip for Preservica ingest.
#
# Usage:
#   ./icaew-wget-crawl.sh --sitemap https://www.icaew.com/sitemap_corporate.xml  # build seedFile.txt first, if missing
#   ./icaew-wget-crawl.sh --sitemap https://www.icaew.com/sitemap_corporate.xml --with-media
#   ./icaew-wget-crawl.sh              # reuses an existing seedFile.txt as-is if you already have one
#
# Flags:
#   --with-media                run the optional media crawl leg too
#   --seed URL                   a single URL to add to seedFile.txt - repeatable (--seed url1 --seed url2 ...);
#                                only meaningful for the icaew-com/media legs (subdomains is already recursive)
#   --sitemap URL                sitemap (or sitemap index) URL; bootstraps seedFile.txt if it doesn't exist yet
#   --wait SECONDS               base --wait between every HTTP request (icaew.com's robots.txt asks
#                                for no delay at all, so this is discretionary courtesy, not a
#                                requirement - at scale it adds up: ~29k requests just for the
#                                icaew-com leg means every +0.1s here is ~48 more minutes) (default: 0.5)
#   --log-reader-script PATH    override location of wget_log_reader.py (default: alongside this script)
#   --sitemap-script PATH        override location of sitemap_xml_to_txt_or_html.py (default: alongside this script)
#   --offline                   don't fall back to downloading missing helper scripts from GitHub

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Fallback source for the two helper scripts if not found locally - check
# they're current with any local fixes before relying on this in a hurry.
SCRIPTS_REPO_RAW="https://raw.githubusercontent.com/icaew-digital-archive/digital-archiving-scripts/22db0b1a14dbcfa64231931ddec12dbad7672136"
LOG_READER_URL="$SCRIPTS_REPO_RAW/web%20crawling/wget_log_reader.py"
SITEMAP_SCRIPT_URL="$SCRIPTS_REPO_RAW/sitemap%20tools/sitemap_xml_to_txt_or_html.py"

# sitemap_xml_to_txt_or_html.py needs 'requests'; wget_log_reader.py is pure
# stdlib. This venv is only created/used if that sitemap script actually runs.
VENV_DIR="$SCRIPT_DIR/venv"
VENV_PY="$VENV_DIR/bin/python3"

# ---- Config ------------------------------------------------------------

COOKIES_FILE="cookies.txt"
SEED_FILE="seedFile.txt"
SEED_URLS=()
SITEMAP_INDEX=""
LOG_READER=""
SITEMAP_SCRIPT=""
WAIT_SECONDS=0.5
RETRY_ATTEMPTS=3
OFFLINE=false

# Reference URL list used to score the subdomains crawl (regulation/train/volunteer).
# No canonical list exists for this leg yet - generate one (e.g. with
# sitemap_xml_to_txt_or_html.py against each subdomain's sitemap.xml) and point
# this at it to get CSV reporting + early-exit retries for that leg too.
SUBDOMAINS_URL_LIST=""

RUN_MEDIA_CRAWL=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-media) RUN_MEDIA_CRAWL=true; shift ;;
    --seed) SEED_URLS+=("$2"); shift 2 ;;
    --sitemap) SITEMAP_INDEX="$2"; shift 2 ;;
    --wait) WAIT_SECONDS="$2"; shift 2 ;;
    --log-reader-script) LOG_READER="$2"; shift 2 ;;
    --sitemap-script) SITEMAP_SCRIPT="$2"; shift 2 ;;
    --offline) OFFLINE=true; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done
[[ -z "$LOG_READER" ]] && LOG_READER="$SCRIPT_DIR/wget_log_reader.py"
[[ -z "$SITEMAP_SCRIPT" ]] && SITEMAP_SCRIPT="$SCRIPT_DIR/sitemap_xml_to_txt_or_html.py"

USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

PACKAGE_NAME="$(date +%Y%m%d)-ICAEW-com-logged-in-wget"

COMMON_OPTS=(
  --load-cookies "$COOKIES_FILE"
  --keep-session-cookies
  --page-requisites
  --adjust-extension
  --convert-links
  --restrict-file-names=windows
  --user-agent="$USER_AGENT"
  --wait="$WAIT_SECONDS"
  --random-wait
  --retry-connrefused
  --waitretry=10
  --tries=3
  --timeout=15
  --no-clobber
)

# ---- Prerequisite checks -------------------------------------------------

if [[ ! -s "$COOKIES_FILE" ]]; then
  echo "Missing or empty required file: $COOKIES_FILE" >&2
  exit 1
fi
command -v python3 >/dev/null || { echo "python3 not found" >&2; exit 1; }
command -v zip >/dev/null || { echo "zip not found" >&2; exit 1; }
command -v wget >/dev/null || { echo "wget not found" >&2; exit 1; }
if ! $OFFLINE; then
  command -v curl >/dev/null || { echo "curl not found (needed for GitHub fallback download; pass --offline to skip)" >&2; exit 1; }
fi

# ---- Ensure helper scripts are present, downloading from GitHub as a last
# resort if missing locally (never overwrites an existing local copy). ------

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

# ---- Ensure a venv with 'requests' exists, for sitemap_xml_to_txt_or_html.py.
# wget_log_reader.py is pure stdlib and doesn't need this. Only runs when the
# sitemap script is actually about to be invoked.

ensure_venv() {
  if [[ ! -x "$VENV_PY" ]]; then
    if $OFFLINE; then
      echo "No venv at $VENV_DIR and --offline set - can't create one" >&2
      exit 1
    fi
    echo "=== No venv at $VENV_DIR - creating one ===" >&2
    python3 -m venv "$VENV_DIR"
  fi

  if ! "$VENV_PY" -c "import requests" >/dev/null 2>&1; then
    if $OFFLINE; then
      echo "venv at $VENV_DIR is missing 'requests' and --offline set - can't install" >&2
      exit 1
    fi
    echo "=== Installing 'requests' into $VENV_DIR ===" >&2
    "$VENV_DIR/bin/pip" install --quiet "requests==2.34.2"
  fi
}

ensure_script "$LOG_READER" "$LOG_READER_URL" "wget_log_reader.py"

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
#
# sitemap_xml_to_txt_or_html.py recurses through sitemap indexes on its own,
# so this works whether --sitemap points at a flat urlset or a full index.

if [[ ! -s "$SEED_FILE" && -n "$SITEMAP_INDEX" ]]; then
  ensure_script "$SITEMAP_SCRIPT" "$SITEMAP_SCRIPT_URL" "sitemap_xml_to_txt_or_html.py"
  ensure_venv
  echo "=== Building $SEED_FILE from sitemap: $SITEMAP_INDEX ==="
  "$VENV_PY" "$SITEMAP_SCRIPT" "$SITEMAP_INDEX" --deduplicate --to_file "$SEED_FILE" \
    --exclude_strings "sprint-test-pages" "active-members"
  echo "=== Seed file built: $(wc -l < "$SEED_FILE") URLs ==="
fi

if [[ ! -s "$SEED_FILE" ]]; then
  echo "Missing or empty required file: $SEED_FILE (provide it directly, or pass --sitemap to build it)" >&2
  exit 1
fi

# ---- Retry-aware crawl runner --------------------------------------------
#
# Repeats the same wget invocation up to RETRY_ATTEMPTS times. --no-clobber
# means already-saved files are skipped on later attempts, so each retry only
# spends time on URLs that are still missing or previously failed. Logs are
# appended across attempts; wget_log_reader.py keeps the last entry per URL,
# so analysis always reflects the most recent attempt's outcome.
#
# Args: name  logfile  url_list (may be empty)  wget_args...
run_leg() {
  local name="$1" logfile="$2" urllist="$3"
  shift 3
  local wget_opts=("$@")
  local prev_csvs=()

  : > "$logfile"

  local attempt=1
  while (( attempt <= RETRY_ATTEMPTS )); do
    echo "=== [$name] attempt $attempt/$RETRY_ATTEMPTS ==="
    wget "${COMMON_OPTS[@]}" "${wget_opts[@]}" 2>&1 | tee -a "$logfile"

    if [[ -n "$urllist" ]]; then
      local output missing non200 new_csvs
      output=$(python3 "$LOG_READER" "$logfile" "$urllist")
      echo "$output"

      missing=$(grep -oP 'Missing \(not found\): \K[0-9]+' <<< "$output")
      non200=$(grep -oP 'Non-200 status codes: \K[0-9]+' <<< "$output")
      new_csvs=$(grep '^  - ' <<< "$output" | sed 's/^  - //')

      if (( ${#prev_csvs[@]} > 0 )); then
        rm -f "${prev_csvs[@]}"
      fi
      prev_csvs=($new_csvs)

      if (( missing + non200 == 0 )); then
        echo "=== [$name] all URLs accounted for after attempt $attempt ==="
        break
      fi
    fi

    (( attempt++ ))
  done
}

# ---- Crawl legs -----------------------------------------------------------

run_leg "icaew-com" "icaew-com-wget.log" "$SEED_FILE" \
  --regex-type pcre \
  --reject-regex '((?i)(.*log(?:off|out).*))|((?i)(.*membership\/active-members.*))' \
  -i "$SEED_FILE"

run_leg "subdomains" "subdomains-wget.log" "$SUBDOMAINS_URL_LIST" \
  --recursive \
  --span-hosts \
  --domains regulation.icaew.com,train.icaew.com,volunteer.icaew.com \
  --no-parent \
  --regex-type pcre \
  --reject-regex '((?i)(.*log(?:off|out).*))|(^(?!https:\/\/(train|volunteer)\.icaew\.com\/?(blog\/?.*|article\/?.*|$)).+$)' \
  regulation.icaew.com train.icaew.com volunteer.icaew.com

if $RUN_MEDIA_CRAWL; then
  run_leg "icaew-media" "icaew-media-wget.log" "$SEED_FILE" \
    --recursive \
    --span-hosts \
    --domains icaew.com \
    --no-parent \
    --regex-type pcre \
    --reject-regex '((?i)(.*log(?:off|out).*))|((?i)(.*membership\/active-members.*))' \
    -i "$SEED_FILE"
fi

# ---- Package output ---------------------------------------------------
#
# cookies.txt is deliberately excluded - it's a live session credential and
# has no business being shipped inside the preserved archive package.

echo "=== Packaging output into $PACKAGE_NAME ==="
mkdir -p "$PACKAGE_NAME"

for dir in www.icaew.com regulation.icaew.com train.icaew.com volunteer.icaew.com; do
  [[ -d "$dir" ]] && mv "$dir" "$PACKAGE_NAME"/
done

mv -f ./*-wget.log "$PACKAGE_NAME"/ 2>/dev/null
mv -f ./matching_urls_*.csv ./missing_urls_*.csv ./non_200_urls_*.csv ./redirections_*.csv "$PACKAGE_NAME"/ 2>/dev/null
cp "$SEED_FILE" "$PACKAGE_NAME"/

zip -r "${PACKAGE_NAME}.zip" "$PACKAGE_NAME" >/dev/null
echo "=== Done: ${PACKAGE_NAME}.zip ==="
