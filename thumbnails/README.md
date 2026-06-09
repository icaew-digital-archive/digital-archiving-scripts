# Preservica Folder Thumbnail Refresh

## Background

In Preservica's NGI and Portal interfaces, folders inherit thumbnails from their child assets. This makes folders visually indistinguishable from documents, which creates confusion and undermines navigation — users cannot immediately tell whether an item is a container or a file.

| Problem | Fix |
|:---:|:---:|
| ![Folder inheriting an asset thumbnail](problem.png) | ![Standard folder icon](folder_10x7.png) |
| Folder displays a child asset's thumbnail | Folder displays a clear, recognisable folder icon |

This script is a workaround for that behaviour. It replaces thumbnails on all Preservica folders with a standard folder icon, ensuring folders are always visually distinct. It is designed to run on a cron schedule so that new folders are picked up and updated automatically over time.

The issue has been raised on the Preservica community forum:
https://community.preservica.com/ideas/distinct-folder-thumbnails-in-portal-2841

## How it works

The script walks the Preservica folder hierarchy, and for each folder it hasn't processed before:

1. Removes the existing thumbnail
2. Waits 30 seconds (to allow the API to process the removal)
3. Applies the standard folder icon (`folder_10x7.png`)
4. Records the folder reference in `processed_folders.txt`

On subsequent runs, already-processed folders are skipped. Any new folders added to Preservica since the last run will be picked up and updated automatically.

## Usage

```bash
# Normal run — processes any folders not yet in the tracking file
python thumbnail_refresh.py

# Walk from a specific folder and all its descendants
python thumbnail_refresh.py --folder "38284948-923c-4666-88a7-b60f381e2523"

# Walk the entire repository from root
python thumbnail_refresh.py --folder root

# Dry run — shows what would be processed without making any changes
python thumbnail_refresh.py --dry-run

# Use a custom thumbnail image
python thumbnail_refresh.py --thumbnail /path/to/image.png
```

## Deployment

The script is intended to be hosted on a server and run on a weekly cron schedule. This ensures any new folders added to Preservica during the week are picked up and updated automatically.

To set up the weekly cron job on the server:

```
0 3 * * 6 cd "/path/to/digital-archiving-scripts/thumbnails" && python3 thumbnail_refresh.py >> thumbnail_refresh.log 2>&1
```

This runs every Saturday at 3am. Adjust the path and timing as needed.

The script is safe to run repeatedly — processed folders are tracked and skipped, so only new folders are ever updated.

## Files

| File | Description |
|---|---|
| `thumbnail_refresh.py` | Main script |
| `folder_10x7.png` | Default folder thumbnail applied to all folders |
| `processed_folders.txt` | Tracks which folder references have been processed (auto-created) |

## Configuration

Credentials are loaded from the `.env` file in the repository root:

```
USERNAME=your@email.com
PASSWORD=yourpassword
TENANT=yourtenant
SERVER=eu.preservica.com
```
