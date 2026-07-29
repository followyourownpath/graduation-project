"""
Query the latest extracted fields from Supabase for a given document type
and print them in a readable table.

Usage:
    python tools/show_fields.py <document_type> [limit]

Example:
    python tools/show_fields.py id_100
    python tools/show_fields.py bank_statement_3m 20
"""

import os
import sys
import requests
from dotenv import load_dotenv


def main():
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    secret_key = os.getenv("SUPABASE_SECRET_KEY", "")

    if not supabase_url or not secret_key:
        print("ERROR: SUPABASE_URL or SUPABASE_SECRET_KEY not set in .env")
        raise SystemExit(1)

    doc_type = sys.argv[1] if len(sys.argv) > 1 else "id_100"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 200

    headers = {
        "apikey": secret_key,
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }

    # Find the most recent job for this document_type
    job_resp = requests.get(
        f"{supabase_url}/rest/v1/ocr_extraction_job",
        headers=headers,
        params={
            "select": "id,document_id,status,created_at,document:source_document_id(document_type)",
            "order": "created_at.desc",
            "limit": "20",
        },
        timeout=15,
    )
    if not job_resp.ok:
        print(f"ERROR fetching jobs: {job_resp.status_code} {job_resp.text[:200]}")
        raise SystemExit(1)

    jobs = job_resp.json()
    # Filter for our doc type (the join may not work with all schemas, fallback below)
    target_job = None
    for job in jobs:
        doc = job.get("document") or {}
        if isinstance(doc, dict) and doc.get("document_type") == doc_type:
            target_job = job
            break

    if not target_job:
        # Fallback: just take the most recent job
        print(f"Note: could not filter by document_type={doc_type}, showing most recent job.")
        target_job = jobs[0] if jobs else None

    if not target_job:
        print("No OCR jobs found in database.")
        raise SystemExit(1)

    job_id = target_job["id"]
    print(f"\n{'='*60}")
    print(f"  OCR Extraction Job: {job_id}")
    print(f"  Status            : {target_job.get('status', 'N/A')}")
    print(f"  Created           : {target_job.get('created_at', 'N/A')}")
    print(f"{'='*60}\n")

    # Fetch extracted fields for this job
    fields_resp = requests.get(
        f"{supabase_url}/rest/v1/extracted_field",
        headers=headers,
        params={
            "ocr_extraction_job_id": f"eq.{job_id}",
            "select": "field_key,field_label,raw_value,normalised_value,data_type,review_status",
            "order": "field_key.asc",
            "limit": str(limit),
        },
        timeout=15,
    )
    if not fields_resp.ok:
        print(f"ERROR fetching fields: {fields_resp.status_code} {fields_resp.text[:200]}")
        raise SystemExit(1)

    fields = fields_resp.json()
    if not fields:
        print("No extracted fields found for this job (fields = 0).")
        raise SystemExit(0)

    print(f"  Total fields extracted: {len(fields)}\n")
    print(f"  {'FIELD KEY':<35} {'TYPE':<12} {'NORMALISED VALUE'}")
    print(f"  {'-'*35} {'-'*12} {'-'*35}")
    for f in fields:
        key = f.get("field_key", "")
        dtype = f.get("data_type", "")
        val = f.get("normalised_value") or f.get("raw_value") or ""
        # Truncate long values
        if len(str(val)) > 50:
            val = str(val)[:47] + "..."
        print(f"  {key:<35} {dtype:<12} {val}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
