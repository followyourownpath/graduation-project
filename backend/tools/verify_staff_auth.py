"""Manually verify a real Supabase staff login against the local backend.

This script never prints or stores the password or access token.
"""

import getpass
import os
import sys

import requests
from dotenv import load_dotenv


def fail(message: str) -> None:
    print(f"FAILED: {message}")
    raise SystemExit(1)


def main() -> None:
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    backend_url = os.getenv("BACKEND_URL", "http://localhost:5000").rstrip("/")

    if not supabase_url or not publishable_key:
        fail("SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY are required in .env")

    email = input("Staff email: ").strip()
    password = getpass.getpass("Staff password (hidden): ")
    if not email or not password:
        fail("email and password are required")

    try:
        login = requests.post(
            f"{supabase_url}/auth/v1/token",
            params={"grant_type": "password"},
            headers={"apikey": publishable_key, "Content-Type": "application/json"},
            json={"email": email, "password": password},
            timeout=20,
        )
    except requests.RequestException:
        fail("could not connect to Supabase Auth")

    if not login.ok:
        fail(f"Supabase login returned HTTP {login.status_code}")

    access_token = login.json().get("access_token")
    if not access_token:
        fail("Supabase login did not return an access token")

    try:
        me = requests.get(
            f"{backend_url}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )
    except requests.RequestException:
        fail("could not connect to the local SmartFinn backend")

    if not me.ok:
        code = (me.json().get("error") or {}).get("code", "unknown_error")
        fail(f"backend returned HTTP {me.status_code} ({code})")

    result = me.json()
    profile = result["staff_profile"]
    print("SUCCESS: authenticated as an active SmartFinn staff member")
    print(f"Role: {profile['role']}")
    print(f"Active: {profile['is_active']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)
