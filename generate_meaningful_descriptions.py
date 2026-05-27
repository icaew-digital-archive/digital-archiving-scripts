#!/usr/bin/env python3
"""
Generate meaningful descriptions for ICAEW Digital Archive folders.
Uses contextual knowledge and web search to create informative descriptions.
"""

import csv
import sys
import re
from pathlib import Path
from urllib.parse import quote


# Knowledge base of ICAEW folder types and their descriptions
FOLDER_DESCRIPTIONS = {
    'AGM Papers': 'Contains Annual General Meeting papers, agendas, minutes, resolutions, and related governance documents from ICAEW\'s annual meetings. These materials document the formal proceedings, member voting, and key decisions made at each AGM.',
    
    'Business Confidence Monitor': 'Contains quarterly survey data and reports from ICAEW\'s Business Confidence Monitor, which tracks business sentiment and economic outlook across UK regions and sectors. Includes regional breakdowns, sector analysis, and research reports.',
    
    'Technical Releases': 'Contains technical guidance, practice notes, and professional standards issued by ICAEW. These releases provide authoritative guidance on accounting, auditing, tax, and professional practice matters for chartered accountants.',
    
    'TECH': 'Contains technical releases and guidance documents covering specific accounting, auditing, and professional practice topics. These documents provide detailed technical information and best practice guidance for ICAEW members.',
    
    'Faculty of Finance and Management': 'Contains publications, reports, and guidance materials produced by ICAEW\'s Faculty of Finance and Management, which supports finance professionals working in business and industry.',
    
    'Faculty Serials': 'Contains serial publications produced by ICAEW faculties, including regular magazines, newsletters, and journals covering various aspects of the accountancy profession.',
    
    'Audit and Beyond': 'Contains issues of Audit and Beyond, a publication covering audit practice, assurance services, and developments in the audit profession.',
    
    'Business and Management': 'Contains issues of Business and Management, a publication focusing on business strategy, management practices, and finance in business contexts.',
    
    'By All Accounts': 'Contains issues of By All Accounts, a publication covering accounting and finance topics for business professionals.',
    
    'Chartech': 'Contains issues of Chartech (formerly Chartech News), a publication covering technical and professional developments in chartered accountancy.',
    
    'Thought Leadership': 'Contains thought leadership publications, research reports, and strategic initiatives exploring the future of the accountancy profession and addressing key industry challenges.',
    
    'Audit and Assurance': 'Contains materials related to audit and assurance practice, including guidance, research, and thought leadership on audit quality and professional standards.',
    
    'Videos': 'Contains video content including webinars, training materials, conference recordings, and educational content produced by ICAEW.',
    
    'Webinars': 'Contains recorded webinars covering a wide range of topics including tax updates, technical guidance, professional development, and current issues affecting the accountancy profession.',
    
    'Vital': 'Contains archived issues of Vital, the magazine for ICAEW students, providing information, guidance, and support for those training to become chartered accountants.',
}


def extract_year(title):
    """Extract year from title if present."""
    year_match = re.search(r'\b(19|20)\d{2}\b', title)
    return year_match.group() if year_match else None


def extract_folder_type(title, path):
    """Identify the main folder type from title and path."""
    # Check path first for broader context
    path_lower = path.lower()
    title_lower = title.lower()
    
    # Check for specific folder types
    if 'agm papers' in title_lower or 'agm papers' in path_lower:
        return 'AGM Papers'
    elif 'business confidence monitor' in title_lower or 'business confidence monitor' in path_lower:
        return 'Business Confidence Monitor'
    elif 'technical releases' in path_lower or ('tech' in title_lower and 'technical' in path_lower):
        return 'Technical Releases'
    elif 'tech' in title_lower and 'technical releases' in path_lower:
        return 'TECH'
    elif 'faculty of finance and management' in path_lower:
        return 'Faculty of Finance and Management'
    elif 'faculty serials' in path_lower:
        return 'Faculty Serials'
    elif 'audit and beyond' in title_lower:
        return 'Audit and Beyond'
    elif 'business and management' in title_lower:
        return 'Business and Management'
    elif 'by all accounts' in title_lower:
        return 'By All Accounts'
    elif 'chartech' in title_lower:
        return 'Chartech'
    elif 'thought leadership' in path_lower:
        return 'Thought Leadership'
    elif 'audit and assurance' in path_lower:
        return 'Audit and Assurance'
    elif 'videos' in path_lower or 'webinars' in path_lower:
        if 'webinars' in path_lower:
            return 'Webinars'
        return 'Videos'
    elif 'vital' in title_lower:
        return 'Vital'
    
    return None


