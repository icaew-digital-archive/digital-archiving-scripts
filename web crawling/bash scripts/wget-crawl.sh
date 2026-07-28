#!/usr/bin/env bash
#
# Generic backup wget crawl wrapper - same retry/packaging pattern as
# icaew-wget-crawl.sh, but parameterized for any single site rather than
# hardcoded to icaew.com. Each site gets its own workspace under sites/<label>/
# so artifacts from different crawls never collide.
#
# Usage:
#   ./wget-crawl.sh --url https://www.ccab.org.uk/ \
#                    --sitemap https://www.ccab.org.uk/sitemap_index.xml
#
#   ./wget-crawl.sh --url https://example.com/ --recursive   # no sitemap available
#
# Flags:
#   --url URL           site start URL (required)
#   --label NAME         short name for the workspace dir / package (default: derived from host)
#   --seed-file PATH     URL list for a non-recursive crawl (default: sites/<label>/seedFile.txt)
#   --seed URL           a single URL to crawl - repeatable (--seed url1 --seed url2 ...); writes
#                        them into --seed-file, so validation/patch-crawl still work normally
#   --sitemap URL        sitemap *index* URL; bootstraps --seed-file if it doesn't exist yet
#   --cookies PATH       cookies.txt for authenticated crawls (default: none - public crawl)
#   --recursive          crawl recursively from --url instead of using a seed list
#   --domains LIST       comma-separated --domains override (default: derived from --url's host)
#   --reject-regex REGEX PCRE passed to --reject-regex (default: none)
#   --wait SECONDS       base --wait between *every* HTTP request wget makes,
#                        including each individual page-requisite (css/js/image),
#                        not just each page - a site's robots.txt Crawl-delay is
#                        normally meant for page-to-page pacing, so treat that
#                        value as an upper bound, not a default to copy in as-is (default: 1)
#   --retries N          retry attempts per leg (default: 3)
#   --log-reader-script PATH   override location of wget_log_reader.py (default: alongside this script)
#   --sitemap-script PATH      override location of sitemap_xml_to_txt_or_html.py (default: alongside this script)
#   --offline                  don't fall back to downloading missing helper scripts from GitHub

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

# ---- Defaults ------------------------------------------------------------

TARGET_URL=""
LABEL=""
SEED_FILE=""
SEED_URLS=()
SITEMAP_INDEX=""
COOKIES_FILE=""
RECURSIVE=false
DOMAINS=""
REJECT_REGEX=""
WAIT_SECONDS=1
RETRY_ATTEMPTS=3
LOG_READER=""
SITEMAP_SCRIPT=""
OFFLINE=false
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

# ---- Arg parsing ----------------------------------------------------------

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url) TARGET_URL="$2"; shift 2 ;;
    --label) LABEL="$2"; shift 2 ;;
    --seed-file) SEED_FILE="$2"; shift 2 ;;
    --seed) SEED_URLS+=("$2"); shift 2 ;;
    --sitemap) SITEMAP_INDEX="$2"; shift 2 ;;
    --cookies) COOKIES_FILE="$2"; shift 2 ;;
    --recursive) RECURSIVE=true; shift ;;
    --domains) DOMAINS="$2"; shift 2 ;;
    --reject-regex) REJECT_REGEX="$2"; shift 2 ;;
    --wait) WAIT_SECONDS="$2"; shift 2 ;;
    --retries) RETRY_ATTEMPTS="$2"; shift 2 ;;
    --log-reader-script) LOG_READER="$2"; shift 2 ;;
    --sitemap-script) SITEMAP_SCRIPT="$2"; shift 2 ;;
    --offline) OFFLINE=true; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

[[ -z "$TARGET_URL" && "${#SEED_URLS[@]}" -gt 0 ]] && TARGET_URL="${SEED_URLS[0]}"
[[ -z "$TARGET_URL" ]] && { echo "--url is required (or provide --seed URL to derive it)" >&2; exit 1; }

HOST="$(sed -E 's#^[a-zA-Z]+://##; s#/.*##' <<< "$TARGET_URL")"
BARE_HOST="${HOST#www.}"

[[ -z "$LABEL" ]] && LABEL="$(tr '.' '-' <<< "$BARE_HOST")"
[[ -z "$DOMAINS" ]] && DOMAINS="$HOST,$BARE_HOST"

WORKDIR="sites/$LABEL"
[[ -z "$SEED_FILE" ]] && SEED_FILE="$WORKDIR/seedFile.txt"
LOG_FILE="$WORKDIR/${LABEL}-wget.log"
[[ -z "$LOG_READER" ]] && LOG_READER="$SCRIPT_DIR/wget_log_reader.py"
[[ -z "$SITEMAP_SCRIPT" ]] && SITEMAP_SCRIPT="$SCRIPT_DIR/sitemap_xml_to_txt_or_html.py"

mkdir -p "$WORKDIR"

