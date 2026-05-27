#!/usr/bin/env python3
"""
Combine Multiple WARC Files
============================

Simple script to combine multiple WARC files into a single WARC file.
Handles both compressed (.warc.gz) and uncompressed (.warc) files.

Usage:
    python combine_warcs.py --input "/path/to/warc/files" --output "combined.warc.gz"
    python combine_warcs.py --input "file1.warc.gz" "file2.warc.gz" --output "combined.warc.gz"

Dependencies: warcio
Install: pip install warcio
"""

import sys
import argparse
from pathlib import Path
from typing import List
import logging

try:
    from warcio import WARCWriter, ArchiveIterator
except ImportError:
    print("Error: warcio library not found.")
    print("Please install it using: pip install warcio")
    sys.exit(1)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def find_warc_files(input_paths: List[str]) -> List[Path]:
    """
    Find all WARC files from input paths (files or directories).
    
    Args:
        input_paths: List of file paths or directory paths
        
    Returns:
        List of Path objects for WARC files
    """
    warc_files = []
    
    for input_path in input_paths:
        path = Path(input_path)
        
        if not path.exists():
            logging.warning(f"Path does not exist: {path}")
            continue
        
        if path.is_file():
            # Single file
            name_lower = path.name.lower()
            if name_lower.endswith('.warc.gz') or name_lower.endswith('.warc'):
                warc_files.append(path)
            else:
                logging.warning(f"Not a WARC file: {path}")
        else:
            # Directory - find all WARC files
            patterns = ['*.warc', '*.warc.gz']
            for pattern in patterns:
                warc_files.extend(path.glob(pattern))
                warc_files.extend(path.glob(f"**/{pattern}"))
    
    # Remove duplicates and sort
    warc_files = sorted(list(set(warc_files)))
    
    if not warc_files:
        raise FileNotFoundError("No WARC files found in input paths")
    
    logging.info(f"Found {len(warc_files)} WARC files")
    for warc_file in warc_files:
        size_mb = warc_file.stat().st_size / (1024 * 1024)
        logging.info(f"  - {warc_file.name} ({size_mb:.2f} MB)")
    
    return warc_files


def combine_warc_files(warc_files: List[Path], output_path: Path, verbose: bool = False) -> None:
    """
    Combine multiple WARC files into a single WARC file.
    
    Args:
        warc_files: List of WARC files to combine
        output_path: Path for the output combined WARC file
        verbose: Enable verbose logging
    """
    logging.info(f"Combining {len(warc_files)} WARC files into: {output_path}")
    
    # Determine output compression based on file extension
    output_gzip = output_path.name.endswith('.gz')
    
    record_count = 0
    info_record_written = False
    
    try:
        with open(output_path, 'wb') as output_file:
            writer = WARCWriter(output_file, gzip=output_gzip)
            
            for warc_file in warc_files:
                logging.info(f"Processing: {warc_file.name}")
                
                try:
                    with open(warc_file, 'rb') as input_file:
                        for record in ArchiveIterator(input_file):
                            # Skip duplicate info records (only keep the first one)
                            if record.rec_type == 'warcinfo':
                                if info_record_written:
                                    if verbose:
                                        logging.debug(f"Skipping duplicate warcinfo record from {warc_file.name}")
                                    continue
                                info_record_written = True
                            
                            # Write the record to the combined WARC
                            writer.write_record(record)
                            record_count += 1
                            
                            if record_count % 1000 == 0:
                                logging.info(f"Processed {record_count} records...")
                
                except Exception as e:
                    logging.error(f"Error processing {warc_file}: {e}")
                    if verbose:
                        import traceback
                        logging.debug(traceback.format_exc())
                    continue
        
        if record_count == 0:
            raise ValueError("No records were successfully combined from the input WARC files")
        
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logging.info(f"✓ Successfully combined {record_count} records into {output_path.name}")
        logging.info(f"  Output file size: {file_size_mb:.2f} MB")
        
    except Exception as e:
        # Clean up partial output file on error
        if output_path.exists():
            output_path.unlink()
            logging.warning(f"Removed incomplete output file: {output_path}")
        raise


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Combine multiple WARC files into a single WARC file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Combine all WARC files in a directory
  python combine_warcs.py --input "/path/to/warc/files" --output "combined.warc.gz"
  
  # Combine specific WARC files
  python combine_warcs.py --input file1.warc.gz file2.warc.gz --output "combined.warc.gz"
  
  # Verbose output
  python combine_warcs.py --input "/path/to/warc/files" --output "combined.warc.gz" --verbose
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        nargs='+',
        required=True,
        help='Input WARC file(s) or directory(ies) containing WARC files'
    )
    
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output combined WARC file path (.warc or .warc.gz)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    try:
        # Find WARC files
        warc_files = find_warc_files(args.input)
        
        # Validate output path
        output_path = Path(args.output)
        if output_path.exists():
            logging.warning(f"Output file already exists: {output_path}")
            response = input("Overwrite? (y/N): ")
            if response.lower() != 'y':
                logging.info("Cancelled.")
                sys.exit(0)
        
        # Combine WARC files
        combine_warc_files(warc_files, output_path, args.verbose)
        
        logging.info("Done!")
        
    except KeyboardInterrupt:
        logging.info("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error: {e}")
        if args.verbose:
            import traceback
            logging.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()

