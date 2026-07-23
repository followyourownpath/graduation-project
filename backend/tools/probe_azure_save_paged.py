"""Analyze a multi-page PDF under Azure F0 limits, with resume support.

F0 constraints observed:
  - max 2 pages per analyze request
  - ~15 pages/minute rate limit (easy to hit while iterating)

This script renders pages to image PDFs (scan-like), analyzes 2-page chunks,
saves each chunk JSON so a rate-limit failure can resume, then merges.

Usage:
  python tools/probe_azure_save_paged.py path/to/doc.pdf [output.json]
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from app.services.azure_document_intelligence import (
    AzureDocumentIntelligenceClient,
    DocumentIntelligenceError,
)
from app.services.azure_paging import (
    DEFAULT_RETRY_WAIT_SECONDS,
    merge_chunk_results,
    split_pdf_chunks,
)

CHUNK_PAUSE_SECONDS = 45
RETRY_WAIT_SECONDS = DEFAULT_RETRY_WAIT_SECONDS


def analyze_with_retry(client, chunk_bytes, label):
    attempts = 0
    while True:
        attempts += 1
        try:
            return client.analyze(chunk_bytes, "application/pdf")
        except DocumentIntelligenceError as error:
            if error.code != "azure_rate_limited" or attempts >= 4:
                raise
            print(f"      rate limited on {label}; waiting {RETRY_WAIT_SECONDS}s (attempt {attempts})")
            time.sleep(RETRY_WAIT_SECONDS)


def main():
    load_dotenv()
    if len(sys.argv) < 2:
        print("Usage: probe_azure_save_paged.py <document.pdf> [output.json]")
        raise SystemExit(2)

    document = Path(sys.argv[1]).resolve()
    if not document.is_file():
        print(f"FAILED: file not found: {document}")
        raise SystemExit(1)

    out = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else document.with_suffix(".azure.paged.json")
    chunk_dir = out.with_suffix(".chunks")
    chunk_dir.mkdir(parents=True, exist_ok=True)

    client = AzureDocumentIntelligenceClient(
        os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", ""),
        os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", ""),
        os.getenv("AZURE_DOCUMENT_INTELLIGENCE_MODEL", ""),
        os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_VERSION", ""),
    )

    chunks = split_pdf_chunks(document.read_bytes())
    print(f"Document: {document.name}")
    print(f"Chunks: {len(chunks)} | resume dir: {chunk_dir}")

    chunk_results = []
    for index, (start, end, chunk_bytes) in enumerate(chunks, start=1):
        chunk_path = chunk_dir / f"chunk_{start:02d}_{end:02d}.json"
        label = f"pages {start}-{end}"
        if chunk_path.is_file():
            print(f"  [{index}/{len(chunks)}] {label} (cached)")
            result = json.loads(chunk_path.read_text())
        else:
            print(f"  [{index}/{len(chunks)}] {label} ...", flush=True)
            result = analyze_with_retry(client, chunk_bytes, label)
            chunk_path.write_text(json.dumps(result, indent=1, ensure_ascii=False))
            part_pages = len((result.get("analyzeResult") or {}).get("pages") or [])
            print(f"      -> saved {part_pages} page(s) to {chunk_path.name}")
            if index < len(chunks):
                print(f"      pausing {CHUNK_PAUSE_SECONDS}s for rate limit...")
                time.sleep(CHUNK_PAUSE_SECONDS)
        chunk_results.append((start, result))

    merged = merge_chunk_results(chunk_results)
    out.write_text(json.dumps(merged, indent=1, ensure_ascii=False))
    analysis = merged["analyzeResult"]
    marks = sum(len(p.get("selectionMarks") or []) for p in analysis.get("pages") or [])
    print("SUCCESS: merged Azure analysis")
    print(f"Pages: {len(analysis['pages'])}")
    print(f"Tables: {len(analysis['tables'])}")
    print(f"Selection marks: {marks}")
    print(f"Content characters: {len(analysis['content'])}")
    print(f"Saved: {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
