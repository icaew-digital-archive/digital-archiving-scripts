# csv-tools

Utilities for merging and scoring metadata CSV files.

---

## `csv_merge.py`

Merge multiple CSV files on the `assetId` column. The first file is the master; subsequent files are left-joined onto it.

```bash
python csv_merge.py <file1.csv> <file2.csv> [more.csv...] [--output merged.csv]
```

| Argument | Description |
|---|---|
| `files` | Two or more CSV files to merge (positional) |
| `--output` | Output file path (default: `merged_output.csv`) |

---

## `score_metadata.py`

Score every asset row in a Preservica export CSV from 0–100 against the ICAEW metadata specification. Outputs a CSV with per-dimension scores and a flag column listing any issues found. Folder rows are skipped.

```bash
python score_metadata.py <input.csv> [--output scores.csv] [--exclude Admin/]
```

| Argument | Description |
|---|---|
| `input_csv` | Preservica full-export CSV to score (required) |
| `--output` / `-o` | Output scores CSV (default: `<input>-scores.csv`) |
| `--exclude` | Skip assets whose `preservica_path` starts with this prefix |

### Scoring dimensions (100 pts total)

| Dimension | Pts | What is checked |
|---|---|---|
| `required_fields` | 40 | 8 required fields × 5 pts each |
| `consistency` | 10 | `entity.title` == `dc:title`, `entity.description` == `dc:description` |
| `date_format` | 10 | `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` |
| `controlled_vocab` | 15 | `dc:type` (5), `icaew:ContentType` (5), `dc:language` (5) |
| `subjects` | 10 | Valid topic names from ICAEW taxonomy; ≤ 10 values |
| `description_quality` | 10 | AI suffix present, description not a stub or placeholder |
| `title_format` | 5 | No `&`, no trailing full stop, starts with uppercase |

### Bonus flags (informational — do not affect score)

These appear in the `flags` column but do not change the numeric score.

| Flag | Meaning |
|---|---|
| `reserved_rights_populated` | `dc:rights` should be empty |
| `reserved_source_populated` | `dc:source` should be empty |
| `reserved_coverage_populated` | `dc:coverage` should be empty |
| `suspect_identifiers:…` | `dc:identifier` values that don't match known patterns |
| `american_spelling_in_desc/title` | American English detected in description or title |
| `whitespace_in:…` | Leading/trailing whitespace in one or more fields |
| `invalid_security_tag:…` | `asset.security_tag` is not `closed`, `open`, or `public` |
| `format_not_lowercase:…` | `dc:format` contains uppercase characters |
| `unrecognised_format:…` | `dc:format` is not a known file extension |
| `creator/publisher/contributor_trailing_period` | Field value ends with a period |
| `creator/publisher/contributor_use_ICAEW_abbreviation` | Full institute name used instead of `ICAEW` |
| `notes_trailing_period` | `icaew:Notes` value ends with a period |
| `non_ascii_in_entity_title/dc_title/dc_desc` | Non-ASCII characters found in text field |

### Subject taxonomy

On each run the script fetches the ICAEW subject taxonomy from the `metadata-extraction` GitHub repo. If the fetch fails, subject names are not validated but the run continues.
