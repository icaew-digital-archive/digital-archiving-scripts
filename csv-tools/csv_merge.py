import pandas as pd
import sys
import argparse
import os

def normalize_asset_id(asset_id):
    if asset_id and isinstance(asset_id, str):
        if '.' in asset_id:
            return asset_id.rsplit('.', 1)[0]
    return asset_id

def main():
    parser = argparse.ArgumentParser(
        description="Merge multiple CSV files on the assetId column. The first file is the master; all others are left-joined onto it.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python csv_merge.py preservica.csv ai.csv
  python csv_merge.py preservica.csv ai.csv semaphore.csv --output merged.csv
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

    master = dataframes[0]
    master_ids = set(master['assetId'])

    merged = master.copy()
    for df, path in zip(dataframes[1:], args.files[1:]):
        matched = len(master_ids.intersection(set(df['assetId'])))
        print(f"  {os.path.basename(path)}: {matched}/{len(master)} rows matched")
        merged = merged.merge(df, on='assetId', how='left', suffixes=('', '_dup'))
        merged = merged[[c for c in merged.columns if not c.endswith('_dup')]]

    merged.columns = merged.columns.str.replace(r'\.\d+$', '', regex=True)

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
