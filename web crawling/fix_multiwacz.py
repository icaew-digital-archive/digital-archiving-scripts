#!/usr/bin/env python3
"""
Fix a Browsertrix "multi-wacz" wrapper into a spec-compliant single WACZ
==========================================================================

Browsertrix Cloud sometimes writes out a .wacz file that is actually a
*collection wrapper* around several complete inner .wacz files (one per
crawl shard), rather than a single spec-compliant WACZ. Its
datapackage.json has "profile": "multi-wacz-package" and the zip has no
top-level archive/, indexes/ or pages/ folders -- it just contains nested
*.wacz members. Tools that expect a normal WACZ (including py-wacz's own
`wacz validate`) reject that structure.

This script rebuilds one valid WACZ from such a file (or from a set of
already-unwrapped shard .wacz files) by:

  1. Recursively unwrapping any multi-wacz wrapper(s) to get the individual
     shard .wacz files.
  2. Extracting each shard and collecting all its WARC files.
  3. Merging each shard's pages/pages.jsonl and pages/extraPages.jsonl into
     a single header + combined entries for each.
  4. Calling `wacz create` (py-wacz, https://github.com/webrecorder/py-wacz)
     on the combined WARCs with the merged page lists, which re-indexes
     everything into one indexes/index.cdx.gz and a proper
     datapackage.json ("profile": "data-package"). No full-text index is
     generated (matches `-d`/--detect-pages behaviour, not `-t`/--text).
  5. Running `wacz validate` on the result and reporting the outcome.

Requires the `wacz` PyPI package, version 0.5.0+ (the CLI gained
`create`/`validate` subcommands and pages-merging flags in that version):
    pip install --upgrade wacz

Usage:
    # Fix a multi-wacz wrapper file
    python fix_multiwacz.py --input broken.wacz --output fixed.wacz

    # Fix a set of already-unwrapped shard .wacz files
    python fix_multiwacz.py --input shard0.wacz shard1.wacz --output fixed.wacz

    # Back up the original and replace it in place with the fixed version
    python fix_multiwacz.py --input broken.wacz --replace-input

    # Pass through collection metadata
    python fix_multiwacz.py --input broken.wacz --output fixed.wacz \\
        --title "Industry Guides" --desc "ICAEW.com industry guides"

Dependencies: wacz>=0.5.0 (py-wacz)
Install: pip install --upgrade wacz
"""

import sys
import json
import shutil
import logging
import zipfile
import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def check_wacz_cli() -> None:
    """Make sure a recent enough `wacz` CLI is importable, or bail with instructions."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "wacz", "--version"],
            capture_output=True, text=True, check=True
        )
        logging.debug(f"wacz CLI version: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.error("The 'wacz' package (py-wacz) is not installed or is too old.")
        logging.error("Install/upgrade it with: pip install --upgrade wacz")
        raise SystemExit(1) from e


def resolve_shards(wacz_path: Path, work_dir: Path) -> List[Path]:
    """
    Recursively resolve a .wacz path into a list of extracted shard
    directories, each containing a normal WACZ layout (archive/, pages/,
    indexes/, ...).

    If `wacz_path` is a multi-wacz wrapper (nested *.wacz members, no
    top-level archive/), its members are extracted and resolved in turn.
    Otherwise `wacz_path` is treated as a shard itself and extracted directly.
    """
    with zipfile.ZipFile(wacz_path) as z:
        names = z.namelist()
        nested_wacz_members = [n for n in names if n.lower().endswith(".wacz")]
        has_archive_dir = any(n.startswith("archive/") for n in names)

        if nested_wacz_members and not has_archive_dir:
            logging.info(
                f"{wacz_path.name} looks like a multi-wacz wrapper "
                f"({len(nested_wacz_members)} nested WACZ file(s)) -- unwrapping"
            )
            shard_dirs = []
            for member in nested_wacz_members:
                nested_path = work_dir / f"nested_{Path(member).name}"
                with z.open(member) as src, open(nested_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                shard_dirs.extend(resolve_shards(nested_path, work_dir))
            return shard_dirs

        logging.info(f"Extracting shard: {wacz_path.name}")
        shard_dir = work_dir / f"shard_{wacz_path.stem}"
        shard_dir.mkdir(parents=True, exist_ok=True)
        z.extractall(shard_dir)
        return [shard_dir]


def gather_warcs(shard_dirs: List[Path], staging_dir: Path) -> List[Path]:
    """Copy every WARC from each shard's archive/ folder into one staging dir."""
    staging_dir.mkdir(parents=True, exist_ok=True)
    warc_files = []
    for shard_dir in shard_dirs:
        archive_dir = shard_dir / "archive"
        if not archive_dir.is_dir():
            continue
        for warc in sorted(archive_dir.glob("*.warc*")):
            dest = staging_dir / warc.name
            if dest.exists():
                logging.warning(f"Duplicate WARC filename across shards, skipping: {warc.name}")
                continue
            shutil.copy2(warc, dest)
            warc_files.append(dest)

    if not warc_files:
        raise FileNotFoundError("No WARC files found in any shard's archive/ folder")

    logging.info(f"Collected {len(warc_files)} WARC file(s) from {len(shard_dirs)} shard(s)")
    return warc_files


