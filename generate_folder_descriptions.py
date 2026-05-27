#!/usr/bin/env python3
"""
Generate descriptions for each folder in the ICAEW Digital Archive export.
Reads the CSV and creates human-readable descriptions based on available metadata.
"""

import csv
import sys
from pathlib import Path


def generate_description(row):
    """
    Generate a description for a folder based on its metadata.
    
    Args:
        row: Dictionary containing folder metadata
        
    Returns:
        str: Human-readable description
    """
    title = row.get('entity.title', '').strip()
    description = row.get('entity.description', '').strip()
    path = row.get('preservica_path', '').strip()
    security_tag = row.get('asset.security_tag', '').strip()
    dc_identifier = row.get('dc:identifier', '').strip()
    
    # Start building the description
    desc_parts = []
    
    # If there's already a description, use it as the primary description
    if description:
        desc_parts.append(description)
    
    # Add context about the folder structure
    if path:
        # Extract meaningful path information
        path_parts = path.split('/')
        if len(path_parts) > 1:
            # Get the parent folder context
            parent_context = path_parts[-2] if len(path_parts) > 1 else ""
            if parent_context and parent_context != title:
                desc_parts.append(f"Located in: {parent_context}")
    
    # Add security/access information if relevant
    if security_tag and security_tag.lower() not in ['public', 'open']:
        desc_parts.append(f"Access level: {security_tag}")
    
    # Add identifier if present and meaningful
    if dc_identifier and dc_identifier != title:
        desc_parts.append(f"Identifier: {dc_identifier}")
    
    # If no description exists, create one based on title and path
    if not desc_parts:
        if title:
            # Try to infer content from title
            if any(year in title for year in [str(y) for y in range(2000, 2030)]):
                desc_parts.append(f"Folder containing materials from {title}")
            elif 'AGM' in title:
                desc_parts.append(f"Folder containing Annual General Meeting papers and related documents")
            elif 'Business Confidence Monitor' in title:
                desc_parts.append(f"Folder containing Business Confidence Monitor data and reports")
            elif 'Technical Releases' in path or 'TECH' in title:
                desc_parts.append(f"Folder containing technical releases and guidance documents")
            elif 'Videos' in path or 'Webinars' in path:
                desc_parts.append(f"Folder containing video content and webinar recordings")
            elif 'Thought Leadership' in path:
                desc_parts.append(f"Folder containing thought leadership materials and publications")
            else:
                desc_parts.append(f"Folder: {title}")
        else:
            desc_parts.append("Folder in ICAEW Digital Archive")
    
    return " | ".join(desc_parts) if desc_parts else "Folder in ICAEW Digital Archive"


def process_csv(input_file, output_file=None):
    """
    Process the CSV file and add descriptions for each folder.
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file (optional, defaults to input_file with _with_descriptions suffix)
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)
    
    if output_file is None:
        output_path = input_path.parent / f"{input_path.stem}_with_descriptions{input_path.suffix}"
    else:
        output_path = Path(output_file)
    
    # Read and process the CSV
    rows = []
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        for row in reader:
            # Generate description
            description = generate_description(row)
            row['description'] = description
            rows.append(row)
    
    # Write the output CSV
    if 'description' not in fieldnames:
        fieldnames = list(fieldnames) + ['description']
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Processed {len(rows)} folders")
    print(f"Output written to: {output_path}")
    
    # Also create a text file with line-by-line descriptions
    txt_output = output_path.parent / f"{input_path.stem}_descriptions.txt"
    with open(txt_output, 'w', encoding='utf-8') as f:
        f.write("ICAEW Digital Archive - Folder Descriptions\n")
        f.write("=" * 80 + "\n\n")
        for i, row in enumerate(rows, start=1):
            f.write(f"Line {i}:\n")
            f.write(f"  Title: {row.get('entity.title', 'N/A')}\n")
            f.write(f"  Path: {row.get('preservica_path', 'N/A')}\n")
            f.write(f"  Description: {row.get('description', 'N/A')}\n")
            f.write(f"  Asset ID: {row.get('assetId', 'N/A')}\n")
            f.write("\n")
    
    print(f"Text descriptions written to: {txt_output}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Generate human-readable descriptions for ICAEW Digital Archive folders from a CSV export.",
        epilog="Example: python generate_folder_descriptions.py export.csv --output export_with_descriptions.csv",
    )
    parser.add_argument("input_csv", help="Path to the input CSV file (Preservica export)")
    parser.add_argument("--output", metavar="OUTPUT_CSV", help="Path to output CSV (default: <input>_with_descriptions.csv)")
    args = parser.parse_args()

    process_csv(args.input_csv, args.output)