command -v python3 >/dev/null || { echo "python3 not found" >&2; exit 1; }
command -v zip >/dev/null || { echo "zip not found" >&2; exit 1; }
command -v wget >/dev/null || { echo "wget not found" >&2; exit 1; }
if ! $OFFLINE; then
  command -v curl >/dev/null || { echo "curl not found (needed for GitHub fallback downloads; pass --offline to skip)" >&2; exit 1; }
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
# sitemap script is actually about to be invoked, and never touches an
# existing venv beyond installing the one package it's missing.

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
# Appends and dedupes rather than overwriting, so this never clobbers an
# existing seed file (e.g. one already built via --sitemap on a prior run).
# Once written, this is just a normal seed file - validation and the one
# patch-crawl-if-needed step work exactly as with a hand-built seedFile.txt.

if [[ "${#SEED_URLS[@]}" -gt 0 ]]; then
  printf '%s\n' "${SEED_URLS[@]}" >> "$SEED_FILE"
  sort -u -o "$SEED_FILE" "$SEED_FILE"
  echo "=== Seed file updated from --seed: now $(wc -l < "$SEED_FILE") URL(s) ===" >&2
fi

# ---- Optional: bootstrap seed file from a sitemap (or sitemap index) ----
#
# sitemap_xml_to_txt_or_html.py recurses through sitemap indexes on its own,
# so this works whether --sitemap points at a flat urlset or a full index.

if [[ ! -s "$SEED_FILE" && -n "$SITEMAP_INDEX" ]]; then
  ensure_script "$SITEMAP_SCRIPT" "$SITEMAP_SCRIPT_URL" "sitemap_xml_to_txt_or_html.py"
  ensure_venv
  echo "=== Building $SEED_FILE from sitemap: $SITEMAP_INDEX ==="
  "$VENV_PY" "$SITEMAP_SCRIPT" "$SITEMAP_INDEX" --deduplicate --to_file "$SEED_FILE"
  echo "=== Seed file built: $(wc -l < "$SEED_FILE") URLs ==="
fi

if ! $RECURSIVE && [[ ! -s "$SEED_FILE" ]]; then
  echo "No seed file at $SEED_FILE and --recursive not set. Provide --seed-file, --sitemap, or --recursive." >&2
  exit 1
fi

# ---- Build wget options ---------------------------------------------------

COMMON_OPTS=(
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

if [[ -n "$COOKIES_FILE" && -s "$COOKIES_FILE" ]]; then
  COMMON_OPTS+=(--load-cookies "$COOKIES_FILE" --keep-session-cookies)
fi

if [[ -n "$REJECT_REGEX" ]]; then
  COMMON_OPTS+=(--regex-type pcre --reject-regex "$REJECT_REGEX")
fi

if $RECURSIVE; then
  CRAWL_ARGS=(--recursive --span-hosts --domains "$DOMAINS" --no-parent "$TARGET_URL")
  URL_LIST=""   # no reference list to score a recursive crawl against
else
  CRAWL_ARGS=(--span-hosts --domains "$DOMAINS" -i "$SEED_FILE")
  URL_LIST="$SEED_FILE"
fi

# ---- Retry-aware crawl (same pattern as icaew-wget-crawl.sh) ---------------
#
# --no-clobber means re-running the identical command skips already-saved
# files, so each retry only spends time on URLs still missing/failed.
# wget_log_reader.py keeps the last log entry per URL, so appending each
# attempt's output to the same log always reflects the latest outcome.

: > "$LOG_FILE"
prev_csvs=()
attempt=1
while (( attempt <= RETRY_ATTEMPTS )); do
  echo "=== [$LABEL] attempt $attempt/$RETRY_ATTEMPTS ==="
  wget "${COMMON_OPTS[@]}" "${CRAWL_ARGS[@]}" 2>&1 | tee -a "$LOG_FILE"

  if [[ -n "$URL_LIST" ]]; then
    output=$(python3 "$LOG_READER" "$LOG_FILE" "$URL_LIST")
    echo "$output"
    missing=$(grep -oP 'Missing \(not found\): \K[0-9]+' <<< "$output")
    non200=$(grep -oP 'Non-200 status codes: \K[0-9]+' <<< "$output")
    mapfile -t new_csvs < <(grep '^  - ' <<< "$output" | sed 's/^  - //')

    rm -f "${prev_csvs[@]}"
    prev_csvs=()
    for f in "${new_csvs[@]}"; do
      mv -f "$f" "$WORKDIR/$f"
      prev_csvs+=("$WORKDIR/$f")
    done

    if (( missing + non200 == 0 )); then
      echo "=== [$LABEL] all URLs accounted for after attempt $attempt ==="
      break
    fi
  fi

  (( attempt++ ))
done

# ---- Package output --------------------------------------------------
#
# Cookies are deliberately excluded from the package - they're a live
# session credential, not archival content.

PACKAGE_NAME="$(date +%Y%m%d)-${LABEL}-wget"
echo "=== Packaging output into $PACKAGE_NAME ==="

for dir in ./*"$BARE_HOST"/; do
  [[ -d "$dir" ]] && mv "$dir" "$WORKDIR/"
done

cp -n "$SEED_FILE" "$WORKDIR/$(basename "$SEED_FILE")" 2>/dev/null

mv "$WORKDIR" "$PACKAGE_NAME"
zip -r "${PACKAGE_NAME}.zip" "$PACKAGE_NAME" >/dev/null
echo "=== Done: ${PACKAGE_NAME}.zip ==="
