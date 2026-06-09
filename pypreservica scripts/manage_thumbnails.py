#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to add, remove, download, or check thumbnail images from Preservica assets and folders.

Usage:
    manage_thumbnails.py add REFERENCE IMAGE_PATH [--file FILE]
    manage_thumbnails.py remove REFERENCE [--file FILE]
    manage_thumbnails.py download REFERENCE [OUTPUT_PATH] [--size SIZE] [--file FILE]
    manage_thumbnails.py check REFERENCE [--file FILE]

Examples:
    # Single reference
    manage_thumbnails.py add "bb45f999-7c07-4471-9c30-54b057c500ff" "../my-icon.png"
    manage_thumbnails.py remove "bb45f999-7c07-4471-9c30-54b057c500ff"
    manage_thumbnails.py download "bb45f999-7c07-4471-9c30-54b057c500ff"
    manage_thumbnails.py download "bb45f999-7c07-4471-9c30-54b057c500ff" "custom-name.jpg"
    manage_thumbnails.py check "bb45f999-7c07-4471-9c30-54b057c500ff"

    # Batch processing from file
    manage_thumbnails.py add --file references.txt "../my-icon.png"
    manage_thumbnails.py add "../my-icon.png" --file references.txt  # Also works
    manage_thumbnails.py remove --file references.txt
    manage_thumbnails.py download --file references.txt --size LARGE
    manage_thumbnails.py check --file references.txt

Note: When using --file, the file should contain one reference per line.
For download, output files default to {reference}.jpg (e.g., "4e979854-e1f0-4d31-84ce-92fab3b1ad9e.jpg")
"""

import argparse
import logging
import os
import sys
from dotenv import load_dotenv
from pyPreservica import EntityAPI, Thumbnail

THUMBNAIL_SIZES = {
    'LARGE': Thumbnail.LARGE,    # 400×400 pixels
    'MEDIUM': Thumbnail.MEDIUM,  # 150×150 pixels
    'SMALL': Thumbnail.SMALL,    # 64×64 pixels
}


def load_env_variables():
    load_dotenv(override=True)
    username = os.getenv('USERNAME')
    password = os.getenv('PASSWORD')
    tenant = os.getenv('TENANT')
    server = os.getenv('SERVER')
    if not all([username, password, tenant, server]):
        print("Error: One or more environment variables are missing. Please check the .env file.")
        sys.exit(1)
    return username, password, tenant, server


def read_references_from_file(file_path):
    if not os.path.isfile(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    references = [
        line.strip() for line in open(file_path, encoding='utf-8')
        if line.strip() and not line.startswith('#')
    ]
    if not references:
        print(f"Error: No valid references found in {file_path}")
        sys.exit(1)
    return references


def get_entity(client, reference):
    pypreservica_logger = logging.getLogger("pyPreservica")
    original_level = pypreservica_logger.level
    try:
        pypreservica_logger.setLevel(logging.CRITICAL)
        return client.asset(reference), "asset"
    except Exception:
        pass
    finally:
        pypreservica_logger.setLevel(original_level)
    return client.folder(reference), "folder"


def add_thumbnail(client, reference, image_path):
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    entity, entity_type = get_entity(client, reference)
    client.add_thumbnail(entity, image_path)
    print(f"Successfully added thumbnail to {entity_type}: {entity.title or reference}")


def remove_thumbnail(client, reference):
    entity, entity_type = get_entity(client, reference)
    client.remove_thumbnail(entity)
    print(f"Successfully removed thumbnail from {entity_type}: {entity.title or reference}")


def download_thumbnail(client, reference, output_path, size=None):
    entity, entity_type = get_entity(client, reference)
    thumbnail_size = THUMBNAIL_SIZES.get(size.upper()) if size else None
    kwargs = {'size': thumbnail_size} if thumbnail_size else {}
    filename = client.thumbnail(entity, output_path, **kwargs)
    print(f"Successfully downloaded thumbnail from {entity_type}: {entity.title or reference}")
    print(f"Saved to: {filename}")


def check_thumbnail(client, reference):
    entity, entity_type = get_entity(client, reference)
    status = "has a thumbnail" if client.has_thumbnail(entity) else "has no thumbnail"
    print(f"{entity_type.capitalize()}: {entity.title or reference} — {status}")


def process_batch(client, references, action_fn):
    print(f"Processing {len(references)} references...")
    success, errors = 0, 0
    for ref in references:
        try:
            action_fn(client, ref)
            success += 1
        except Exception as e:
            print(f"Error processing {ref}: {e}")
            errors += 1
    print(f"\nBatch complete: {success} succeeded, {errors} failed")


def main():
    parser = argparse.ArgumentParser(description='Add, remove, download, or check thumbnails on Preservica assets and folders')
    subparsers = parser.add_subparsers(dest='action', help='Action to perform', required=True)

    add_parser = subparsers.add_parser('add', help='Add a thumbnail to an asset or folder')
    add_parser.add_argument('reference', nargs='?')
    add_parser.add_argument('image_path', nargs='?')
    add_parser.add_argument('--file', '-f')

    remove_parser = subparsers.add_parser('remove', help='Remove a thumbnail from an asset or folder')
    remove_parser.add_argument('reference', nargs='?')
    remove_parser.add_argument('--file', '-f')

    download_parser = subparsers.add_parser('download', help='Download a thumbnail from an asset or folder')
    download_parser.add_argument('reference', nargs='?')
    download_parser.add_argument('output_path', nargs='?', help='Output file path (default: {reference}.jpg)')
    download_parser.add_argument('--size', choices=['LARGE', 'MEDIUM', 'SMALL'],
                                 help='LARGE (400×400), MEDIUM (150×150), SMALL (64×64)')
    download_parser.add_argument('--file', '-f')

    check_parser = subparsers.add_parser('check', help='Check whether an asset or folder has a thumbnail')
    check_parser.add_argument('reference', nargs='?')
    check_parser.add_argument('--file', '-f')

    args = parser.parse_args()
    username, password, tenant, server = load_env_variables()
    client = EntityAPI(username=username, password=password, tenant=tenant, server=server)

    try:
        if args.action == 'add':
            image_path = args.image_path or args.reference
            if args.file:
                if not image_path:
                    print("Error: image_path is required when using --file")
                    sys.exit(1)
                process_batch(client, read_references_from_file(args.file),
                              lambda c, r: add_thumbnail(c, r, image_path))
            else:
                if not args.reference or not args.image_path:
                    print("Error: reference and image_path are required (or use --file)")
                    sys.exit(1)
                add_thumbnail(client, args.reference, args.image_path)

        elif args.action == 'remove':
            if args.file:
                process_batch(client, read_references_from_file(args.file), remove_thumbnail)
            else:
                if not args.reference:
                    print("Error: reference is required (or use --file)")
                    sys.exit(1)
                remove_thumbnail(client, args.reference)

        elif args.action == 'download':
            if args.file:
                process_batch(client, read_references_from_file(args.file),
                              lambda c, r: download_thumbnail(c, r, f"{r}.jpg", args.size))
            else:
                if not args.reference:
                    print("Error: reference is required (or use --file)")
                    sys.exit(1)
                download_thumbnail(client, args.reference,
                                   args.output_path or f"{args.reference}.jpg", args.size)

        elif args.action == 'check':
            if args.file:
                process_batch(client, read_references_from_file(args.file), check_thumbnail)
            else:
                if not args.reference:
                    print("Error: reference is required (or use --file)")
                    sys.exit(1)
                check_thumbnail(client, args.reference)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
