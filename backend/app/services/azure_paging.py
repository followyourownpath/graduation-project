"""Split multi-page PDFs for Azure Document Intelligence page limits.

Azure F0 (and some other tiers) reject analyze requests with more than two
pages. Fact Find forms are seven pages, so production analysis must chunk,
analyze, then merge into one layout JSON shaped like a single analyzeResult.
"""

from __future__ import annotations

import time
from typing import Any, Callable

import fitz

from app.services.azure_document_intelligence import DocumentIntelligenceError

DEFAULT_PAGES_PER_CHUNK = 2
DEFAULT_RETRY_WAIT_SECONDS = 70


def pdf_page_count(pdf_bytes: bytes) -> int:
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        return len(document)
    finally:
        document.close()


def split_pdf_chunks(
    pdf_bytes: bytes,
    pages_per_chunk: int = DEFAULT_PAGES_PER_CHUNK,
    dpi: int = 150,
) -> list[tuple[int, int, bytes]]:
    """Render page ranges to image-backed PDF chunks (scan-like).

    Returns list of (1-based start page, end page, chunk_pdf_bytes).
    """
    source = fitz.open(stream=pdf_bytes, filetype="pdf")
    chunks = []
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    try:
        for start in range(0, len(source), pages_per_chunk):
            end = min(start + pages_per_chunk, len(source))
            part = fitz.open()
            for index in range(start, end):
                page = source[index]
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                rect = page.rect
                new_page = part.new_page(width=rect.width, height=rect.height)
                new_page.insert_image(rect, stream=pix.tobytes("png"))
            chunks.append((start + 1, end, part.tobytes(deflate=True)))
            part.close()
    finally:
        source.close()
    return chunks


def merge_chunk_results(chunk_results: list[tuple[int, dict]]) -> dict[str, Any]:
    """Merge per-chunk Azure results; page_offset_start is 1-based absolute."""
    merged = {
        "status": "succeeded",
        "analyzeResult": {
            "apiVersion": None,
            "modelId": None,
            "content": "",
            "pages": [],
            "tables": [],
            "paragraphs": [],
            "styles": [],
        },
    }
    analysis = merged["analyzeResult"]
    for page_offset_start, result in chunk_results:
        part = result.get("analyzeResult") or {}
        if not analysis["apiVersion"]:
            analysis["apiVersion"] = part.get("apiVersion")
            analysis["modelId"] = part.get("modelId")
        content = part.get("content") or ""
        if content:
            analysis["content"] = (analysis["content"] + "\n" + content).strip()

        def remap_page(number):
            if number is None:
                return None
            return page_offset_start + (number - 1)

        for page in part.get("pages") or []:
            page = dict(page)
            page["pageNumber"] = remap_page(page.get("pageNumber"))
            analysis["pages"].append(page)

        for table in part.get("tables") or []:
            table = dict(table)
            regions = []
            for region in table.get("boundingRegions") or []:
                region = dict(region)
                region["pageNumber"] = remap_page(region.get("pageNumber"))
                regions.append(region)
            table["boundingRegions"] = regions
            analysis["tables"].append(table)

        for para in part.get("paragraphs") or []:
            para = dict(para)
            regions = []
            for region in para.get("boundingRegions") or []:
                region = dict(region)
                region["pageNumber"] = remap_page(region.get("pageNumber"))
                regions.append(region)
            para["boundingRegions"] = regions
            analysis["paragraphs"].append(para)

        for style in part.get("styles") or []:
            analysis["styles"].append(style)

    analysis["pages"].sort(key=lambda page: page.get("pageNumber") or 0)
    return merged


def _analyze_with_retry(
    analyze: Callable[[bytes, str], dict],
    chunk_bytes: bytes,
    *,
    sleep: Callable[[float], None],
    max_retries: int,
    retry_wait_seconds: float,
) -> dict:
    attempts = 0
    while True:
        attempts += 1
        try:
            return analyze(chunk_bytes, "application/pdf")
        except DocumentIntelligenceError as error:
            if error.code != "azure_rate_limited" or attempts >= max_retries:
                raise
            sleep(retry_wait_seconds)


def analyze_pdf_in_page_chunks(
    client,
    pdf_bytes: bytes,
    *,
    pages_per_chunk: int = DEFAULT_PAGES_PER_CHUNK,
    chunk_pause_seconds: float = 0,
    max_retries: int = 4,
    retry_wait_seconds: float = DEFAULT_RETRY_WAIT_SECONDS,
    sleep: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """Analyze a PDF under a per-request page cap and return a merged result."""
    sleep = sleep or getattr(client, "_sleep", time.sleep)
    chunks = split_pdf_chunks(pdf_bytes, pages_per_chunk=pages_per_chunk)
    if not chunks:
        raise DocumentIntelligenceError(
            "azure_document_rejected",
            "Azure rejected the document or analysis request.",
            422,
        )
    if len(chunks) == 1:
        return client.analyze(chunks[0][2], "application/pdf")

    chunk_results = []
    for index, (start, _end, chunk_bytes) in enumerate(chunks):
        result = _analyze_with_retry(
            client.analyze,
            chunk_bytes,
            sleep=sleep,
            max_retries=max_retries,
            retry_wait_seconds=retry_wait_seconds,
        )
        chunk_results.append((start, result))
        if chunk_pause_seconds and index < len(chunks) - 1:
            sleep(chunk_pause_seconds)
    return merge_chunk_results(chunk_results)
