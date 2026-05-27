#!/usr/bin/env python3
"""
Metadata quality scorer for ICAEW Preservica export CSV.
Grades each ASSET row 0-100 against the metadata specification.

Works with full Preservica exports (from a_get_metadata.py) and with merged
metadata CSVs. Columns are accessed by name so column order does not matter.
If entity.entity_type is present, only rows with EntityType.ASSET are scored;
if absent, all rows are scored.

Usage:
    python3 score_metadata.py <input.csv> [--output scores.csv] [--exclude Admin/]

Scoring dimensions (max 100 pts total):
    required_fields     40  (5 pts each x 8 required fields)
    consistency         10  (entity.title == dc:title, entity.description == dc:description)
    date_format         10  (YYYY, YYYY-MM, or YYYY-MM-DD)
    controlled_vocab    15  (dc:type 5, icaew:ContentType 5, dc:language 5)
    subjects            10  (valid topic names, <= 10 values)
    description_quality 10  (AI suffix present, not a stub/placeholder)
    title_format         5  (no &, no trailing full stop, starts uppercase)
"""

import argparse
import csv
import re
import sys
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------
DCMI_TYPES = {
    "Text", "Moving Image", "Still Image", "Sound",
    "Dataset", "Interactive Resource", "Collection",
}

ICAEW_CONTENT_TYPES = {
    "Annual report", "Article", "Biographical profile", "Company profile",
    "Course", "Database", "eBook", "eBook chapter", "Event", "Form",
    "Helpsheets and support", "Hub page", "ICAEW consultation and response",
    "Industry profile", "Internal ICAEW policy", "Journal", "Learning material",
    "Legal precedent", "Library book", "Library journal", "Listing",
    "Member reward", "Minutes and board papers", "Newsletter", "No content type",
    "Podcast", "Press release", "Promotional material", "Regional news",
    "Regulations", "Report", "Representation", "Research guide",
    "Speech or presentation", "Technical release", "Thought leadership report",
    "Transcript", "Video", "Webinar", "Website",
}

# American English spellings that should be British — derived from icaew.yaml profile
AMERICAN_SPELLINGS = re.compile(
    r'\b('
    # -ize verbs (should be -ise)
    r'organiz|recogniz|analyz|optimiz|prioritiz|finaliz|summariz|standardiz|'
    r'minimiz|maximiz|realiz|specializ|authoriz|categoriz|characteriz|emphasiz|'
    r'criticiz|apologiz|memoriz|visualiz'
    r'|'
    # -or endings (should be -our)
    r'color|behavior|honor|labor|favor|harbor|neighbor'
    r'|'
    # -er endings (should be -re)
    r'center|centers'
    r'|'
    # -ense endings (should be -ence)
    r'defense|offense'
    r'|'
    # -og endings (should be -ogue)
    r'catalog|dialog|analog'
    r'|'
    # -gram (should be programme when schedule/plan — flag conservatively)
    r'program(?!me)'
    r'|'
    # double-l / single-l differences
    r'enrollment|fulfill|skillful|traveled|canceled|labeled|modeled|modeled|'
    r'modeling|traveling|counselor|counseled'
    r'|'
    # specific words
    r'jewelry|gray|maneuver|skeptical|pajamas'
    r')\b',
    re.IGNORECASE,
)

ISO_DATE_IN_TITLE = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')

# Valid identifier patterns: ISBN, full URL, or ICAEW reference code
IDENTIFIER_PATTERN = re.compile(
    r'^('
    r'ISBN\s+[\d\-X]+'
    r'|https?://\S+'
    r'|www\.\S+'
    r'|[A-Z][A-Z0-9]*(?:\s+[A-Z0-9]+)*[\s/\-][A-Z0-9/\-]+'
    r'|[A-Z]{2,}\d{3,}'
    r')$',
    re.IGNORECASE,
)

DATE_PATTERN = re.compile(r'^\d{4}(-(?:0[1-9]|1[0-2])(-(?:0[1-9]|[12]\d|3[01]))?)?$')

ISO_LANG_PATTERN = re.compile(r'^[a-z]{2}(-[A-Z]{2})?$')

VALID_SECURITY_TAGS = {"closed", "open", "public"}

VALID_EXTENSIONS = {
    "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt", "txt", "srt",
    "jpg", "jpeg", "png", "tiff", "tif", "gif", "bmp",
    "mp4", "mkv", "avi", "mov", "mp3", "wav",
    "html", "htm", "xml", "json", "csv", "wacz",
}

ICAEW_FULL_NAME = "Institute of Chartered Accountants in England and Wales"

