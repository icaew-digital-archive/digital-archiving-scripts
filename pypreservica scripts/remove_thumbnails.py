#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to add, remove, or download thumbnail images from Preservica assets and folders.

Usage: 
    remove_thumbnails.py add REFERENCE IMAGE_PATH [--file FILE]
    remove_thumbnails.py remove REFERENCE [--file FILE]
    remove_thumbnails.py download REFERENCE [OUTPUT_PATH] [--size SIZE] [--file FILE]

Examples:
    # Single reference
    remove_thumbnails.py add "bb45f999-7c07-4471-9c30-54b057c500ff" "../my-icon.png"
    remove_thumbnails.py remove "bb45f999-7c07-4471-9c30-54b057c500ff"
    remove_thumbnails.py download "bb45f999-7c07-4471-9c30-54b057c500ff"
    remove_thumbnails.py download "bb45f999-7c07-4471-9c30-54b057c500ff" "custom-name.jpg"
    
    # Batch processing from file
    remove_thumbnails.py add --file references.txt "../my-icon.png"
    remove_thumbnails.py add "../my-icon.png" --file references.txt  # Also works
    remove_thumbnails.py remove --file references.txt
    remove_thumbnails.py download --file references.txt --size LARGE
    
Note: When using --file, the file should contain one reference per line.
For download, output files default to {reference}.jpg (e.g., "4e979854-e1f0-4d31-84ce-92fab3b1ad9e.jpg")
"""

import argparse
import os
import sys
from dotenv import load_dotenv
from pyPreservica import EntityAPI, Thumbnail


def load_env_variables():
    """Load environment variables from .env file"""
    load_dotenv(override=True)
    username = os.getenv('USERNAME')
    password = os.getenv('PASSWORD')
    tenant = os.getenv('TENANT')
    server = os.getenv('SERVER')

    if not username or not password or not tenant or not server:
        print("Error: One or more environment variables are missing. Please check the .env file.")
        sys.exit(1)

    return username, password, tenant, server


def read_references_from_file(file_path):
    """Read references from a text file, one per line."""
    if not os.path.isfile(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    references = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line and not line.startswith('#'):  # Skip empty lines and comments
                references.append(line)
    
    if not references:
        print(f"Error: No valid references found in {file_path}")
        sys.exit(1)
    
    return references


def get_entity(client, reference, exit_on_error=True):
    """Get an entity (asset or folder) by reference."""
    try:
        entity = client.asset(reference)
        entity_type = "asset"
    except Exception:
        try:
            entity = client.folder(reference)
            entity_type = "folder"
        except Exception as e:
            if exit_on_error:
                print(f"Error: Could not find asset or folder with reference {reference}")
                print(f"Details: {e}")
                sys.exit(1)
            else:
                raise
    return entity, entity_type


def add_thumbnail(client, reference, image_path, exit_on_error=True):
    """Add a thumbnail to a Preservica asset or folder."""
    # Validate image file exists
    if not os.path.isfile(image_path):
        error_msg = f"Error: Image file not found: {image_path}"
        if exit_on_error:
            print(error_msg)
            sys.exit(1)
        else:
            print(error_msg)
            return False
    
    try:
        entity, entity_type = get_entity(client, reference, exit_on_error)
    except Exception as e:
        if exit_on_error:
            raise
        else:
            print(f"Error: Could not find asset or folder with reference {reference}: {e}")
            return False
    
    try:
        client.add_thumbnail(entity, image_path)
        print(f"Successfully added thumbnail to {entity_type}: {entity.title or reference}")
        return True
    except Exception as e:
        error_msg = f"Error adding thumbnail to {reference}: {e}"
        if exit_on_error:
            print(error_msg)
            sys.exit(1)
        else:
            print(error_msg)
            return False


def remove_thumbnail(client, reference, exit_on_error=True):
    """Remove a thumbnail from a Preservica asset or folder."""
    try:
        entity, entity_type = get_entity(client, reference, exit_on_error)
    except Exception as e:
        if exit_on_error:
            raise
        else:
            print(f"Error: Could not find asset or folder with reference {reference}: {e}")
            return False
    
    try:
        client.remove_thumbnail(entity)
        print(f"Successfully removed thumbnail from {entity_type}: {entity.title or reference}")
        return True
    except Exception as e:
        error_msg = f"Error removing thumbnail from {reference}: {e}"
        if exit_on_error:
            print(error_msg)
            sys.exit(1)
        else:
            print(error_msg)
            return False


def download_thumbnail(client, reference, output_path, size=None, exit_on_error=True):
    """Download a thumbnail from a Preservica asset or folder."""
    try:
        entity, entity_type = get_entity(client, reference, exit_on_error)
    except Exception as e:
        if exit_on_error:
            raise
        else:
            print(f"Error: Could not find asset or folder with reference {reference}: {e}")
            return False
    
    # Map size string to Thumbnail constant
    size_map = {
        'LARGE': Thumbnail.LARGE,    # 400×400 pixels
        'MEDIUM': Thumbnail.MEDIUM,  # 150×150 pixels
        'SMALL': Thumbnail.SMALL     # 64×64 pixels
    }
    
    thumbnail_size = size_map.get(size.upper()) if size else None
    
    try:
        if thumbnail_size:
            filename = client.thumbnail(entity, output_path, thumbnail_size)
        else:
            filename = client.thumbnail(entity, output_path)
        print(f"Successfully downloaded thumbnail from {entity_type}: {entity.title or reference}")
        print(f"Saved to: {filename}")
        return True
    except Exception as e:
        error_msg = f"Error downloading thumbnail from {reference}: {e}"
        if exit_on_error:
            print(error_msg)
            sys.exit(1)
        else:
            print(error_msg)
            return False


def process_batch_add(client, references, image_path):
    """Process multiple references to add thumbnails."""
    print(f"Processing {len(references)} references...")
    success_count = 0
    error_count = 0
    
    for reference in references:
        if add_thumbnail(client, reference, image_path, exit_on_error=False):
            success_count += 1
        else:
            error_count += 1
    
    print(f"\nBatch processing complete: {success_count} succeeded, {error_count} failed")


def process_batch_remove(client, references):
    """Process multiple references to remove thumbnails."""
    print(f"Processing {len(references)} references...")
    success_count = 0
    error_count = 0
    
    for reference in references:
        if remove_thumbnail(client, reference, exit_on_error=False):
            success_count += 1
        else:
            error_count += 1
    
    print(f"\nBatch processing complete: {success_count} succeeded, {error_count} failed")


def process_batch_download(client, references, size=None):
    """Process multiple references to download thumbnails."""
    print(f"Processing {len(references)} references...")
    success_count = 0
    error_count = 0
    
    for reference in references:
        # Generate output filename based on reference
        output_path = f"{reference}.jpg"
        if download_thumbnail(client, reference, output_path, size, exit_on_error=False):
            success_count += 1
        else:
            error_count += 1
    
    print(f"\nBatch processing complete: {success_count} succeeded, {error_count} failed")


def main():
    parser = argparse.ArgumentParser(description='Add, remove, or download thumbnail from a Preservica asset or folder')
    subparsers = parser.add_subparsers(dest='action', help='Action to perform', required=True)
    
    # Add subcommand
    add_parser = subparsers.add_parser('add', help='Add a thumbnail to an asset or folder')
    add_parser.add_argument('reference', nargs='?', help='Preservica asset or folder reference (required if not using --file)')
    add_parser.add_argument('image_path', nargs='?', help='Path to the thumbnail image file')
    add_parser.add_argument('--file', '-f', help='Text file containing references (one per line). When using --file, provide image_path as the first positional argument after the subcommand.')
    
    # Remove subcommand
    remove_parser = subparsers.add_parser('remove', help='Remove a thumbnail from an asset or folder')
    remove_parser.add_argument('reference', nargs='?', help='Preservica asset or folder reference (required if not using --file)')
    remove_parser.add_argument('--file', '-f', help='Text file containing references (one per line)')
    
    # Download subcommand
    download_parser = subparsers.add_parser('download', help='Download a thumbnail from an asset or folder')
    download_parser.add_argument('reference', nargs='?', help='Preservica asset or folder reference (required if not using --file)')
    download_parser.add_argument('output_path', nargs='?', 
                                 help='Output file path for the thumbnail (default: {reference}.jpg, ignored with --file)')
    download_parser.add_argument('--size', choices=['LARGE', 'MEDIUM', 'SMALL'],
                                 help='Thumbnail size: LARGE (400×400), MEDIUM (150×150), SMALL (64×64)')
    download_parser.add_argument('--file', '-f', help='Text file containing references (one per line)')
    
    args = parser.parse_args()

    # Load credentials and initialize client
    username, password, tenant, server = load_env_variables()
    client = EntityAPI(username=username, password=password, tenant=tenant, server=server)

    # Execute the requested action
    if args.action == 'add':
        if args.file:
            references = read_references_from_file(args.file)
            # When using --file, image_path might be in the reference position
            image_path = args.image_path or args.reference
            if not image_path:
                print("Error: image_path is required when using --file")
                print("Usage: remove_thumbnails.py add --file references.txt image.png")
                sys.exit(1)
            process_batch_add(client, references, image_path)
        else:
            if not args.reference or not args.image_path:
                print("Error: reference and image_path are required (or use --file)")
                sys.exit(1)
            add_thumbnail(client, args.reference, args.image_path)
    elif args.action == 'remove':
        if args.file:
            references = read_references_from_file(args.file)
            process_batch_remove(client, references)
        else:
            if not args.reference:
                print("Error: reference is required (or use --file)")
                sys.exit(1)
            remove_thumbnail(client, args.reference)
    elif args.action == 'download':
        if args.file:
            references = read_references_from_file(args.file)
            process_batch_download(client, references, args.size)
        else:
            if not args.reference:
                print("Error: reference is required (or use --file)")
                sys.exit(1)
            # Default to reference.jpg if no output path provided
            output_path = args.output_path or f"{args.reference}.jpg"
            download_thumbnail(client, args.reference, output_path, args.size)


if __name__ == '__main__':
    main()
