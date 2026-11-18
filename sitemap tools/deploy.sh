#!/usr/bin/env bash
# Deploy the sitemap monitor + emailer to a droplet and schedule it with cron.
# Usage: ./deploy.sh user@droplet-ip ["cron schedule"]
set -euo pipefail

HOST="${1:?usage: ./deploy.sh user@host [\"cron schedule\"]}"
SCHEDULE="${2:-0 8 * * *}"   # default: daily at 08:00 (droplet's timezone, usually UTC)
DIR='~/sitemap-monitor'
HERE="$(cd "$(dirname "$0")" && pwd)"

ssh "$HOST" "mkdir -p $DIR"
scp "$HERE/python_emailer.py" "$HERE/sitemap_monitor.py" "$HOST:sitemap-monitor/"
# Gmail API token from gmail_authorise.py (only sent if it exists locally)
[ -f "$HERE/gmail_token.json" ] && scp "$HERE/gmail_token.json" "$HOST:sitemap-monitor/"

# ssh joins args into one remote command string, so quote the schedule for the remote shell
ssh "$HOST" bash -s -- "$(printf %q "$SCHEDULE")" <<'REMOTE'
set -euo pipefail
SCHEDULE="$1"
cd ~/sitemap-monitor
chmod 700 . && chmod 600 python_emailer.py && { [ ! -f gmail_token.json ] || chmod 600 gmail_token.json; }

# Use a venv so we don't touch system Python (Ubuntu blocks pip install system-wide)
if [ ! -x venv/bin/python ]; then
    if ! python3 -m venv venv 2>/dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y -qq python3-venv
        python3 -m venv venv
    fi
fi
venv/bin/pip install -q --upgrade requests

# Install/replace the cron entry (tagged so re-running deploy doesn't duplicate it)
LINE="$SCHEDULE cd $HOME/sitemap-monitor && $HOME/sitemap-monitor/venv/bin/python python_emailer.py >> $HOME/sitemap-monitor/cron.log 2>&1 # sitemap-monitor"
( crontab -l 2>/dev/null | grep -v '# sitemap-monitor$' || true; echo "$LINE" ) | crontab -
echo "Installed cron entry:"; crontab -l | grep '# sitemap-monitor$'
REMOTE
