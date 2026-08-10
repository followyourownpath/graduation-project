# Acceptance Test Report

Execution date: 10 August 2026  
Build under assessment: latest approved `main` revision at execution time

## Result definitions

| Result | Meaning |
|---|---|
| Pass | Reproduced with the expected result |
| Automated pass | Covered by a passing deterministic automated check |
| Pending live check | Requires the nominated Supabase, Azure, Mercury or deployed environment |

## Acceptance cases

| ID | Scenario | Expected result | Result / evidence |
|---|---|---|---|
| AT-01 | Sign in as an active staff user | Login succeeds and protected dashboard loads | Pending live check |
| AT-02 | Attempt access without a token, with an invalid token, inactive staff or missing profile | Request is rejected with 401 or 403 without leaking sensitive details | Automated pass: authentication route/service tests |
| AT-03 | Create a valid application | Application and Fact Find submission records are created | Automated pass; live UI confirmation pending |
| AT-04 | Upload one valid synthetic supported document | File and metadata are stored and status becomes uploaded | Automated pass; live Storage confirmation pending |
| AT-05 | Upload invalid or misleading content | Request is rejected; failed metadata persistence rolls back the object | Automated pass |
| AT-06 | Process supported synthetic documents | OCR/AcroForm values, pages, tables, fields and confidence evidence are persisted | Automated pass; live Azure confirmation pending |
| AT-07 | Submit a blank fillable Fact Find | Clear validation failure is shown without wasting Azure quota | Automated pass |
| AT-08 | Correct an extracted field and save | Reviewed value and review metadata persist after reload | Automated route pass; live UI confirmation pending |
| AT-09 | Approve or reject a submission | Valid transition succeeds; invalid transition is rejected | Automated pass; live UI confirmation pending |
| AT-10 | Assess a complete approved submission | One persistent risk assessment is produced with deterministic score and level | Automated pass using golden/ready data |
| AT-11 | Inspect a risk result | Per-document rule outcomes and compared values are visible; account numbers are masked | Automated display pass; visual confirmation pending |
| AT-12 | Exercise Mercury writeback in dry-run/test mode | Payload and tracking steps are produced without an uncontrolled production write | Automated payload/repository pass; live Mercury test pending credentials |
| AT-13 | Scan repository for secrets | No populated `.env`, private key or high-risk credential is tracked | Secret Scan CI |
| AT-14 | Build and start with Docker | Backend becomes healthy and frontend login page responds | Compose validation pass; full container start pending Docker host |
| AT-15 | Follow installation manual from a clean machine | Tester can configure, start, verify and stop the system | Pending independent tester execution |
| AT-16 | Trigger loading, empty and API failure states | Clear progress, guidance and retry controls are shown | Automated frontend component pass |
| AT-17 | Use primary pages at desktop and mobile viewport widths | No clipped controls, horizontal page overflow or inaccessible primary action | Pending final visual pass |

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

## Final live-test record

Before submission, the team should replace each `Pending live check` above with the execution time, tester, environment, result and evidence location. If an external service prevents completion, record its response/status, retry performed and fallback demonstration agreed with the tutor.

Suggested evidence naming:

```text
evidence/AT-01-active-staff-login.png
evidence/AT-06-live-ocr-result.png
evidence/AT-11-risk-trace.png
evidence/AT-14-docker-compose-ps.txt
evidence/AT-17-mobile-applications.png
```

No real customer data, credentials or access tokens may appear in screenshots or logs.