def generate_description(row):
    """
    Generate a meaningful description for a folder based on its metadata.
    """
    title = row.get('entity.title', '').strip()
    existing_desc = row.get('entity.description', '').strip()
    path = row.get('preservica_path', '').strip()
    security_tag = row.get('asset.security_tag', '').strip()
    
    # If there's already a good description, use it as base
    if existing_desc and len(existing_desc) > 50:
        base_desc = existing_desc
    else:
        base_desc = None
    
    # Identify folder type
    folder_type = extract_folder_type(title, path)
    year = extract_year(title)
    
    # Build description
    desc_parts = []
    
    if base_desc:
        desc_parts.append(base_desc)
    elif folder_type and folder_type in FOLDER_DESCRIPTIONS:
        # Use the base description for this folder type
        type_desc = FOLDER_DESCRIPTIONS[folder_type]
        
        # Add year-specific context if available
        if year:
            if 'AGM Papers' in folder_type:
                desc_parts.append(f"Contains Annual General Meeting papers, agendas, minutes, resolutions, and related governance documents from ICAEW's {year} annual meeting.")
            elif 'Business Confidence Monitor' in folder_type:
                # Check for regional folders
                regions = ['East Midlands', 'East of England', 'London', 'Scotland', 'Wales', 'North West', 'Northern England', 'South East', 'South West', 'West Midlands', 'Yorkshire and Humberside']
                if any(region in title for region in regions):
                    region = [r for r in regions if r in title]
                    if region:
                        desc_parts.append(f"Contains Business Confidence Monitor survey data and reports for {region[0]}, tracking business sentiment and economic outlook in this region.")
                    else:
                        region = title.split(',')[-1].strip() if ',' in title else title.replace('Business Confidence Monitor', '').strip()
                        desc_parts.append(f"Contains Business Confidence Monitor survey data and reports for {region}, tracking business sentiment and economic outlook in this region.")
                elif 'Sectors' in title or any(sector in title for sector in ['Construction', 'Manufacturing', 'Retail', 'Energy', 'Water', 'Mining', 'Engineering']):
                    sector = title.split(',')[-1].strip() if ',' in title else title.replace('Business Confidence Monitor', '').strip()
                    desc_parts.append(f"Contains Business Confidence Monitor data and analysis for the {sector} sector, tracking business confidence and economic indicators.")
                elif 'Research Reports' in title:
                    desc_parts.append(f"Contains research reports and analysis from the Business Confidence Monitor, providing in-depth insights into UK business sentiment and economic trends.")
                elif 'Data Tables' in title:
                    desc_parts.append(f"Contains Business Confidence Monitor data tables from {year}, providing structured data on business sentiment and economic indicators.")
                else:
                    desc_parts.append(f"Contains Business Confidence Monitor data and reports from {year}, tracking business sentiment and economic outlook across UK regions and sectors.")
            elif 'TECH' in folder_type or 'Technical Releases' in folder_type:
                desc_parts.append(f"Contains technical releases and guidance documents from {year}, providing authoritative guidance on accounting, auditing, tax, and professional practice matters.")
            elif 'Faculty Serials' in folder_type or any(serial in folder_type for serial in ['Audit and Beyond', 'Business and Management', 'By All Accounts', 'Chartech']):
                desc_parts.append(f"Contains issues of {title.split(',')[0]} from {year}, covering developments and topics relevant to the accountancy profession during that year.")
            else:
                desc_parts.append(type_desc)
                if year:
                    desc_parts.append(f"Materials from {year}.")
        else:
            # No year, use generic description
            if 'Business Confidence Monitor' in folder_type:
                regions = ['East Midlands', 'East of England', 'London', 'Scotland', 'Wales', 'North West', 'Northern England', 'South East', 'South West', 'West Midlands', 'Yorkshire and Humberside']
                if any(region in title for region in regions):
                    region = [r for r in regions if r in title]
                    if region:
                        desc_parts.append(f"Contains Business Confidence Monitor survey data and reports for {region[0]}, tracking business sentiment and economic outlook in this region.")
                    else:
                        region = title.split(',')[-1].strip() if ',' in title else title.replace('Business Confidence Monitor', '').strip()
                        desc_parts.append(f"Contains Business Confidence Monitor survey data and reports for {region}, tracking business sentiment and economic outlook in this region.")
                elif 'Regions' in title:
                    desc_parts.append("Contains Business Confidence Monitor survey data organized by UK regions, tracking regional business sentiment and economic outlook.")
                elif 'Sectors' in title or any(sector in title for sector in ['Construction', 'Manufacturing', 'Retail', 'Energy', 'Water', 'Mining', 'Engineering']):
                    sector = title.split(',')[-1].strip() if ',' in title else title.replace('Business Confidence Monitor', '').strip()
                    desc_parts.append(f"Contains Business Confidence Monitor data and analysis for the {sector} sector, tracking business confidence and economic indicators.")
                elif 'Research Reports' in title:
                    desc_parts.append("Contains research reports and analysis from the Business Confidence Monitor, providing in-depth insights into UK business sentiment and economic trends.")
                elif 'Data Tables' in title:
                    desc_parts.append("Contains Business Confidence Monitor data tables, providing structured data on business sentiment and economic indicators.")
                else:
                    desc_parts.append(type_desc)
            elif 'Webinars' in folder_type or 'Videos' in folder_type:
                if 'Restricted access' in path:
                    desc_parts.append(f"Contains restricted-access webinar recordings and video content. {title}")
                else:
                    desc_parts.append(f"Contains webinar recordings and video content. {title}")
            else:
                desc_parts.append(type_desc)
    else:
        # Fallback: create description from title and path
        if year:
            desc_parts.append(f"Contains materials from {title} ({year}).")
        else:
            desc_parts.append(f"Contains materials related to {title}.")
        
        # Add path context if helpful
        if path and '/' in path:
            parent = path.split('/')[-2] if len(path.split('/')) > 1 else None
            if parent and parent.lower() not in title.lower():
                desc_parts.append(f"Part of the {parent} collection.")
    
    # Add access level note if restricted
    if security_tag and security_tag.lower() not in ['public', 'open']:
        desc_parts.append(f"Access level: {security_tag}.")
    
    return " ".join(desc_parts) if desc_parts else f"Folder containing materials related to {title}."


