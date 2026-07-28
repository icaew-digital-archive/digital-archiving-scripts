#!/usr/bin/env bash
#
# ICAEW "template crawl" - a quick, disposable test of specific page URLs
# before committing to a full crawl (see handbook:
# admin-guides/web-archiving/browsertrix.html). Uses scopeType: "page-spa",
# so it crawls ONLY the exact URLs in the seed file - no discovery, no scope
# regex needed at all.
#
# Unlike icaew-browsertrix-crawl.sh, there's deliberately no retry loop,
# validation against a seed list, patch crawl, or QA zip here - this is for
# eyeballing whether specific pages render correctly (e.g. a new page
# template/design), not tracking completeness. Run it, then open the
# resulting WACZ in https://replayweb.page/ and look at it.
#
# Browser profile creation is NOT automated. This reuses the SAME profile as
# icaew-browsertrix-crawl.sh's logged-in crawl (crawls/profiles/profile.tar.gz)
# - if you've already created one for that script, it's reused here directly.
#
# Usage:
#   ./icaew-template-browsertrix-crawl.sh --seed https://www.icaew.com/some-new-page-design/
#   ./icaew-template-browsertrix-crawl.sh --seed https://url-one/ --seed https://url-two/
#
# Flags:
#   --seed-file PATH     URL list to crawl (default: template-seedFile.txt)
#   --seed URL           a single URL to test - repeatable (--seed url1 --seed url2 ...);
#                        appends+dedupes into --seed-file, never overwrites it
#   --collection NAME    collection name (default: template-test)
#   --workers N          Browsertrix worker count (default: 6)
#   --offline            don't fall back to pulling the Docker image if missing

set -uo pipefail

CUSTOM_BEHAVIORS_URL="https://raw.githubusercontent.com/icaew-digital-archive/digital-archiving-scripts/22db0b1a14dbcfa64231931ddec12dbad7672136/browsertrix-crawler%20files%20and%20scripts/icaew-com-behaviors-v2.js"
IMAGE="webrecorder/browsertrix-crawler:1.5.11"

# ---- Defaults ------------------------------------------------------------

SEED_FILE="template-seedFile.txt"
SEED_URLS=()
COLLECTION="template-test"
WORKERS=6
OFFLINE=false

# ---- Arg parsing ----------------------------------------------------------

while [[ $# -gt 0 ]]; do
  case "$1" in
    --seed-file) SEED_FILE="$2"; shift 2 ;;
    --seed) SEED_URLS+=("$2"); shift 2 ;;
    --collection) COLLECTION="$2"; shift 2 ;;
    --workers) WORKERS="$2"; shift 2 ;;
    --offline) OFFLINE=true; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

CRAWL_CONFIG="template-crawl-config.yaml"
PROFILE_PATH="crawls/profiles/profile.tar.gz"
LOG_FILE="${COLLECTION}-browsertrix.log"

mkdir -p crawls/profiles crawls/collections

# ---- Prerequisite checks -------------------------------------------------
#
# No python/zip/curl needed here - no validator, no WACZ post-processing,
# no GitHub-hosted helper scripts to fetch. Just Docker.

command -v docker >/dev/null || { echo "docker not found" >&2; exit 1; }

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
# Appends and dedupes rather than overwriting, so re-running with a new
# --seed URL just adds to the existing test list rather than clobbering it.

if [[ "${#SEED_URLS[@]}" -gt 0 ]]; then
  printf '%s\n' "${SEED_URLS[@]}" >> "$SEED_FILE"
  sort -u -o "$SEED_FILE" "$SEED_FILE"
  echo "=== Seed file updated from --seed: now $(wc -l < "$SEED_FILE") URL(s) ===" >&2
fi

if [[ ! -s "$SEED_FILE" ]]; then
  echo "Missing or empty required file: $SEED_FILE (provide --seed-file directly, or use --seed to add specific test URLs)" >&2
  exit 1
fi

