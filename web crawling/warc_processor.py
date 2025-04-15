#!/usr/bin/env python3
"""
WARC Processor - A tool for processing Web Archive (WARC) files.

This script provides functionality to:
1. Process single or multiple WARC files into WACZ (Web Archive Collection Zipped) format
2. Combine multiple WARC files into a single WARC file
3. Handle pages.jsonl and extraPages.jsonl for enhanced web archive metadata

Features:
- Automatic detection of single vs multiple WARC file processing
- Progress bars for long-running operations
- Secure temporary file handling
- Support for both .warc and .warc.gz formats
- Optional preservation of intermediate combined WARC file
- Validation of input files and formats
- Automatic page detection when no pages file is provided

Behavior Notes:
- By default, uses --detect-pages when no pages file is specified
- --pages and --detect-pages are mutually exclusive
- When using --pages, page detection is disabled

Usage:
    python warc_processor.py --input [WARC_FILES...] --output OUTPUT.wacz [OPTIONS]
    python warc_processor.py --input DIRECTORY --output OUTPUT.wacz [OPTIONS]

For detailed usage instructions, run:
    python warc_processor.py --help

Dependencies:
    - warcio: For reading and writing WARC files
    - wacz: For creating WACZ archives
    - tqdm: For progress bars
"""

from warcio.archiveiterator import ArchiveIterator
from warcio.warcwriter import WARCWriter
from wacz.main import create_wacz
import os
import pathlib
from datetime import datetime
from typing import List, Union, Optional
import argparse
import sys
import time
from tqdm import tqdm
import tempfile
import shutil


def get_warc_files(source: Union[str, List[str]]) -> List[str]:
    """
    Get list of WARC files from either a directory or list of files.
    Files must have .warc or .warc.gz extension.

    Args:
        source: Either a directory path or list of WARC file paths
    Returns:
        List[str]: Sorted list of absolute paths to valid WARC files
    Raises:
        ValueError: If no valid WARC files found or if source type is invalid
    """
    if isinstance(source, str) and os.path.isdir(source):
        # If source is a directory, find all WARC files in it
        warc_files = [
            os.path.join(source, f)
            for f in os.listdir(source)
            if f.endswith(('.warc', '.warc.gz'))
        ]
    elif isinstance(source, (list, tuple)):
        # If source is a list of files, validate each one exists
        warc_files = []
        for f in source:
            if os.path.isfile(f) and f.endswith(('.warc', '.warc.gz')):
                warc_files.append(os.path.abspath(f))
            else:
                print(f"Warning: {f} is not a valid WARC file, skipping")
    else:
        raise ValueError(
            "Source must be either a directory path or list of WARC files")

    if not warc_files:
        raise ValueError("No valid WARC files found")

    return sorted(warc_files)  # Sort for consistent ordering


def validate_jsonl_file(file_path: str) -> bool:
    """
    Validate that a JSONL file exists and has the correct extension.
    Prints warning messages if validation fails.

    Args:
        file_path: Path to the JSONL file to validate
    Returns:
        bool: True if file exists and has .jsonl extension, False otherwise
    """
    if not file_path:
        return False
    if not os.path.isfile(file_path):
        print(f"Warning: {file_path} does not exist")
        return False
    if not file_path.endswith('.jsonl'):
        print(f"Warning: {file_path} is not a JSONL file")
        return False
    return True


