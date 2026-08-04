# browsertrix-crawler files and scripts

Custom behaviour scripts for [Browsertrix Crawler](https://github.com/webrecorder/browsertrix-crawler), targeting the ICAEW website, plus helper scripts for inspecting crawl output.

---

## Behaviour scripts (JavaScript)

These are injected into the crawler to handle site-specific interactions during a crawl.

| File | Purpose |
|---|---|
| `icaew-com-behaviors-v4.js` | Current ICAEW behaviour (use this one) |

Older versions (`icaew-com-behaviors-v3.js`, `icaew-com-behaviors-v2.js`, `icaew-com-behaviors-v2-fixed.js`, `icaew-com-behaviors.js`) live in `old behaviors/` for reference.

Reference the behaviour file in your Browsertrix config:

```yaml
behaviors: /path/to/icaew-com-behaviors-v4.js
```

---

## Helper scripts (Python)

### `pages_json_log_validate.py`

Validate a Browsertrix `pages.json` crawl log — checks structure and flags any anomalies.

### `jsonlreader.py`

Read and inspect JSONL log files produced by Browsertrix.

---

## Test / scratch files

`old behaviors/new.js`, `old behaviors/icaew-com-behaviors-vx-test.js`, `test-c-filter-console.js`, `test-icaew-behaviors-snippet.js` are development snippets used when iterating on behaviour scripts. Not for production use.
