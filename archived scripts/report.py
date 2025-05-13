#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to generate a report on archive growth, file types, and total archive size using Preservica.

Usage: 
    archive_report.py

This script connects to Preservica using credentials from a .env file, and produces:
1. Archive growth over time
2. File type analysis
3. Total archive size

Reports will be generated as CSV files, and visualizations will be displayed.
"""

import os
import csv
from collections import Counter, defaultdict
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import logging
from pyPreservica import EntityAPI

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def load_env_variables():
    """Load environment variables from the .env file."""
    logging.info("Loading environment variables from .env file")
    load_dotenv(override=True)
    
    username = os.getenv('USERNAME')
    password = os.getenv('PASSWORD')
    tenant = os.getenv('TENANT')
    server = os.getenv('SERVER')

    if not username or not password or not tenant or not server:
        logging.error("One or more environment variables are missing. Please check the .env file.")
        exit(1)

    logging.info(f"Environment variables loaded: USERNAME={username}, TENANT={tenant}, SERVER={server}")
    return username, password, tenant, server


def initialize_client(username, password, tenant, server):
    """Initialize the Preservica API client."""
    logging.info("Initializing Preservica API client")
    try:
        client = EntityAPI(username=username, password=password, tenant=tenant, server=server)
        logging.info("Preservica API client initialized successfully")
        return client
    except Exception as e:
        logging.error(f"Failed to initialize Preservica API client: {e}")
        exit(1)


def retrieve_assets(client):
    """Retrieve all assets from the root folder."""
    logging.info("Retrieving assets from the root folder")
    
    try:
        descendants = list(client.all_descendants("672bbddf-324f-47ee-9c98-1064cae71ed4"))  # Convert generator to list
        logging.info(f"Total descendants retrieved: {len(descendants)}")
        
        # Filter to include only assets
        assets = [item for item in descendants if item.entity_type == "ASSET"]  # Check if the entity is an asset
        logging.info(f"Total assets found: {len(assets)}")
        return assets
    except Exception as e:
        logging.error(f"Failed to retrieve assets: {e}")
        exit(1)


def generate_archive_growth_report(assets):
    """Generate archive growth report based on asset creation dates."""
    logging.info("Generating archive growth report")
    growth_counter = Counter()

    for index, asset in enumerate(assets):
        creation_date = asset.creation_date.strftime('%Y-%m')
        growth_counter[creation_date] += 1

        # Log progress every 100 assets processed
        if index % 100 == 0:
            logging.info(f"Processed {index + 1}/{len(assets)} assets for archive growth report")

    # Write to CSV
    with open('archive_growth_report.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Date', 'Assets Added'])
        for date, count in sorted(growth_counter.items()):
            writer.writerow([date, count])

    logging.info("Archive growth report written to 'archive_growth_report.csv'")

    # Plot archive growth
    dates = sorted(growth_counter.keys())
    counts = [growth_counter[date] for date in dates]

    logging.info("Displaying archive growth report graph")
    plt.plot(dates, counts, marker='o')
    plt.title('Archive Growth Over Time')
    plt.xlabel('Date (Year-Month)')
    plt.ylabel('Number of Assets Added')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def generate_file_type_analysis(assets):
    """Generate a report on file types stored in the archive."""
    logging.info("Generating file type analysis")
    file_types = defaultdict(int)

    for index, asset in enumerate(assets):
        file_format = asset.mime_type
        file_types[file_format] += 1

        # Log progress every 100 assets processed
        if index % 100 == 0:
            logging.info(f"Processed {index + 1}/{len(assets)} assets for file type analysis")

    # Write to CSV
    with open('file_type_report.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['File Type', 'Count'])
        for file_type, count in file_types.items():
            writer.writerow([file_type, count])

    logging.info("File type report written to 'file_type_report.csv'")

    # Plot file types
    file_types_sorted = sorted(file_types.items(), key=lambda x: x[1], reverse=True)
    file_type_labels, file_type_counts = zip(*file_types_sorted)

    logging.info("Displaying file type distribution graph")
    plt.figure(figsize=(10, 6))
    plt.barh(file_type_labels, file_type_counts)
    plt.title('File Type Distribution')
    plt.xlabel('Number of Files')
    plt.tight_layout()
    plt.show()


def calculate_total_archive_size(assets):
    """Calculate and report the total size of the archive."""
    logging.info("Calculating total archive size")
    total_size = 0

    for index, asset in enumerate(assets):
        total_size += asset.size

        # Log progress every 100 assets processed
        if index % 100 == 0:
            logging.info(f"Processed {index + 1}/{len(assets)} assets for total size calculation")

    total_size_gb = total_size / (1024 ** 3)
    logging.info(f"Total Archive Size: {total_size_gb:.2f} GB")
    print(f"Total Archive Size: {total_size_gb:.2f} GB")


def main():
    """Main function to execute the report generation."""
    logging.info("Starting archive report generation process")

    username, password, tenant, server = load_env_variables()
    client = initialize_client(username, password, tenant, server)
    
    logging.info("Retrieving assets to generate reports")
    assets = retrieve_assets(client)

    # Generate reports
    logging.info("Starting archive growth report generation")
    generate_archive_growth_report(assets)

    logging.info("Starting file type analysis report generation")
    generate_file_type_analysis(assets)

    logging.info("Starting total archive size calculation")
    calculate_total_archive_size(assets)

    logging.info("All reports generated successfully")


if __name__ == '__main__':
    main()
