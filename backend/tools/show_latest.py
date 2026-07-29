import os, requests
from dotenv import load_dotenv
load_dotenv()

url = os.getenv("SUPABASE_URL").rstrip("/")
key = os.getenv("SUPABASE_SECRET_KEY")
h = {"apikey": key, "Authorization": f"Bearer {key}"}

# Get latest job
r = requests.get(
    f"{url}/rest/v1/ocr_extraction_job"
    "?select=id,source_document_id,job_status,created_at&order=created_at.desc&limit=1",
    headers=h, timeout=10
)
job = r.json()[0]
job_id = job["id"]
print(f"Job ID     : {job_id}")
print(f"Status     : {job['job_status']}")
print(f"Created at : {job['created_at']}")

# Get all extracted fields for this job
r2 = requests.get(
    f"{url}/rest/v1/extracted_field"
    f"?ocr_extraction_job_id=eq.{job_id}"
    "&select=field_key,normalised_value,data_type&order=field_key.asc&limit=500",
    headers=h, timeout=10
)
fields = r2.json()
print(f"\nTotal fields extracted: {len(fields)}")
print(f"\n  {'FIELD KEY':<38} {'TYPE':<12} NORMALISED VALUE")
print(f"  {'-'*38} {'-'*12} {'-'*40}")
for f in fields:
    val = str(f.get("normalised_value") or "")[:55]
    print(f"  {f['field_key']:<38} {f['data_type']:<12} {val}")
