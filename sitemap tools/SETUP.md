# Droplet setup: sitemap monitor + emailer

Runs `sitemap_monitor.py` daily on a DigitalOcean droplet and emails the output via the Gmail API (DigitalOcean blocks SMTP).

## 1. Gmail API (one-off)

In [Google Cloud Console](https://console.cloud.google.com), signed in as the sending account:

1. Create a project and enable the **Gmail API**.
2. **Branding**: fill in app name, support email, home page and privacy policy URLs.
3. **Audience**: External → **Publish app** (Testing mode expires tokens after 7 days).
4. **Clients**: Create client → **Desktop app** → download as `client_secret.json`.

On your PC (needs a browser):

```bash
python3 gmail_authorise.py client_secret.json   # creates gmail_token.json
```

## 2. Configure

Edit `python_emailer.py`: `from_email`, `to_email`, `cc_emails`, and the sitemap URLs in `script_args`.

## 3. Deploy

```bash
./deploy.sh root@DROPLET_IP              # daily 08:00 UTC
./deploy.sh root@DROPLET_IP "0 8 * * 1"  # or a custom cron schedule
```

Copies the scripts and token to `~/sitemap-monitor/`, installs `requests` in a venv and adds the cron job. Safe to re-run after any change.

## 4. Test

```bash
ssh root@DROPLET_IP 'cd ~/sitemap-monitor && venv/bin/python python_emailer.py'
```

The first run only saves a baseline (`sitemap_memory.json`); new URLs are reported from the next run.

## Troubleshooting

- **Logs:** `~/sitemap-monitor/cron.log` on the droplet.
- **Token error (400 from oauth2.googleapis.com):** rerun `gmail_authorise.py`, then `deploy.sh`.
- **Wrong sender:** the token was approved by another Google account; reauthorise with the right one.

Never commit `client_secret.json` or `gmail_token.json`.
