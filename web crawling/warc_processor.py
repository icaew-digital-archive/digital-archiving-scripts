#!/usr/bin/env python3
"""
WARC Processor Script
=====================

Combines multiple WARC files into a single WARC and converts to WACZ format.
Designed for digital archivists to consolidate and standardize web archive collections.

Features
--------
- WARC file discovery and combination
- WACZ conversion using official wacz tool
- Page detection and text indexing
- Comprehensive logging and error handling

Usage
-----
Basic: python warc_processor.py --input "/path/to/warcs" --output "output.wacz"
Text index: python warc_processor.py --input "/path/to/warcs" --output "output.wacz" --text-index
Verbose: python warc_processor.py --input "/path/to/warcs" --output "output.wacz" --verbose

Options
-------
--input, -i: Input directory or WARC file (required)
--output, -o: Output WACZ file path (required)
--verbose, -v: Enable verbose logging
--debug: Enable debug logging
--keep-temp: Keep temporary combined WARC file
--no-detect-pages: Disable page detection
--text-index: Generate full-text search index

Dependencies: warcio, wacz
Install: pip install warcio wacz
"""

import os
import sys
import argparse
import subprocess
import glob
from pathlib import Path
from typing import List, Optional
import logging

try:
    from warcio import WARCWriter, ArchiveIterator
    from warcio.statusandheaders import StatusAndHeaders
except ImportError:
    print("Error: warcio library not found.")
    print("Please install it using: pip install warcio")
    sys.exit(1)


