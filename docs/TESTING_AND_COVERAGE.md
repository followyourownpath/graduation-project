# Testing and Coverage

## Testing strategy

SmartFINN uses multiple test levels so failures are caught at the smallest practical boundary.

| Level | Scope | External dependency policy |
|---|---|---|
| Unit | Normalisation, rules, formatting, mappings and validation | No network access |
| Component | Frontend rendering, empty/error/loading states and user interactions | API modules mocked |
| Integration | Flask routes, service orchestration, Supabase repositories and Azure client behaviour | HTTP success and failure responses stubbed |
| End to end | Login, upload, OCR, review, approval and risk assessment | Uses dedicated Supabase and Azure test resources |
| Manual acceptance | Visual usability, responsive layout and production smoke checks | Recorded against the nominated test environment |

## Automated commands

Backend:

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=75
```

Frontend:

```bash
cd frontend
npm ci
npm run test:coverage
npm run lint
npm run build
```

Production configuration:

```bash
APP_ENV_FILE=deploy/production.env.example \
SUPABASE_URL=https://example.supabase.co \
SUPABASE_PUBLISHABLE_KEY=validation-placeholder \
docker compose -f docker-compose.prod.yml config --quiet
```

## Verified baseline

The following baseline was reproduced on 10 August 2026 from the final quality-improvement branches:

| Check | Result |
|---|---|
| Backend pytest | 132 passed |
| Backend statement coverage | 76.52% |
| Authentication service | 100% |
| Intake service | 100% |
| CRM repository | 98% |
| OCR pipeline | 95% |
| Frontend unit tests | 10 passed |
| Frontend component/interaction tests | 7 passed |
| Configured frontend coverage scope | 87.32% statements, 71.25% branches, 88.88% functions, 87.32% lines |
| Frontend ESLint | Passed |
| Next.js production build | Passed |
| Production Compose configuration | Passed |
| Local Docker image build and container health | Passed on 11 August 2026; see `docs/evidence/AT-14-local-docker.txt` |

CI retains `backend/coverage.xml` as an artifact and fails if backend coverage drops below 75%. Frontend CI fails if the configured UI coverage thresholds are not met.

Sanitized Docker and responsive-login evidence is stored under `docs/evidence/`. Authenticated live checks require the assessor account and cloud credentials delivered through the tutor-approved private channel described in the installation manual; secrets are never stored with evidence.

## Happy and sad cases

The automated suite covers both successful operations and representative failures, including:

- missing, invalid, expired and inactive staff authentication;
- Supabase denial, timeout and unexpected responses;
- valid uploads, invalid content and metadata rollback;
- Azure success, rejection, timeout, rate limiting and malformed responses;
- blank Fact Find forms and OCR fallback behaviour;
- missing, duplicate and incomplete documents for risk assessment;
- unknown and null risk states;
- empty, loading and retryable frontend states; and
- CRM insert, update, retry and persistence failures.

## External-service testing

Automated tests do not depend on live cloud availability. Supabase, Azure and Mercury calls are mocked or stubbed at the service boundary. This keeps PR checks deterministic and explicitly exercises external failure behaviour.

Live smoke scripts under `backend/tools/` are used only with dedicated test credentials. A live Azure failure caused by quota, rate limiting or service availability must be recorded in the acceptance report rather than hidden by repeatedly changing the test.

## Test data and privacy

Only synthetic documents under `mock-data/` may be used for automated or assessor testing. Tests must not contain real customer names, credentials, access tokens, bank account details or identity documents. Account numbers shown in rules results are masked by the frontend.

## Known coverage limitation

The large Supabase review service remains expensive to cover exhaustively because it coordinates numerous REST resources. Its public routes and primary workflows are covered, while repository failure paths are progressively tested with stubs. This limitation is mitigated through route tests, service-boundary tests, synthetic smoke tests and the manual acceptance workflow.
