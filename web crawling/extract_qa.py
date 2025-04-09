import os
import gzip
import json
import tempfile
import pandas as pd
from zipfile import ZipFile
from warcio.archiveiterator import ArchiveIterator
import typer

app = typer.Typer(help="Extract QA comparison data from a WACZ file into a CSV.")

def log(message: str, icon: str = "", no_emoji: bool = False):
    print(f"{'' if no_emoji else icon + ' '}{message}")


@app.command()
def extract(
    input: str = typer.Option(..., "--input", "-i", help="Path to the input WACZ file"),
    output: str = typer.Option(None, "--output", "-o", help="Optional path to output CSV file"),
    no_emoji: bool = typer.Option(False, "--no-emoji", help="Disable emoji output"),
):
    """Extract QA JSON records from info WARC files inside a WACZ archive."""
    if not os.path.exists(input):
        log(f"File not found: {input}", "❌", no_emoji)
        raise typer.Exit(code=1)

    if output is None:
        output = os.path.splitext(input)[0] + ".csv"

    log(f"Unzipping WACZ: {input}", "📦", no_emoji)

    with tempfile.TemporaryDirectory() as temp_dir:
        with ZipFile(input, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        archive_path = os.path.join(temp_dir, "archive")
        if not os.path.isdir(archive_path):
            log("No 'archive/' folder found in WACZ.", "❌", no_emoji)
            raise typer.Exit(code=2)

        log(f"Found archive folder: {archive_path}", "📁", no_emoji)

        data = []
        warc_files = [f for f in os.listdir(archive_path) if f.startswith("info") and f.endswith(".warc.gz")]

        if not warc_files:
            log("No info-*.warc.gz files found.", "⚠️", no_emoji)
            raise typer.Exit(code=3)

        log(f"Processing {len(warc_files)} WARC file(s)...", "🔍", no_emoji)

        for fname in warc_files:
            full_path = os.path.join(archive_path, fname)
            log(f"Processing {fname}", "📖", no_emoji)

            try:
                with gzip.open(full_path, "rb") as stream:
                    for record in ArchiveIterator(stream):
                        if (
                            record.rec_type == "resource" and
                            record.content_type == "application/json"
                        ):
                            uri = record.rec_headers.get_header("WARC-Target-URI")
                            if not uri or not uri.startswith("urn:pageinfo:"):
                                continue

                            try:
                                payload = record.content_stream().read()
                                json_data = json.loads(payload.decode("utf-8"))

                                comparison = json_data.get("comparison", {})
                                rc = comparison.get("resourceCounts", {})

                                data.append({
                                    "url": json_data.get("url"),
                                    "screenshot_match": comparison.get("screenshotMatch"),
                                    "text_match": comparison.get("textMatch"),
                                    "crawl_good": rc.get("crawlGood"),
                                    "crawl_bad": rc.get("crawlBad"),
                                    "replay_good": rc.get("replayGood"),
                                    "replay_bad": rc.get("replayBad"),
                                    "status": json_data.get("status"),
                                    "timestamp": record.rec_headers.get_header("WARC-Date"),
                                    "source_file": fname
                                })

                            except Exception as e:
                                log(f"⚠️ Failed to parse JSON in {fname}: {e}", no_emoji=no_emoji)
            except Exception as e:
                log(f"❌ Could not read {fname}: {e}", no_emoji=no_emoji)

        if not data:
            log("No QA data found in WACZ.", "⚠️", no_emoji)
        else:
            df = pd.DataFrame(data).sort_values("url")
            df.to_csv(output, index=False)
            log(f"Extracted {len(df)} QA records.", "✅", no_emoji)
            log(f"Saved to {output}", "📁", no_emoji)


if __name__ == "__main__":
    app()
