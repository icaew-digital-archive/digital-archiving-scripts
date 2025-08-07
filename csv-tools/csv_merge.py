import pandas as pd
import sys
import argparse
import os

def normalize_asset_id(asset_id):
    """Normalize asset ID by removing .pdf extension if present"""
    if asset_id and asset_id.endswith('.pdf'):
        return asset_id[:-4]  # Remove .pdf extension
    return asset_id

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(
        description="Merge multiple CSV files based on assetId column",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Merge with default file names in current directory
  python csv_merge.py

  # Merge with custom file paths
  python csv_merge.py --preservica data/preservica.csv --ai data/ai.csv --semaphore data/semaphore.csv --output merged_result.csv

  # Merge with custom output path
  python csv_merge.py --output /path/to/output/merged_data.csv
        """
    )
    
    parser.add_argument(
        '--preservica',
        default='preservica.csv',
        help='Path to preservica CSV file (default: preservica.csv)'
    )
    
    parser.add_argument(
        '--ai',
        default='ai.csv',
        help='Path to AI metadata CSV file (default: ai.csv)'
    )
    
    parser.add_argument(
        '--semaphore',
        default='semaphore.csv',
        help='Path to Semaphore subject CSV file (default: semaphore.csv)'
    )
    
    parser.add_argument(
        '--output',
        default='merged_output.csv',
        help='Path for output merged CSV file (default: merged_output.csv)'
    )
    
    args = parser.parse_args()
    
    # Check if input files exist
    input_files = {
        'preservica': args.preservica,
        'ai': args.ai,
        'semaphore': args.semaphore
    }
    
    for name, filepath in input_files.items():
        if not os.path.exists(filepath):
            print(f"❌ ERROR: '{name}' file not found at '{filepath}'. Aborting.")
            sys.exit(1)
    
    print(f"📁 Loading input files...")
    print(f"  Preservica: {args.preservica}")
    print(f"  AI: {args.ai}")
    print(f"  Semaphore: {args.semaphore}")
    
    # Load input files
    try:
        preservica = pd.read_csv(args.preservica)
        ai = pd.read_csv(args.ai)
        semaphore = pd.read_csv(args.semaphore)
        print("✅ All input files loaded successfully")
    except Exception as e:
        print(f"❌ ERROR: Failed to load one or more input files: {e}")
        sys.exit(1)
    
    # Normalize assetIds in all dataframes
    print("🔄 Normalizing asset IDs...")
    preservica['assetId'] = preservica['assetId'].apply(normalize_asset_id)
    ai['assetId'] = ai['assetId'].apply(normalize_asset_id)
    semaphore['assetId'] = semaphore['assetId'].apply(normalize_asset_id)
    
    # Select only specific columns from preservica.csv
    preservica_columns_to_keep = ['assetId', 'entity.entity_type',
                            'asset.security_tag', 'file_extension']
    
    # Check if required columns exist in preservica
    missing_columns = [col for col in preservica_columns_to_keep if col not in preservica.columns]
    if missing_columns:
        print(f"❌ ERROR: Preservica CSV missing required columns: {missing_columns}")
        sys.exit(1)
    
    preservica = preservica[preservica_columns_to_keep]
    
    # Check 'assetId' exists in ai and semaphore
    for name, df in [("ai.csv", ai), ("semaphore.csv", semaphore)]:
        if 'assetId' not in df.columns:
            print(f"❌ ERROR: '{name}' does not contain 'assetId'. Aborting.")
            sys.exit(1)
    
    # --- Specify columns to DROP ---
    preservica_columns_to_drop = ['SHA256 checksum',
                            'MD5 checksum', 'SHA1 checksum']  # example
    ai_columns_to_drop = ['']
    semaphore_columns_to_drop = ['error']
    
    # --- Apply drops (assetId is always retained) ---
    preservica = preservica.drop(columns=[
                     col for col in preservica_columns_to_drop if col in preservica.columns], errors='ignore')
    ai = ai.drop(columns=[
                       col for col in ai_columns_to_drop if col in ai.columns], errors='ignore')
    semaphore = semaphore.drop(columns=[
                       col for col in semaphore_columns_to_drop if col in semaphore.columns], errors='ignore')
    
    print("🔄 Merging CSV files...")
    
    # --- Merge logic ---
    # Start with preservica dataframe
    merged = preservica.copy()
    
    # Merge with ai using assetId as the key
    merged = merged.merge(ai, on='assetId', how='left', suffixes=('', '_ai'))
    
    # Merge with semaphore using assetId as the key
    merged = merged.merge(semaphore, on='assetId', how='left', suffixes=('', '_semaphore'))
    
    # Remove suffixes from column names
    merged.columns = merged.columns.str.replace(
        '_ai', '').str.replace('_semaphore', '')
    
    # Handle duplicate dc:subject columns by combining them
    print("🔄 Processing duplicate dc:subject columns...")
    subject_columns = [col for col in merged.columns if col.startswith('dc:subject')]
    
    if len(subject_columns) > 1:
        # Combine all dc:subject columns into a single column
        merged['dc:subject'] = merged[subject_columns].apply(
            lambda row: '; '.join([str(val) for val in row if pd.notna(val) and str(val).strip()]), 
            axis=1
        )
        
        # Remove the duplicate columns
        columns_to_drop = [col for col in subject_columns if col != 'dc:subject']
        merged = merged.drop(columns=columns_to_drop)
    
    # --- Save final result ---
    try:
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            print(f"📁 Created output directory: {output_dir}")
        
        merged.to_csv(args.output, index=False)
        print(f"✅ Merged CSV written to: {args.output}")
        print(f"📊 Total rows in merged output: {len(merged)}")
        
        # Print some statistics about the merge
        print(f"📈 Merge statistics:")
        print(f"  - Preservica rows: {len(preservica)}")
        print(f"  - AI rows: {len(ai)}")
        print(f"  - Semaphore rows: {len(semaphore)}")
        print(f"  - Final merged rows: {len(merged)}")
        
        # Check for unmatched rows
        preservica_ids = set(preservica['assetId'])
        ai_ids = set(ai['assetId'])
        semaphore_ids = set(semaphore['assetId'])
        
        ai_matched = len(preservica_ids.intersection(ai_ids))
        semaphore_matched = len(preservica_ids.intersection(semaphore_ids))
        
        print(f"  - AI matches: {ai_matched}/{len(preservica)}")
        print(f"  - Semaphore matches: {semaphore_matched}/{len(preservica)}")
        
    except Exception as e:
        print(f"❌ ERROR: Failed to write output file '{args.output}': {e}")
        sys.exit(1)
    
    print("🎉 Merge completed successfully!")

if __name__ == "__main__":
    main()
