# SmartFINN

SmartFINN is a mortgage document processing and risk-assessment platform. It
extracts structured data from application documents, supports staff review and
correction, and runs deterministic cross-document rules to produce traceable
risk results.

## Key features

- Supabase authentication with active-staff access control
- Upload, OCR and structured extraction for Fact Find, ID, payslip, bank
  statement and ATO Notice of Assessment documents
- Human review and correction of extracted fields
- Phase 1 Rules Engine with persistent risk reports
- Optional Connective Mercury CRM integration

## Architecture and technology

```text
Next.js frontend
       |
Flask REST API
       |-- Supabase Auth, PostgreSQL and Storage
       |-- Azure Document Intelligence
       `-- Connective Mercury CRM (optional)
```

- Frontend: Next.js 16 and React 19
- Backend: Python 3.11 and Flask
- Cloud services: Supabase and Azure Document Intelligence
- Deployment: Docker Compose, with Nginx on the production VPS

## Quick start

Prerequisites: Git, Docker Engine and Docker Compose.

```bash
git clone <repository-url>
cd capstone-project-26t2-9900-w19b-bread
cp deploy/production.env.example .env
```

Set the Supabase and Azure test-environment values in `.env`, then start the
application:

```bash
docker compose up --build
```

- Frontend: <http://localhost:3000>
- Backend health: <http://localhost:8000/api/v1/health>

Authentication and database persistence require a configured Supabase project.
Real OCR additionally requires Azure Document Intelligence credentials. Never
commit the populated `.env` file or any secret/service-role key.

Stop the local stack with:

```bash
docker compose down
```

The production VPS uses `docker-compose.prod.yml` and the instructions in
`docs/VPS_DEPLOYMENT.md`; it is separate from this local quick-start setup.

## Testing

Backend:

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest
```

Frontend:

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build
```

## Documentation

- [API contract](docs/API_CONTRACT.md)
- [VPS deployment](docs/VPS_DEPLOYMENT.md)
- [Rules Engine Phase 1 handoff](docs/RULES_ENGINE_PHASE1_IMPLEMENTATION_HANDOFF.md)
- [Supabase schema, migrations and verification](supabase/README.md)
