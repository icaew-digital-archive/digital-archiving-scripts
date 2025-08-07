import pandas as pd
import sys

# Load input files
preservica = pd.read_csv("preservica.csv") # Should be a_get_metadata.py output
ai = pd.read_csv("ai.csv") # Should be AI metadata output
semaphore = pd.read_csv("semaphore.csv") # Should be Semaphore subject output

# Select only specific columns from preservica.csv
preservica_columns_to_keep = ['assetId', 'entity.entity_type',
                        'asset.security_tag', 'file_extension']
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

# Rename all dc:subject.X columns to just dc:subject
merged.columns = merged.columns.str.replace(
    r'dc:subject\.\d+', 'dc:subject', regex=True)

# --- Save final result ---
merged.to_csv("merged_output.csv", index=False)

print("✅ Merged CSV written with specified columns dropped and duplicate names allowed.")
