"""Analyze one explicitly supplied mock document and print a safe summary."""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from app.services.azure_document_intelligence import AzureDocumentIntelligenceClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("document")
    parser.add_argument("--mime-type", default="application/pdf")
    args = parser.parse_args()

    load_dotenv()
    client = AzureDocumentIntelligenceClient(
        os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", ""),
        os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", ""),
        os.getenv("AZURE_DOCUMENT_INTELLIGENCE_MODEL", ""),
        os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_VERSION", ""),
    )

    with open(args.document, "rb") as document:
        result = client.analyze(document.read(), args.mime_type)

    analysis = result.get("analyzeResult") or {}
    content_lines = [line.strip() for line in analysis.get("content", "").splitlines()]
    content_lines = [line for line in content_lines if line]
    print("SUCCESS: Azure analysis completed")
    print(f"Pages: {len(analysis.get('pages') or [])}")
    print(f"Tables: {len(analysis.get('tables') or [])}")
    print(f"Content characters: {len(analysis.get('content') or '')}")
    print("First text lines:")
    for line in content_lines[:8]:
        print(f"- {line[:120]}")


if __name__ == "__main__":
    main()