def combine_warcs(warc_files: List[str], output_warc: str) -> bool:
    """
    Combine multiple WARC files into a single WARC file.
    Adds a warcinfo record with merge metadata.
    Shows progress bars for both files and records.

    Args:
        warc_files: List of WARC file paths to combine
        output_warc: Path for the combined output WARC file
    Returns:
        bool: True if combination successful, False if any error occurred
    """
    try:
        # Create parent directory if it doesn't exist
        os.makedirs(os.path.dirname(output_warc), exist_ok=True)

        print(f"\nMerging {len(warc_files)} WARC files:")
        for f in warc_files:
            print(f"- {os.path.basename(f)}")

        with open(output_warc, 'wb') as output:
            writer = WARCWriter(output, gzip=True)

            # Add a warcinfo record with merge metadata
            merge_info = {
                'software': 'warcio.warcwriter',
                'datetime': datetime.utcnow().isoformat(),
                'merged-from': [os.path.basename(f) for f in warc_files]
            }
            writer.write_record(writer.create_warcinfo_record(
                filename=output_warc, info=merge_info))

            # Process each WARC file with progress bar
            total_records = 0
            for warc_file in tqdm(warc_files, desc="Processing WARC files", unit="file"):
                try:
                    with open(warc_file, 'rb') as stream:
                        # Count records first to set up progress bar
                        record_count = sum(1 for _ in ArchiveIterator(stream))
                        stream.seek(0)  # Reset file pointer

                        # Process records with progress bar
                        with tqdm(total=record_count, desc=f"Processing {os.path.basename(warc_file)}",
                                  unit="records", leave=False) as pbar:
                            for record in ArchiveIterator(stream):
                                writer.write_record(record)
                                total_records += 1
                                pbar.update(1)
                except Exception as e:
                    print(f"\nError processing {warc_file}: {str(e)}")
                    continue

        print(f"\nSuccessfully created combined WARC: {output_warc}")
        print(f"Total records processed: {total_records}")
        return True
    except Exception as e:
        print(f"\nError combining WARCs: {str(e)}")
        return False


def create_wacz_from_warc(
    input_warc: str,
    output: str,
    pages_file: Optional[str] = None,
    extra_pages_file: Optional[str] = None,
    copy_pages: bool = False
) -> Optional[str]:
    """
    Convert a WARC file to WACZ format.
    Will add .wacz extension to output path if not present.

    By default, uses --detect-pages when no pages file is provided.
    If a pages file is specified, page detection is disabled as these
    options are mutually exclusive.

    Args:
        input_warc: Path to input WARC file
        output: Path for output WACZ file
        pages_file: Optional path to pages.jsonl file. If provided, disables --detect-pages
        extra_pages_file: Optional path to extraPages.jsonl file
        copy_pages: Whether to copy pages files as-is instead of matching to WARC records
    Returns:
        Optional[str]: Path to created WACZ file if successful, None if failed
    """
    try:
        # Ensure the parent directory exists
        os.makedirs(os.path.dirname(output) or '.', exist_ok=True)

        # Add .wacz extension if not present
        wacz_path = output if output.endswith('.wacz') else f"{output}.wacz"

        print("\nCreating WACZ file...")
        start_time = time.time()

        # Build wacz.create() arguments as a list
        args = ['create', input_warc, '-o', wacz_path]

        # Only add --detect-pages if no pages file is provided
        if not pages_file:
            args.append('--detect-pages')

        # Add pages files if provided and valid
        if pages_file and validate_jsonl_file(pages_file):
            args.extend(['-p', pages_file])
            if copy_pages:
                args.append('--copy-pages')

        if extra_pages_file and validate_jsonl_file(extra_pages_file):
            args.extend(['-e', extra_pages_file])
            if copy_pages:
                args.append('--copy-pages')

        # Call wacz.create() with our arguments
        from wacz.main import main as wacz_main
        wacz_main(args)

        elapsed = time.time() - start_time
        print(f"\nSuccessfully created WACZ file: {wacz_path}")
        print(f"Time taken: {elapsed:.1f} seconds")
        return wacz_path
    except Exception as e:
        print(f"\nError creating WACZ: {str(e)}")
        return None