# ---- Always include the ICAEW logo SVG in the seed list -------------------
#
# Hardcoded rather than relying on it showing up via --seed/--seed-file -
# added unconditionally (deduped, so re-runs don't create repeat entries)
# so it's always captured regardless of what else is or isn't in
# $SEED_FILE.

echo "https://cdn.icaew.com/v1/production/img/fe-global/logo__icaew.svg" >> "$SEED_FILE"
sort -u -o "$SEED_FILE" "$SEED_FILE"

# ---- Browser profile: can't automate, it's interactive --------------------
# Reuses the same profile as icaew-browsertrix-crawl.sh's logged-in crawl.

if [[ ! -s "$PROFILE_PATH" ]]; then
  ABS_PROFILE_DIR="$(cd crawls/profiles && pwd)"
  {
    echo "=== No browser profile at $PROFILE_PATH ==="
    echo "This step needs a human. Run this:"
    echo
    echo "  docker run -p 6080:6080 -p 9223:9223 \\"
    echo "      -v $ABS_PROFILE_DIR:/crawls/profiles/ \\"
    echo "      -it $IMAGE \\"
    echo "      create-login-profile --url \"https://my.icaew.com/security/Account/Login\""
    echo
    echo "Then, in order:"
    echo "  1. Open Chrome and navigate to http://localhost:9223/"
    echo "  2. Click \"Allow all cookies\""
    echo "  3. Disable Brave shields"
    echo "  4. Login with your credentials"
    echo "  5. Disable Brave shields again (if prompted)"
    echo "  6. Close the \"Discover the latest MyICAEW App\" banner"
    echo "  7. Navigate to a page with a StreamAMG video player, e.g."
    echo "     https://www.icaew.com/for-current-aca-students/training-agreement/your-online-training-file-guide/online-training-file-videos"
    echo "  8. Verify that the video element loads correctly"
    echo "  9. Click \"Create Profile\""
    echo
    echo "Then re-run this script - it'll find the profile and continue."
  } >&2
  exit 1
fi

# ---- Generate crawl-config.yaml if missing (page-spa: exact URLs only) --

if [[ ! -s "$CRAWL_CONFIG" ]]; then
  cat > "$CRAWL_CONFIG" <<EOF
# For additional configuration options, see https://crawler.docs.browsertrix.com/user-guide/yaml-crawl-config/
# Generated by icaew-template-browsertrix-crawl.sh - template crawl for testing specific page designs

profile: /crawls/profiles/profile.tar.gz
seedFile: /app/seedFile.txt
collection: $COLLECTION
screencastPort: 9037
customBehaviors: $CUSTOM_BEHAVIORS_URL

allowHashUrls: true
combineWARC: true
generateWACZ: true
workers: $WORKERS
text:
  - to-warc
diskUtilization: 0

scopeType: "page-spa"
EOF
  echo "=== Generated $CRAWL_CONFIG ===" >&2
fi

# ---- Run the crawl ---------------------------------------------------

ABS_CRAWLS_DIR="$(cd crawls && pwd)"
ABS_CRAWL_CONFIG="$(cd "$(dirname "$CRAWL_CONFIG")" && pwd)/$(basename "$CRAWL_CONFIG")"
ABS_SEED_FILE="$(cd "$(dirname "$SEED_FILE")" && pwd)/$(basename "$SEED_FILE")"

open_monitor() {
  command -v xdg-open >/dev/null || return 0
  ( sleep 3 && xdg-open "http://localhost:9037/" >/dev/null 2>&1 ) &
}

echo "=== Running template crawl '$COLLECTION' (monitor at http://localhost:9037) ===" >&2
open_monitor
docker run -p 9037:9037 \
  -v "$ABS_CRAWLS_DIR:/crawls" \
  -v "$ABS_CRAWL_CONFIG:/app/crawl-config.yaml" \
  -v "$ABS_SEED_FILE:/app/seedFile.txt" \
  "$IMAGE" crawl --config /app/crawl-config.yaml 2>&1 | tee -a "$LOG_FILE"

echo "=== Done: open crawls/collections/$COLLECTION/$COLLECTION.wacz in https://replayweb.page/ to check the pages rendered correctly ===" >&2