def merge_pages_jsonl(shard_dirs: List[Path], rel_path: str) -> Optional[str]:
    """
    Merge a pages-format jsonl file (pages/pages.jsonl or
    pages/extraPages.jsonl) across shards into one header line + all entry
    lines. Returns None if none of the shards have that file.
    """
    header = None
    entries = []
    found_any = False

    for shard_dir in shard_dirs:
        path = shard_dir / rel_path
        if not path.exists():
            continue
        found_any = True
        lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not lines:
            continue
        try:
            parsed_header = json.loads(lines[0])
        except json.JSONDecodeError:
            logging.warning(f"Could not parse header line in {path}, skipping its entries")
            continue
        if header is None:
            header = parsed_header
        entries.extend(lines[1:])

    if not found_any:
        return None

    if header is None:
        header = {"format": "json-pages-1.0", "id": "pages", "title": "Pages"}

    return "\n".join([json.dumps(header)] + entries) + "\n"


def build_wacz(
    warc_files: List[Path],
    output_path: Path,
    work_dir: Path,
    pages_content: Optional[str],
    extra_pages_content: Optional[str],
    hash_type: str,
    title: Optional[str] = None,
    desc: Optional[str] = None,
    url: Optional[str] = None,
) -> None:
    """Invoke `wacz create` to rebuild a single spec-compliant WACZ."""
    cmd = [sys.executable, "-m", "wacz", "create"] + [str(w) for w in warc_files]
    cmd += ["-o", str(output_path), "--hash-type", hash_type]

    # If we have merged page lists, pass them through verbatim (-c = copy as-is,
    # skipping re-validation/re-parsing). Otherwise fall back to having wacz
    # detect pages from the WARCs itself (no full-text index, i.e. no -t/--text).
    used_copy_pages = False
    if pages_content is not None:
        pages_path = work_dir / "merged_pages.jsonl"
        pages_path.write_text(pages_content, encoding="utf-8")
        cmd += ["-p", str(pages_path)]
        used_copy_pages = True

    if extra_pages_content is not None:
        extra_pages_path = work_dir / "merged_extraPages.jsonl"
        extra_pages_path.write_text(extra_pages_content, encoding="utf-8")
        cmd += ["-e", str(extra_pages_path)]
        used_copy_pages = True

    if used_copy_pages:
        cmd += ["-c"]
    else:
        logging.info("No pages.jsonl found in any shard; falling back to --detect-pages")
        cmd += ["-d"]

    if title:
        cmd += ["--title", title]
    if desc:
        cmd += ["--desc", desc]
    if url:
        cmd += ["--url", url]

    logging.info("Running: " + " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    for line in result.stdout.splitlines():
        logging.info(f"  wacz create: {line}")
    if result.returncode != 0:
        for line in result.stderr.splitlines():
            logging.error(f"  wacz create: {line}")
        raise RuntimeError("wacz create failed")


def validate_wacz(wacz_path: Path) -> bool:
    """Run `wacz validate` and return True if it reports success."""
    cmd = [sys.executable, "-m", "wacz", "validate", "-f", str(wacz_path)]
    logging.info("Running: " + " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    for line in result.stdout.splitlines():
        logging.info(f"  wacz validate: {line}")
    for line in result.stderr.splitlines():
        logging.warning(f"  wacz validate: {line}")
    return result.returncode == 0 and "Validation succeeded" in result.stdout


def fix_multiwacz(
    input_paths: List[Path],
    output_path: Path,
    hash_type: str = "sha256",
    title: Optional[str] = None,
    desc: Optional[str] = None,
    url: Optional[str] = None,
    keep_temp: bool = False,
) -> bool:
    """Full pipeline: unwrap -> gather WARCs -> merge pages -> rebuild -> validate."""
    check_wacz_cli()

    tmp_root = tempfile.mkdtemp(prefix="fix_multiwacz_")
    work_dir = Path(tmp_root)
    logging.debug(f"Working directory: {work_dir}")

    try:
        shard_dirs = []
        for input_path in input_paths:
            shard_dirs.extend(resolve_shards(input_path, work_dir))
        logging.info(f"Resolved {len(shard_dirs)} shard(s) total")

        staging_dir = work_dir / "warcs"
        warc_files = gather_warcs(shard_dirs, staging_dir)

        pages_content = merge_pages_jsonl(shard_dirs, "pages/pages.jsonl")
        extra_pages_content = merge_pages_jsonl(shard_dirs, "pages/extraPages.jsonl")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        build_wacz(
            warc_files, output_path, work_dir,
            pages_content, extra_pages_content,
            hash_type, title, desc, url,
        )

        ok = validate_wacz(output_path)
        if ok:
            logging.info(f"Validation succeeded: {output_path}")
        else:
            logging.error(f"Validation FAILED for rebuilt file: {output_path}")
        return ok

    finally:
        if keep_temp:
            logging.info(f"Keeping temp directory for inspection: {work_dir}")
        else:
            shutil.rmtree(work_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(
        description='Rebuild a spec-compliant WACZ from a Browsertrix multi-wacz wrapper (or shard files)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fix a multi-wacz wrapper file
  python fix_multiwacz.py --input broken.wacz --output fixed.wacz

  # Fix a set of already-unwrapped shard .wacz files
  python fix_multiwacz.py --input shard0.wacz shard1.wacz --output fixed.wacz

  # Back up the original and replace it in place with the fixed version
  python fix_multiwacz.py --input broken.wacz --replace-input

  # Pass through collection metadata
  python fix_multiwacz.py --input broken.wacz --output fixed.wacz \\
      --title "Industry Guides" --desc "ICAEW.com industry guides"
        """
    )

    parser.add_argument(
        '--input', '-i',
        nargs='+', required=True,
        help='Input .wacz file(s): a multi-wacz wrapper and/or individual shard .wacz files'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output path for the rebuilt WACZ (required unless --replace-input is used)'
    )
    parser.add_argument(
        '--replace-input', action='store_true',
        help='Back up the single --input file (to <name>.broken-multiwacz.bak) and '
             'overwrite it in place with the rebuilt WACZ. Requires exactly one --input.'
    )
    parser.add_argument('--hash-type', choices=['sha256', 'md5'], default='sha256',
                         help='Hash algorithm for datapackage.json (default: sha256)')
    parser.add_argument('--title', help='Collection title to record in datapackage.json')
    parser.add_argument('--desc', help='Collection description to record in datapackage.json')
    parser.add_argument('--url', help='Main seed URL to record in datapackage.json')
    parser.add_argument('--keep-temp', action='store_true',
                         help='Keep the temporary working directory for inspection')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()
    setup_logging(args.verbose)

    input_paths = [Path(p) for p in args.input]
    for p in input_paths:
        if not p.exists():
            logging.error(f"Input file does not exist: {p}")
            sys.exit(1)

    if args.replace_input:
        if len(input_paths) != 1:
            logging.error("--replace-input requires exactly one --input file")
            sys.exit(1)
        if args.output:
            logging.error("--replace-input and --output are mutually exclusive")
            sys.exit(1)
        original = input_paths[0]
        backup = original.with_suffix(original.suffix + ".broken-multiwacz.bak")
        output_path = original
    else:
        if not args.output:
            logging.error("--output is required unless --replace-input is used")
            sys.exit(1)
        original = None
        backup = None
        output_path = Path(args.output)

    # Build to a temp location first so we never clobber a good file with a bad one.
    build_target = output_path.with_suffix(output_path.suffix + ".rebuilding")

    try:
        ok = fix_multiwacz(
            input_paths, build_target,
            hash_type=args.hash_type,
            title=args.title, desc=args.desc, url=args.url,
            keep_temp=args.keep_temp,
        )
    except KeyboardInterrupt:
        logging.info("\nInterrupted by user")
        build_target.unlink(missing_ok=True)
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error: {e}")
        if args.verbose:
            import traceback
            logging.debug(traceback.format_exc())
        build_target.unlink(missing_ok=True)
        sys.exit(1)

    if not ok:
        build_target.unlink(missing_ok=True)
        logging.error("Rebuilt WACZ failed validation; not replacing/writing output. See log above.")
        sys.exit(1)

    if args.replace_input:
        logging.info(f"Backing up original to: {backup}")
        shutil.move(str(original), str(backup))

    shutil.move(str(build_target), str(output_path))
    logging.info(f"Done! Fixed WACZ written to: {output_path}")


if __name__ == "__main__":
    main()
