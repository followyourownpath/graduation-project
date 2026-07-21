import os
from dotenv import load_dotenv
import requests

load_dotenv("backend/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SECRET_KEY")

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Accept": "application/json",
}

res = requests.get(f"{url}/rest/v1/fact_find_submission?select=*", headers=headers)
print("Submissions:", res.json())

res2 = requests.get(f"{url}/rest/v1/source_document?select=*", headers=headers)
print("Documents:", res2.json())
