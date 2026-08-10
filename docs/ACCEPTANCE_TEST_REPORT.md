# Acceptance Test Report

Execution dates: 10-11 August 2026
Code baseline under assessment: `main` revision `0c72994`
Documentation verification revision: the revision containing this report

## Result definitions

| Result | Meaning |
|---|---|
| Pass | Reproduced with the expected result |
| Automated pass | Covered by a passing deterministic automated check |
| Controlled live check required | Cannot be executed without credentials distributed through the tutor-approved private channel |
| Partial pass | The publicly accessible or locally reproducible portion passed; the protected portion still requires controlled access |

## Acceptance cases

| ID | Scenario | Expected result | Result / evidence |
|---|---|---|---|
| AT-01 | Sign in as an active staff user | Login succeeds and protected dashboard loads | Controlled live check required: the deployed login page is reachable, but an active staff credential must be supplied privately before the protected workflow can be tested |
| AT-02 | Attempt access without a token, with an invalid token, inactive staff or missing profile | Request is rejected with 401 or 403 without leaking sensitive details | Automated pass: authentication route/service tests |
| AT-03 | Create a valid application | Application and Fact Find submission records are created | Automated pass; controlled live UI check requires the AT-01 staff credential |
| AT-04 | Upload one valid synthetic supported document | File and metadata are stored and status becomes uploaded | Automated pass; controlled live Storage check requires the AT-01 staff credential and nominated Supabase project |
| AT-05 | Upload invalid or misleading content | Request is rejected; failed metadata persistence rolls back the object | Automated pass |
| AT-06 | Process supported synthetic documents | OCR/AcroForm values, pages, tables, fields and confidence evidence are persisted | Automated pass; controlled live check requires the nominated Azure test resource |
| AT-07 | Submit a blank fillable Fact Find | Clear validation failure is shown without wasting Azure quota | Automated pass |
| AT-08 | Correct an extracted field and save | Reviewed value and review metadata persist after reload | Automated route pass; controlled live UI check requires the AT-01 staff credential |
| AT-09 | Approve or reject a submission | Valid transition succeeds; invalid transition is rejected | Automated pass; controlled live UI check requires the AT-01 staff credential |
| AT-10 | Assess a complete approved submission | One persistent risk assessment is produced with deterministic score and level | Automated pass using golden/ready data |
| AT-11 | Inspect a risk result | Per-document rule outcomes and compared values are visible; account numbers are masked | Automated display pass; protected report-page visual check requires the AT-01 staff credential |
| AT-12 | Exercise Mercury writeback in dry-run/test mode | Payload and tracking steps are produced without an uncontrolled production write | Automated payload/repository pass; live writes remain disabled unless the tutor approves a dedicated Mercury test tenant |
| AT-13 | Scan repository for secrets | No populated `.env`, private key or high-risk credential is tracked | Secret Scan CI |
| AT-14 | Build and start with Docker | Backend becomes healthy and frontend login page responds | Pass on 11 August 2026: both production images built, backend became healthy, login returned HTTP 200, and containers were removed after testing; see `docs/evidence/AT-14-local-docker.txt` and `docs/evidence/AT-14-local-docker-login.png` |
| AT-15 | Follow installation manual from a clean machine | Tester can configure, start, verify and stop the system | Partial pass: ZIP extraction, Docker build/start, health requests and cleanup were reproduced; final independent execution still belongs to the assessor or a team member who did not prepare the manual |
| AT-16 | Trigger loading, empty and API failure states | Clear progress, guidance and retry controls are shown | Automated frontend component pass |
| AT-17 | Use primary pages at desktop and mobile viewport widths | No clipped controls, horizontal page overflow or inaccessible primary action | Partial pass on 11 August 2026: public login verified at 1440 x 900 and 390 x 844 with no console errors or horizontal overflow; authenticated primary pages require the AT-01 credential; see `docs/evidence/AT-17-login-desktop.png` and `docs/evidence/AT-17-login-mobile.png` |

## Automated verification summary

| Check | Result |
|---|---|
| Backend tests | Pass - 132 tests |
| Backend coverage gate | Pass - 76.52%, minimum 75% |
| Frontend tests | Pass - 10 unit and 7 component/interaction tests |
| Frontend coverage gate | Pass for configured UI scope |
| Frontend lint | Pass |
| Frontend production build | Pass |
| Production Compose resolution | Pass |
| Local Docker image build and container health | Pass - evidence under `docs/evidence/` |
| Public deployed login at desktop/mobile widths | Pass - evidence under `docs/evidence/` |

The four push workflows on revision `0c72994` completed successfully: Backend CI, Frontend CI, Production Image CI and Secret Scan.

## Controlled test access

Secrets are intentionally excluded from Git and the Moodle ZIP. Before submission, the team must place the active assessor account and any agreed Supabase/Azure test values in the private Moodle submission comments or another channel explicitly approved by the tutor. That message should identify:

- the deployed test URL or whether local Docker should be used;
- the temporary staff email and password;
- the credential expiry time;
- whether live Azure OCR is included; and
- whether Mercury is dry-run only.

Once controlled access is available, record the execution time, tester, environment, result and sanitized evidence for AT-01, AT-03, AT-04, AT-06, AT-08, AT-09 and AT-11. If the external service prevents completion, preserve the service status, one bounded retry and the alternative demonstration agreed with the tutor.

No real customer data, credentials or access tokens may appear in screenshots or logs.
