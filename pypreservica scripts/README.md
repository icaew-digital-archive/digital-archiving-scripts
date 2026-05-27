# pypreservica scripts

Scripts for interacting with the Preservica API — exporting metadata, updating records, downloading assets, and more.

---

## Setup

Create a `.env` file in the directory you run the scripts from:

```
USERNAME=""
PASSWORD=""
TENANT=""
SERVER="eu.preservica.com"
```

---

## Workflow order

The `a–d` scripts reflect a typical metadata update workflow:

```
a_get_metadata.py           → export current metadata to CSV
b_delete_metadata.py        → clear existing metadata
c_add_metadata_from_csv.py  → write new metadata from CSV
d_update_xip_from_csv.py    → update titles / descriptions / security tags
```

---

## `a_get_metadata.py`

Export metadata, checksums, and file format information from Preservica to a CSV file.

```bash
python a_get_metadata.py \
    (--preservica-folder-ref <ID> | --references-file <file.txt>) \
    --metadata-csv output.csv \
    [options]
```

| Argument | Description |
|---|---|
| `--preservica-folder-ref` | Preservica folder reference ID |
| `--references-file` | Text file of folder/asset reference IDs (one per line) |
| `--metadata-csv` | Output CSV filename (required) |
| `--algorithm` | Checksum algorithm: `MD5`, `SHA1`, `SHA256`, or `ALL` (default: `ALL`) |
| `--new-template` | Use extended Dublin Core elements |
| `--exclude-folders` | Folder references to exclude |
| `--entity-type` | Filter by `assets`, `folders`, or `both` (default: `both`) |
| `--all-generations` | Include all asset generations (default: first generation only) |

---

## `b_delete_metadata.py`

Delete ICAEW and OAI_DC metadata from Preservica assets or folders.

```bash
python b_delete_metadata.py \
    (--csv-file <file.csv> | --preservica_folder_ref <ID>)
```

| Argument | Description |
|---|---|
| `--csv-file` | CSV with an `assetId` column listing items to process |
| `--preservica_folder_ref` | Folder ID — processes all descendants |

---

## `c_add_metadata_from_csv.py`

Add metadata to Preservica assets or folders from a CSV. Column names prefixed `dc:` are written as Dublin Core; columns prefixed `icaew:` are written to the ICAEW namespace. Requires an `assetId` column.

```bash
python c_add_metadata_from_csv.py --csv-file <file.csv>
```

---

## `d_update_xip_from_csv.py`

Update Preservica XIP fields (title, description, security tag) from a CSV.

Required columns: `assetId`, `entity.title`, `entity.description`, `asset.security_tag`, `entity.entity_type`.

```bash
python d_update_xip_from_csv.py --csv-file <file.csv>
```

---

## `download_preservica_assets.py`

Download assets from Preservica with fixity verification.

```bash
python download_preservica_assets.py <output_directory> \
    (--folder <ID> | --folders-file <file> | --asset <ID> | --assets-file <file>) \
    [options]
```

| Argument | Description |
|---|---|
| `output_directory` | Directory to save downloads (positional, required) |
| `--folder` | Single folder ID |
| `--folders-file` | Text file of folder IDs |
| `--asset` | Single asset ID |
| `--assets-file` | Text file of asset IDs |
| `--original-only` | Download first generation (Preservation copy) only |
| `--use-asset-ref` | Use asset reference numbers in filenames |
| `--exclude-extensions` | File extensions to skip (repeatable) |

---

## `move_preservica_assets.py`

Move assets or folders to a target Preservica folder.

```bash
python move_preservica_assets.py \
    (--asset <ID> | --assets-file <file> | --folder <ID> | --folders-file <file>) \
    --destination <folder_ID> [--force]
```

| Argument | Description |
|---|---|
| `--asset` / `--assets-file` | Single asset ID or file of IDs |
| `--folder` / `--folders-file` | Single folder ID or file of IDs |
| `--destination` | Target folder reference ID (required) |
| `--force` | Skip confirmation prompt |

---

## `build_preservica_tree.py`

Build a folder-tree text file from a Preservica CSV export.

```bash
python build_preservica_tree.py <export.csv> [options]
```

| Argument | Description |
|---|---|
| `input_csv` | Full Preservica export CSV (positional) |
| `-o` / `--output` | Output file (default: `<input>-folders-tree.txt`) |
| `-d` / `--depth` | Maximum tree depth |
| `--show-ids` | Append asset IDs after folder names |
| `--include-assets` | Include assets in the tree (default: folders only) |

---

## `remove_thumbnails.py`

Add, remove, or download thumbnail images for Preservica assets or folders.

```bash
python remove_thumbnails.py add     <REFERENCE> <IMAGE_PATH> [--file <refs.txt>]
python remove_thumbnails.py remove  <REFERENCE>              [--file <refs.txt>]
python remove_thumbnails.py download <REFERENCE> [OUTPUT_PATH] [--size <SIZE>] [--file <refs.txt>]
```

---

## `pypreservica-video-package-ingest/video_subtitle_package_ingest.py`

Upload video files and matching `.srt` subtitle files to Preservica as paired assets. Expects a 1:1 filename match between video and subtitle files.

```bash
python pypreservica-video-package-ingest/video_subtitle_package_ingest.py \
    --video_folder <dir> \
    --preservica_folder_id <ID>
```

Supported video formats: `mp4`, `mkv`, `avi`, `mov`, `flv`.