class WARCProcessor:
    """Processes WARC files and converts them to WACZ format."""
    
    def __init__(self, input_path: str, output_path: str, log_level: str = "INFO"):
        """
        Initialize the WARC processor.
        
        Args:
            input_path (str): Path to input directory or WARC file
            output_path (str): Path to output WACZ file
            log_level (str): Logging level
        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input path does not exist: {input_path}")
        
        # Check if wacz command is available
        self._check_wacz_command()
    
    def _check_wacz_command(self) -> None:
        """Check if the wacz command-line tool is available."""
        try:
            result = subprocess.run(['wacz', '--help'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise Exception("wacz command failed")
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self.logger.error("wacz command-line tool not found or not working.")
            self.logger.error("Please install it using: pip install wacz")
            self.logger.error(f"Error: {e}")
            sys.exit(1)
    
    def find_warc_files(self) -> List[Path]:
        """Find all WARC files in the input directory."""
        warc_files = []
        
        if self.input_path.is_file():
            # Single WARC file
            if self.input_path.suffix.lower() in ['.warc', '.warc.gz']:
                warc_files.append(self.input_path)
            else:
                raise ValueError(f"Input file is not a WARC file: {self.input_path}")
        else:
            # Directory - find all WARC files
            patterns = ['*.warc', '*.warc.gz']
            for pattern in patterns:
                warc_files.extend(self.input_path.glob(pattern))
                warc_files.extend(self.input_path.glob(f"**/{pattern}"))
        
        # Remove duplicates and sort
        warc_files = sorted(list(set(warc_files)))
        
        if not warc_files:
            raise FileNotFoundError(f"No WARC files found in: {self.input_path}")
        
        self.logger.info(f"Found {len(warc_files)} WARC files")
        for warc_file in warc_files:
            self.logger.debug(f"  - {warc_file}")
        
        return warc_files
    
    def combine_warc_files(self, warc_files: List[Path], temp_warc_path: Path) -> Path:
        """
        Combine multiple WARC files into a single WARC file.
        
        Args:
            warc_files (List[Path]): List of WARC files to combine
            temp_warc_path (Path): Path for the temporary combined WARC file
            
        Returns:
            Path: Path to the combined WARC file
        """
        self.logger.info(f"Combining {len(warc_files)} WARC files into: {temp_warc_path}")
        
        record_count = 0
        
        with open(temp_warc_path, 'wb') as output_file:
            writer = WARCWriter(output_file, gzip=True)
            
            for warc_file in warc_files:
                self.logger.info(f"Processing: {warc_file}")
                
                try:
                    with open(warc_file, 'rb') as input_file:
                        for record in ArchiveIterator(input_file):
                            # Write the record to the combined WARC
                            writer.write_record(record)
                            record_count += 1
                            
                            if record_count % 1000 == 0:
                                self.logger.info(f"Processed {record_count} records...")
                
                except Exception as e:
                    self.logger.error(f"Error processing {warc_file}: {e}")
                    continue
        
        self.logger.info(f"Combined WARC created with {record_count} records: {temp_warc_path}")
        return temp_warc_path
    
    def convert_warc_to_wacz(self, warc_path: Path, detect_pages: bool = True, text_index: bool = False) -> None:
        """
        Convert a WARC file to WACZ format using the wacz command-line tool.
        
        Args:
            warc_path (Path): Path to the WARC file to convert
            detect_pages (bool): Whether to detect pages and generate pages.jsonl
            text_index (bool): Whether to generate full-text search index
        """
        self.logger.info(f"Converting WARC to WACZ: {warc_path} -> {self.output_path}")
        
        try:
            # Build wacz command
            cmd = ['wacz', 'create', '-o', str(self.output_path)]
            
            # Add options based on parameters
            if detect_pages:
                cmd.append('--detect-pages')
            
            if text_index:
                cmd.append('--text')
            
            # Add the WARC file
            cmd.append(str(warc_path))
            
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            
            # Run the wacz command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode != 0:
                self.logger.error(f"wacz command failed with return code {result.returncode}")
                self.logger.error(f"stdout: {result.stdout}")
                self.logger.error(f"stderr: {result.stderr}")
                raise Exception(f"wacz command failed: {result.stderr}")
            
            self.logger.info(f"WACZ file created successfully: {self.output_path}")
            if result.stdout:
                self.logger.debug(f"wacz output: {result.stdout}")
            
        except subprocess.TimeoutExpired:
            self.logger.error("wacz command timed out after 1 hour")
            raise
        except Exception as e:
            self.logger.error(f"Error converting WARC to WACZ: {e}")
            raise
    
    def process(self, cleanup_temp: bool = True, detect_pages: bool = True, text_index: bool = False) -> None:
        """
        Main processing method.
        
        Args:
            cleanup_temp (bool): Whether to clean up temporary files
            detect_pages (bool): Whether to detect pages and generate pages.jsonl
            text_index (bool): Whether to generate full-text search index
        """
        try:
            # Find WARC files
            warc_files = self.find_warc_files()
            
            # If only one WARC file, use it directly
            if len(warc_files) == 1:
                self.logger.info("Single WARC file found, converting directly to WACZ")
                self.convert_warc_to_wacz(warc_files[0], detect_pages, text_index)
            else:
                # Create temporary WARC file path
                temp_warc_path = self.output_path.with_suffix('.warc.gz')
                
                # Combine WARC files
                combined_warc = self.combine_warc_files(warc_files, temp_warc_path)
                
                # Convert to WACZ
                self.convert_warc_to_wacz(combined_warc, detect_pages, text_index)
                
                # Clean up temporary file
                if cleanup_temp and temp_warc_path.exists():
                    temp_warc_path.unlink()
                    self.logger.info(f"Cleaned up temporary file: {temp_warc_path}")
            
            self.logger.info("Processing completed successfully!")
            
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            raise


def main():
    """Main function to handle command line arguments and run the processor."""
    parser = argparse.ArgumentParser(
        description='Combine WARC files and convert to WACZ format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a directory of WARC files
  python warc_processor.py --input "/path/to/warc/files" --output "output.wacz"
  
  # Process a single WARC file
  python warc_processor.py --input "single.warc.gz" --output "output.wacz"
  
  # Verbose logging with text index
  python warc_processor.py --input "/path/to/warc/files" --output "output.wacz" --verbose --text-index
  
  # Without page detection
  python warc_processor.py --input "/path/to/warc/files" --output "output.wacz" --no-detect-pages
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input directory containing WARC files or single WARC file'
    )
    
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output WACZ file path'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--keep-temp',
        action='store_true',
        help='Keep temporary combined WARC file'
    )
    
    parser.add_argument(
        '--no-detect-pages',
        action='store_true',
        help='Disable page detection and pages.jsonl generation'
    )
    
    parser.add_argument(
        '--text-index',
        action='store_true',
        help='Generate full-text search index (requires --detect-pages)'
    )
    
    args = parser.parse_args()
    
    # Determine log level
    if args.debug:
        log_level = "DEBUG"
    elif args.verbose:
        log_level = "INFO"
    else:
        log_level = "WARNING"
    
    try:
        # Create processor and run
        processor = WARCProcessor(
            input_path=args.input,
            output_path=args.output,
            log_level=log_level
        )
        
        processor.process(
            cleanup_temp=not args.keep_temp,
            detect_pages=not args.no_detect_pages,
            text_index=args.text_index
        )
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 