# Fields checked for leading/trailing whitespace (bonus flag only)
WHITESPACE_FIELDS = [
    "dc:title", "dc:description", "dc:creator", "dc:subject",
    "dc:publisher", "dc:date", "dc:type", "dc:format", "dc:language",
    "dc:relation", "dc:contributor", "dc:identifier",
    "icaew:ContentType", "icaew:Notes",
]

# ---------------------------------------------------------------------------
# Row helpers
# ---------------------------------------------------------------------------

def build_row_dict(raw_row: list[str], header_to_indices: dict) -> dict[str, list[str]]:
    """Build {field: [raw_values]} from a CSV row, preserving raw whitespace."""
    return {
        field: [raw_row[i] for i in indices if i < len(raw_row)]
        for field, indices in header_to_indices.items()
    }


def vals(row: dict[str, list[str]], field: str) -> list[str]:
    """Return non-empty stripped values for a named field."""
    return [v.strip() for v in row.get(field, []) if v.strip()]


def first(row: dict[str, list[str]], field: str) -> str:
    """Return the first non-empty stripped value for a field, or ''."""
    v = vals(row, field)
    return v[0] if v else ""


# ---------------------------------------------------------------------------
# Subject taxonomy
# ---------------------------------------------------------------------------

def load_valid_subjects() -> set[str]:
    """
    Fetch the ICAEW subject taxonomy from topic_list.txt on GitHub.
    Returns an empty set on failure (subject names will not be validated).
    """
    url = (
        "https://raw.githubusercontent.com/icaew-digital-archive/"
        "metadata-extraction/refs/heads/main/topic_list.txt"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            content = resp.read().decode("utf-8")
        topics = {
            line.strip()[2:]
            for line in content.splitlines()
            if line.strip().startswith("- ")
        }
        print(f"  Loaded {len(topics)} subject topics.", file=sys.stderr)
        return topics
    except Exception as exc:
        print(
            f"  Warning: could not load subject taxonomy ({exc}). "
            f"Subject names will not be validated.",
            file=sys.stderr,
        )
        return set()


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

def score_asset(row: dict[str, list[str]], valid_subjects: set[str]) -> tuple[int, dict, list[str]]:
    scores: dict[str, int] = {}
    flags:  list[str]      = []

    # Convenience locals
    entity_title = first(row, "entity.title")
    entity_desc  = first(row, "entity.description")
    dc_title     = vals(row, "dc:title")[0] if vals(row, "dc:title") else ""
    dc_desc      = first(row, "dc:description")

    # ---- 1. Required field presence (5 pts each, max 40) -------------------
    required = {
        "title":       bool(vals(row, "dc:title")),
        "description": bool(dc_desc),
        "creator":     bool(vals(row, "dc:creator")),
        "publisher":   bool(vals(row, "dc:publisher")),
        "date":        bool(vals(row, "dc:date")),
        "type":        bool(vals(row, "dc:type")),
        "format":      bool(first(row, "dc:format")),
        "language":    bool(vals(row, "dc:language")),
    }
    scores["required_fields"] = sum(required.values()) * 5
    for field, present in required.items():
        if not present:
            flags.append(f"missing_{field}")

    # ---- 2. entity.title / entity.description consistency (5 pts each) ----
    title_consistent = entity_title == dc_title
    desc_consistent  = entity_desc  == dc_desc

    scores["consistency"] = (5 if title_consistent else 0) + (5 if desc_consistent else 0)
    if not title_consistent:
        flags.append("entity_title_mismatch")
    if not desc_consistent:
        flags.append("entity_desc_mismatch")

    # ---- 3. Date format (10 pts) -------------------------------------------
    dates = vals(row, "dc:date")
    if not dates:
        date_ok = False
    else:
        date_ok = all(DATE_PATTERN.match(d) for d in dates)
    scores["date_format"] = 10 if date_ok else 0
    if dates and not date_ok:
        flags.append(f"invalid_date_format:{dates[0]}")

    # ---- 4. Controlled vocabulary (5 pts each, max 15) ---------------------
    dc_types = vals(row, "dc:type")
    type_ok  = bool(dc_types) and dc_types[0] in DCMI_TYPES

    ct_value = first(row, "icaew:ContentType")
    ct_ok    = (not ct_value) or (ct_value in ICAEW_CONTENT_TYPES)

    languages = vals(row, "dc:language")
    lang_ok   = bool(languages) and all(ISO_LANG_PATTERN.match(l) for l in languages)

    scores["controlled_vocab"] = (
        (5 if type_ok else 0) +
        (5 if ct_ok   else 0) +
        (5 if lang_ok else 0)
    )
    if dc_types and not type_ok:
        flags.append(f"invalid_dc_type:{dc_types[0]}")
    if ct_value and not ct_ok:
        flags.append(f"invalid_content_type:{ct_value}")
    if languages and not lang_ok:
        flags.append(f"invalid_language:{languages[0]}")

    # ---- 5. Subjects (10 pts) ----------------------------------------------
    subjects = vals(row, "dc:subject")
    if not subjects:
        scores["subjects"] = 10
    elif len(subjects) > 10:
        scores["subjects"] = 0
        flags.append(f"too_many_subjects:{len(subjects)}")
    elif valid_subjects:
        bad = [s for s in subjects if s not in valid_subjects]
        if bad:
            scores["subjects"] = 5
            flags.append("invalid_subject_names:" + "|".join(bad[:3]))
        else:
            scores["subjects"] = 10
    else:
        scores["subjects"] = 10

    # ---- 6. Description quality (10 pts) -----------------------------------
    desc     = dc_desc
    filename = first(row, "filename")
    has_ai_suffix   = desc.endswith("(AI generated description)")
    not_placeholder = (
        len(desc) > 80
        and desc != filename
        and not desc.startswith(filename.split(".")[0] if filename else "\x00")
    )

    scores["description_quality"] = (
        (5 if has_ai_suffix   else 0) +
        (5 if not_placeholder else 0)
    )
    if desc and not has_ai_suffix:
        flags.append("missing_ai_suffix")
    if desc and not not_placeholder:
        flags.append("description_placeholder_or_stub")

    # ---- 7. Title format (5 pts) -------------------------------------------
    if not dc_title:
        scores["title_format"] = 0
    else:
        no_amp      = "&" not in dc_title
        no_dot      = not dc_title.endswith(".")
        upper_start = dc_title[0].isupper()
        scores["title_format"] = (
            (2 if no_amp      else 0) +
            (2 if no_dot      else 0) +
            (1 if upper_start else 0)
        )
        if not no_amp:
            flags.append("title_contains_ampersand")
        if not no_dot:
            flags.append("title_trailing_fullstop")
        if not upper_start:
            flags.append("title_lowercase_start")

    # ---- Bonus flags (informational only, do not affect score) -------------

    # Reserved fields should be empty
    if vals(row, "dc:rights"):
        flags.append("reserved_rights_populated")
    if vals(row, "dc:source"):
        flags.append("reserved_source_populated")
    if first(row, "dc:coverage"):
        flags.append("reserved_coverage_populated")

    # Identifiers against known pattern
    bad_ids = [i for i in vals(row, "dc:identifier") if not IDENTIFIER_PATTERN.match(i)]
    if bad_ids:
        flags.append("suspect_identifiers:" + "|".join(bad_ids[:3]))

    # Description must end with . or ? before the AI suffix
    if dc_desc and dc_desc.endswith("(AI generated description)"):
        text_before_suffix = dc_desc[: dc_desc.rfind("(AI generated description)")].strip()
        if text_before_suffix and not (text_before_suffix.endswith(".") or text_before_suffix.endswith("?")):
            flags.append("description_missing_period_before_ai_suffix")

    # Title should not contain ISO date format (use readable dates instead)
    if dc_title and ISO_DATE_IN_TITLE.search(dc_title):
        flags.append("title_contains_iso_date")

    # American English in description and title
    for field_name, text in [("desc", dc_desc), ("title", dc_title)]:
        if text and AMERICAN_SPELLINGS.search(text):
            flags.append(f"american_spelling_in_{field_name}")

    # Leading/trailing whitespace in metadata fields
    ws_fields = []
    for field_name in WHITESPACE_FIELDS:
        for v in row.get(field_name, []):
            if v and v != v.strip():
                ws_fields.append(field_name)
                break
    if ws_fields:
        flags.append("whitespace_in:" + "|".join(ws_fields))

    # Security tag
    security_tag = first(row, "asset.security_tag")
    if security_tag and security_tag not in VALID_SECURITY_TAGS:
        flags.append(f"invalid_security_tag:{security_tag}")

    # Format extension
    fmt = first(row, "dc:format")
    if fmt:
        if fmt != fmt.lower():
            flags.append(f"format_not_lowercase:{fmt}")
        elif fmt not in VALID_EXTENSIONS:
            flags.append(f"unrecognised_format:{fmt}")

    # Creator / publisher / contributor: trailing period or full ICAEW name
    for field_label, field_name in [
        ("creator",     "dc:creator"),
        ("publisher",   "dc:publisher"),
        ("contributor", "dc:contributor"),
    ]:
        for v in vals(row, field_name):
            if v.endswith("."):
                flags.append(f"{field_label}_trailing_period")
                break
            if ICAEW_FULL_NAME in v:
                flags.append(f"{field_label}_use_ICAEW_abbreviation")
                break

    # Notes: no trailing period
    for note in vals(row, "icaew:Notes"):
        if note.endswith("."):
            flags.append("notes_trailing_period")
            break

    # Non-ASCII characters in key text fields
    for field_label, text in [
        ("entity_title", entity_title),
        ("dc_title",     dc_title),
        ("dc_desc",      dc_desc),
    ]:
        if text and any(ord(c) > 127 for c in text):
            flags.append(f"non_ascii_in_{field_label}")

    total = sum(scores.values())
    return total, scores, flags


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score ICAEW Preservica export CSV rows 0–100 against the metadata specification.",
        epilog="Example: python score_metadata.py export.csv --output scores.csv --exclude Admin/",
    )
    parser.add_argument("input_csv", help="Preservica full-export CSV to score")
    parser.add_argument(
        "--output", "-o",
        metavar="OUTPUT_CSV",
        help="Output scores CSV (default: <input>-scores.csv)",
    )
    parser.add_argument(
        "--exclude",
        metavar="PREFIX",
        help="Skip assets whose preservica_path starts with this prefix (e.g. 'Admin/')",
    )
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    if not input_path.exists():
        parser.error(f"Input file not found: {input_path}")

    output_path    = Path(args.output) if args.output else input_path.with_stem(input_path.stem + "-scores")
    exclude_prefix = args.exclude

    print("Loading subject taxonomy…", file=sys.stderr)
    valid_subjects = load_valid_subjects()

    out_fields = [
        "assetId", "filename", "preservica_path", "total_score",
        "required_fields", "consistency", "date_format",
        "controlled_vocab", "subjects", "description_quality", "title_format",
        "flags",
    ]

    total_assets = 0
    skipped = 0
    score_buckets = {"0-24": 0, "25-49": 0, "50-74": 0, "75-89": 0, "90-100": 0}

    print(f"Scoring {input_path.name}…", file=sys.stderr)
    if exclude_prefix:
        print(f"  Excluding paths starting with: {exclude_prefix!r}", file=sys.stderr)

    with (
        open(input_path,  encoding="utf-8-sig", newline="") as infile,
        open(output_path, encoding="utf-8",     newline="", mode="w") as outfile,
    ):
        reader = csv.reader(infile)
        headers = next(reader)

        # Build {field_name: [col_indices]} to handle duplicate column names
        header_to_indices: dict[str, list[int]] = {}
        for i, h in enumerate(headers):
            header_to_indices.setdefault(h, []).append(i)

        writer = csv.DictWriter(outfile, fieldnames=out_fields)
        writer.writeheader()

        for raw_row in reader:
            row = build_row_dict(raw_row, header_to_indices)

            # Filter by entity type if the column is present
            entity_type = first(row, "entity.entity_type")
            if entity_type and entity_type != "EntityType.ASSET":
                continue

            # Apply exclude prefix if preservica_path is present
            path = first(row, "preservica_path")
            if exclude_prefix and path and path.startswith(exclude_prefix):
                skipped += 1
                continue

            total, scores, flags = score_asset(row, valid_subjects)

            writer.writerow({
                "assetId":         first(row, "assetId"),
                "filename":        first(row, "filename"),
                "preservica_path": path,
                "total_score":     total,
                **scores,
                "flags":           "; ".join(flags),
            })
            total_assets += 1

            if   total <= 24:  score_buckets["0-24"]   += 1
            elif total <= 49:  score_buckets["25-49"]  += 1
            elif total <= 74:  score_buckets["50-74"]  += 1
            elif total <= 89:  score_buckets["75-89"]  += 1
            else:              score_buckets["90-100"] += 1

    if skipped:
        print(f"  Skipped {skipped} assets matching exclude prefix.", file=sys.stderr)
    print(f"\nDone. {total_assets} assets scored → {output_path.name}", file=sys.stderr)
    print("Score distribution:", file=sys.stderr)
    for band, count in score_buckets.items():
        pct = count / total_assets * 100 if total_assets else 0
        print(f"  {band:>7}  {count:5}  ({pct:.1f}%)", file=sys.stderr)


if __name__ == "__main__":
    main()
