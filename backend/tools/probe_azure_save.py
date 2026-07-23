"""Call Azure Document Intelligence and save the full JSON for offline OCR work.

Usage:
  python tools/probe_azure_save.py path/to/doc.pdf [output.json]

Does not require Supabase or staff login — only Azure env vars.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from app.services.azure_document_intelligence import AzureDocumentIntelligenceClient


def main():
    load_dotenv()
    if len(sys.argv) < 2:
        print("Usage: probe_azure_save.py <document.pdf> [output.json]")
        raise SystemExit(2)

    document = Path(sys.argv[1]).resolve()
    if not document.is_file():
        print(f"FAILED: file not found: {document}")
        raise SystemExit(1)

    out = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else document.with_suffix(".azure.json")

    client = AzureDocumentIntelligenceClient(
        os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", ""),
        os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", ""),
        os.getenv("AZURE_DOCUMENT_INTELLIGENCE_MODEL", ""),
        os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_VERSION", ""),
    )

    print(f"Analyzing: {document}")
    print(f"Output:    {out}")
    with document.open("rb") as stream:
        result = client.analyze(stream.read(), "application/pdf")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False))

    analysis = result.get("analyzeResult") or {}
    print("SUCCESS: Azure analysis completed")
    print(f"Pages: {len(analysis.get('pages') or [])}")
    print(f"Tables: {len(analysis.get('tables') or [])}")
    print(f"Selection marks: {sum(len(p.get('selectionMarks') or []) for p in analysis.get('pages') or [])}")
    print(f"Content characters: {len(analysis.get('content') or '')}")
    print(f"Saved: {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
