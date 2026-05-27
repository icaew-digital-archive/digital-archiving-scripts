# file-management

Utilities for managing and cleaning up files — deduplication by checksum, bulk deletion, and empty folder removal.

---

## `checksum_duplicate_finder.py`

Find duplicate files by comparing their checksums against a known reference set (CSV or TXT format).

```bash
python checksum_duplicate_finder.py <checksum_report> <folder> [options]
```

| Argument | Description |
|---|---|
| `checksum_report` | Reference checksum file (CSV or TXT) (positional) |
| `folder` | Directory to scan (positional) |
| `--algo` | Hash algorithm (default: `sha1`; any `hashlib` algorithm) |
| `--output-duplicates` | Output file for duplicate paths (default: `duplicates.txt`) |
| `--exclude` | Folders to exclude from scanning (repeatable) |
| `--log-file` | Log file path (default: `checksum_duplicate_checker.log`) |
| `--verbose` | Enable verbose logging |
| `--workers` | Number of parallel worker processes (default: CPU count) |

---

## `delete_files_from_list.py`

Safely delete files (and any resulting empty directories) listed one-per-line in a text file. Prompts for confirmation unless `--no-confirm` is set.

```bash
python delete_files_from_list.py <file_list.txt> [--dry-run] [--no-confirm]
```

| Argument | Description |
|---|---|
| `file_list` | Text file of paths to delete, one per line (positional) |
| `--dry-run` | Preview deletions without making any changes |
| `--no-confirm` | Skip the confirmation prompt |
| `--log-file` | Log file path (default: `delete_files.log`) |
| `--verbose` | Enable verbose logging |

---

## `empty_folder_finder.py`

Find and optionally delete completely empty folders in a directory tree.

```bash
python empty_folder_finder.py <directory> [--delete] [--dry-run]
```

| Argument | Description |
|---|---|
| `directory` | Root directory to scan (positional) |
| `--delete` | Delete empty folders instead of just listing them |
| `--dry-run` | Show what would be deleted (use with `--delete`) |
| `--exclude` | Exclude folders matching a pattern (repeatable, fnmatch syntax) |
| `--no-confirm` | Skip confirmation prompt when deleting |
| `--verbose` | Show detailed progress |
| `--log` | Log file path |
