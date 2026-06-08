import pandas as pd
import sys
import argparse
import os
import re

DC_SUBJECT_RE = re.compile(r'^dc:subject(\.\d+)?$')


def normalize_asset_id(asset_id):
    if asset_id and isinstance(asset_id, str):
        if '.' in asset_id:
            return asset_id.rsplit('.', 1)[0]
    return asset_id


def is_dc_subject(col):
    return bool(DC_SUBJECT_RE.match(col))


def get_subject_cols(df):
    return [c for c in df.columns if is_dc_subject(c)]


def dedup_on_asset_id(df, path):
    """
    Drop duplicate assetId rows, keeping the one with the most non-null values.
    Warns if duplicates are found.
    """
    dupes = df[df.duplicated('assetId', keep=False)]
    if dupes.empty:
        return df
    dupe_ids = dupes['assetId'].unique()
    print(f"  WARNING: {os.path.basename(path)} has {len(dupe_ids)} duplicate assetId(s) after normalization — keeping the row with the most non-null values for each.")
    df = df.copy()
    df['_nonnull'] = df.notna().sum(axis=1)
    df = df.sort_values('_nonnull', ascending=False).drop_duplicates('assetId').drop(columns='_nonnull')
    return df


def get_row_subjects(lookup, asset_id, subject_cols):
    """Return list of non-empty subject strings for an asset, or []."""
    if lookup is None or not subject_cols or asset_id not in lookup.index:
        return []
    row = lookup.loc[asset_id]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    return [str(v) for v in row[subject_cols] if pd.notna(v) and str(v).strip()]


def resolve_subjects(merged_df, ai_df, semaphore_df):
    """
    Remove any dc:subject columns from merged_df and rebuild them by combining
    subjects from both sources:
    - Semaphore subjects come first (primary).
    - AI subjects that aren't already in the semaphore list are appended.
    - If semaphore has no subjects for a row, AI subjects are used as fallback.
    """
    ai_subj_cols = get_subject_cols(ai_df) if ai_df is not None else []
    sem_subj_cols = get_subject_cols(semaphore_df) if semaphore_df is not None else []

    ai_lookup = ai_df.set_index('assetId') if ai_df is not None and ai_subj_cols else None
    sem_lookup = semaphore_df.set_index('assetId') if semaphore_df is not None and sem_subj_cols else None

    non_subj_cols = [c for c in merged_df.columns if not is_dc_subject(c)]
    merged_clean = merged_df[non_subj_cols].copy()

    all_subjects = []
    for asset_id in merged_clean['assetId']:
        sem_subjects = get_row_subjects(sem_lookup, asset_id, sem_subj_cols)
        subjects = sem_subjects if sem_subjects else get_row_subjects(ai_lookup, asset_id, ai_subj_cols)
        all_subjects.append(subjects)

    max_subj = max((len(s) for s in all_subjects), default=0)
    if max_subj == 0:
        return merged_clean

    subj_col_names = ['dc:subject'] * max_subj
    subj_rows = [s + [''] * (max_subj - len(s)) for s in all_subjects]
    subj_df = pd.DataFrame(subj_rows, columns=subj_col_names, index=merged_clean.index)

    return pd.concat([merged_clean, subj_df], axis=1)


def merge_dataframes(dataframes, files, subject_merge):
    master = dataframes[0]

    if subject_merge:
        master = master[[c for c in master.columns if not is_dc_subject(c)]]

    master_ids = set(master['assetId'])
    merged = master.copy()

    ai_df = dataframes[1] if len(dataframes) > 1 else None
    sem_df = dataframes[2] if len(dataframes) > 2 else None

    for i, (df, path) in enumerate(zip(dataframes[1:], files[1:]), start=1):
        df = dedup_on_asset_id(df, path)
        matched = len(master_ids.intersection(set(df['assetId'])))
        print(f"  {os.path.basename(path)}: {matched}/{len(master)} rows matched")

        # Only bring in columns that don't already exist in merged
        new_cols = [c for c in df.columns if c != 'assetId' and c not in merged.columns]

        # In subject-merge mode, dc:subject columns for files 2+3 are handled by resolve_subjects
        if subject_merge and i <= 2:
            new_cols = [c for c in new_cols if not is_dc_subject(c)]

        merged = merged.merge(df[['assetId'] + new_cols], on='assetId', how='left')

    if subject_merge:
        merged = resolve_subjects(merged, ai_df, sem_df)

    # Strip .N numeric suffixes from all column names (e.g. dc:creator.1 → dc:creator)
    merged.columns = merged.columns.str.replace(r'\.\d+$', '', regex=True)

    return merged


def main():
    parser = argparse.ArgumentParser(
        description="Merge multiple CSV files on the assetId column. The first file is the master; all others are left-joined onto it.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python csv_merge.py preservica.csv ai.csv
  python csv_merge.py preservica.csv ai.csv semaphore.csv --output merged.csv
  python csv_merge.py preservica.csv ai.csv semaphore.csv --no-subject-merge
        """
    )

    parser.add_argument(
        'files',
        nargs='+',
        help='CSV files to merge (first file is the master)'
    )

    parser.add_argument(
        '--output',
        default='merged_output.csv',
        help='Output file path (default: merged_output.csv)'
    )

    parser.add_argument(
        '--subject-merge',
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            'Subject merge mode (on by default): strips dc:subject from the master, '
            'treats file 2 as AI subjects (fallback) and file 3 as Semaphore subjects (primary — '
            'falls back to AI when a row has no Semaphore subjects). '
            'Use --no-subject-merge to disable.'
        )
    )

    args = parser.parse_args()

    if len(args.files) < 2:
        print("ERROR: Provide at least two CSV files to merge.")
        sys.exit(1)

    master_dir = os.path.dirname(os.path.abspath(args.files[0]))
    if args.output == 'merged_output.csv':
        args.output = os.path.join(master_dir, 'merged_output.csv')

    for path in args.files:
        if not os.path.exists(path):
            print(f"ERROR: File not found: '{path}'")
            sys.exit(1)

    print(f"Loading {len(args.files)} files...")
    try:
        dataframes = [pd.read_csv(f) for f in args.files]
    except Exception as e:
        print(f"ERROR: Failed to load files: {e}")
        sys.exit(1)

    for i, (df, path) in enumerate(zip(dataframes, args.files)):
        if 'assetId' not in df.columns:
            print(f"ERROR: '{path}' is missing the 'assetId' column")
            sys.exit(1)
        dataframes[i]['assetId'] = df['assetId'].apply(normalize_asset_id)

    if args.subject_merge:
        print("Subject merge mode: ON")
        print("  File 1 (master): dc:subject columns will be stripped")
        print(f"  File 2 (AI subjects / fallback): {os.path.basename(args.files[1])}")
        if len(args.files) > 2:
            print(f"  File 3 (Semaphore subjects / primary): {os.path.basename(args.files[2])}")
    else:
        print("Subject merge mode: OFF")

    merged = merge_dataframes(dataframes, args.files, args.subject_merge)

    try:
        output_dir = os.path.dirname(args.output)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        merged.to_csv(args.output, index=False)
        print(f"Merged {len(merged)} rows written to: {os.path.abspath(args.output)}")
    except Exception as e:
        print(f"ERROR: Failed to write output: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
