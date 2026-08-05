# SmartFinn backend

Flask API for SmartFinn document intake, OCR extraction, normalisation, review,
and approval workflows.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python wsgi.py
```

The development API will be available at `http://localhost:8000`. Copy `.env.example` to a
local `.env`; the application loads it automatically. Runtime environment
variables can also be used. Do not commit real credentials.

## Tests

```powershell
python -m pytest
```

Tests can also run in an isolated Docker image without installing local Python
packages:

```powershell
docker build --target test -t smartfinn-backend-test .
docker run --rm smartfinn-backend-test
```

## Docker

```powershell
docker build --target production -t smartfinn-backend .
docker run --rm -p 5000:5000 --env-file .env smartfinn-backend
```

The versioned health endpoint is `GET /api/v1/health`.

## Backend API contract

The frontend/backend contract is maintained in
[`API_CONTRACT.md`](./API_CONTRACT.md). It records the current endpoints,
authentication requirement, request fields, response shapes, and common errors.

Any pull request that adds, removes, or changes an endpoint must update the
contract in the same pull request.

## Manual staff authentication check

With the backend running locally, use the interactive verification script. It
does not print or persist the entered password or returned access token.

```powershell
python tools/verify_staff_auth.py
```

After authentication succeeds, the intake smoke test creates one clearly named
test application and uploads one small test PDF:

```powershell
python tools/smoke_test_intake.py
```

The full OCR persistence smoke test uses the reviewed synthetic payslip by
default and performs one billable Azure page analysis:

```powershell
python tools/smoke_test_ocr_pipeline.py
```