def process_warcs(
    source: Union[str, List[str]],
    output: str,
    keep_combined_warc: bool = False,
    pages_file: Optional[str] = None,
    extra_pages_file: Optional[str] = None,
    copy_pages: bool = False,
    combine_only: bool = False
):
    """
    Process WARC file(s) and create a WACZ archive.
    For a single WARC file, converts directly to WACZ.
    For multiple WARC files, combines them first then converts to WACZ.
    Uses a temporary directory for intermediate files.

    By default, uses --detect-pages when no pages file is provided.
    If pages_file is specified, automatic page detection is disabled.

    Args:
        source: Directory containing WARCs or list of WARC file paths
        output: Output path for WACZ file (or combined WARC if combine_only=True)
        keep_combined_warc: Whether to keep the intermediate combined WARC (only applies when combining multiple files)
        pages_file: Optional path to pages.jsonl file. If provided, disables --detect-pages
        extra_pages_file: Optional path to extraPages.jsonl file
        copy_pages: Whether to copy pages files as-is instead of matching to WARC records
        combine_only: If True, only combines WARCs without creating WACZ
    Raises:
        ValueError: If no valid WARC files found
        Exception: If any error occurs during processing
    """
    try:
        # Create output parent directory if needed
        os.makedirs(os.path.dirname(output) or '.', exist_ok=True)

        # Get list of WARC files
        warc_files = get_warc_files(source)
        if not warc_files:
            raise ValueError("No WARC files found")

        # If only one WARC file and not in combine-only mode, process it directly
        if len(warc_files) == 1 and not combine_only:
            print("\nSingle WARC file provided, converting directly to WACZ...")
            wacz_path = create_wacz_from_warc(
                warc_files[0],
                output,
                pages_file,
                extra_pages_file,
                copy_pages
            )
            return

        # For combine-only mode or multiple files
        print(f"\nCombining {len(warc_files)} WARC files...")

        # If combine-only, use the output path directly for the combined WARC
        if combine_only:
            # Ensure output has .warc.gz extension
            if not output.endswith('.warc.gz'):
                output = output + '.warc.gz'
            combined_warc = output
            combine_warcs(warc_files, combined_warc)
            print(f"\nCombined WARC file created at: {combined_warc}")
            return

        # Regular WACZ creation process with multiple files
        with tempfile.TemporaryDirectory() as temp_dir:
            combined_warc = os.path.join(temp_dir, "combined.warc.gz")

            # Step 1: Combine WARCs
            print("\nStep 1: Combining WARC files...")
            if combine_warcs(warc_files, combined_warc):
                # If user wants to keep the combined WARC, copy it next to the output WACZ
                final_warc = None
                if keep_combined_warc:
                    final_warc = os.path.join(
                        os.path.dirname(output), "combined.warc.gz")
                    shutil.copy2(combined_warc, final_warc)
                    print(f"\nKept combined WARC file at: {final_warc}")
                    # Use the copied WARC for WACZ creation
                    combined_warc = final_warc

                # Step 2: Convert to WACZ
                print("\nStep 2: Converting to WACZ...")
                wacz_path = create_wacz_from_warc(
                    combined_warc,
                    output,
                    pages_file,
                    extra_pages_file,
                    copy_pages
                )

    except Exception as e:
        print(f"\nError processing WARCs: {str(e)}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Process WARC files into a combined WACZ archive',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all WARC files in a directory:
  python warc_processor.py --input /path/to/warcs/ --output output.wacz

  # Process specific WARC files:
  python warc_processor.py --input file1.warc file2.warc.gz --output output.wacz

  # Process a single WARC file:
  python warc_processor.py --input combined.warc.gz --output output.wacz

  # Include pages files:
  python warc_processor.py --input /path/to/warcs/ --output output.wacz --pages pages.jsonl --extra-pages extraPages.jsonl

  # Only combine WARC files without creating WACZ:
  python warc_processor.py --input file1.warc file2.warc --output combined.warc.gz --combine-only
""")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    parser.add_argument('--input', required=True, nargs='+',
                        help='Input WARC file(s) or directory containing WARC files. '
                        'If a directory is provided, all .warc and .warc.gz files in it will be processed. '
                        'For a single WARC file, it will be converted directly without combining.')
    parser.add_argument('--output', required=True,
                        help='Output path for WACZ file (or combined WARC if --combine-only is used)')
    parser.add_argument('--keep-warc', action='store_true',
                        help='Keep the intermediate combined WARC file')
    parser.add_argument('--pages', help='Path to pages.jsonl file')
    parser.add_argument('--extra-pages', help='Path to extraPages.jsonl file')
    parser.add_argument('--copy-pages', action='store_true',
                        help='Copy pages files as-is instead of matching to WARC records')
    parser.add_argument('--combine-only', action='store_true',
                        help='Only combine WARC files without creating WACZ')

    try:
        args = parser.parse_args()
    except argparse.ArgumentError as e:
        parser.print_help()
        print(f"\nError: {str(e)}")
        sys.exit(1)

    # If a single directory is provided, use it as source directory
    # Otherwise treat inputs as a list of files
    if len(args.input) == 1 and os.path.isdir(args.input[0]):
        source = args.input[0]
    else:
        source = args.input

    process_warcs(
        source,
        args.output,
        args.keep_warc,
        args.pages,
        args.extra_pages,
        args.copy_pages,
        args.combine_only
    )


if __name__ == "__main__":
    main()