def process_csv(input_file, output_file=None):
    """
    Process the CSV file and add meaningful descriptions for each folder.
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)
    
    if output_file is None:
        output_path = input_path.parent / f"{input_path.stem}_with_meaningful_descriptions{input_path.suffix}"
    else:
        output_path = Path(output_file)
    
    # Read and process the CSV
    rows = []
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        
        for row in reader:
            # Generate description
            description = generate_description(row)
            row['description'] = description
            rows.append(row)
    
    # Write the output CSV
    if 'description' not in fieldnames:
        fieldnames.append('description')
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Processed {len(rows)} folders")
    print(f"Output written to: {output_path}")
    
    # Also create a text file with line-by-line descriptions
    txt_output = output_path.parent / f"{input_path.stem}_meaningful_descriptions.txt"
    with open(txt_output, 'w', encoding='utf-8') as f:
        f.write("ICAEW Digital Archive - Folder Descriptions\n")
        f.write("=" * 80 + "\n\n")
        for i, row in enumerate(rows, start=1):
            f.write(f"Line {i}: {row.get('entity.title', 'N/A')}\n")
            f.write(f"  Description: {row.get('description', 'N/A')}\n")
            f.write(f"  Path: {row.get('preservica_path', 'N/A')}\n")
            f.write(f"  Asset ID: {row.get('assetId', 'N/A')}\n")
            f.write("\n")
    
    print(f"Text descriptions written to: {txt_output}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Generate contextual descriptions for ICAEW Digital Archive folders using a built-in knowledge base.",
        epilog="Example: python generate_meaningful_descriptions.py export.csv --output export_with_descriptions.csv",
    )
    parser.add_argument("input_csv", help="Path to the input CSV file (Preservica export)")
    parser.add_argument("--output", metavar="OUTPUT_CSV", help="Path to output CSV (default: <input>_with_meaningful_descriptions.csv)")
    args = parser.parse_args()

    process_csv(args.input_csv, args.output)

