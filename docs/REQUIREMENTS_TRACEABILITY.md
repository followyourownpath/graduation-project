# Requirements Traceability Matrix

This matrix links the agreed final objectives to implementation, verification and demonstration evidence.

| ID | Requirement | Implementation | Automated verification | Acceptance evidence |
|---|---|---|---|---|
| AUTH-01 | Only authenticated active staff can access protected workflows | `backend/app/auth.py`, `backend/app/services/auth.py`, Supabase staff RLS | `backend/tests/test_auth.py`, authentication service tests | AT-01, AT-02 |
| INT-01 | Staff can create a mortgage application | Intake page, intake route and Supabase intake RPC | `backend/tests/test_intake.py`, intake service tests | AT-03 |
| DOC-01 | Staff can upload required document types securely | Intake service, Storage bucket and upload validation | Intake route/service tests | AT-04, AT-05 |
| OCR-01 | The system extracts structured values from supported documents | Azure client, OCR pipeline and document normalisers | Azure, OCR, Fact Find and normalisation tests | AT-06, AT-07 |
| OCR-02 | The system exposes confidence and source evidence for review | Confidence mapper, page/table/field persistence and review UI | Confidence and OCR persistence tests | AT-06 |
| REV-01 | Staff can inspect and correct extracted fields | Review route/service and application review page | `backend/tests/test_review.py` | AT-08 |
| REV-02 | Staff can approve or reject a reviewed submission | Review status API and frontend controls | Review route tests | AT-09 |
| RISK-01 | Approved submissions can be assessed using deterministic cross-document rules | Rules Engine Phase 1 modules and persistent assessment service | Rules, readiness, route and service tests | AT-10 |
| RISK-02 | Risk results show traceable document and field comparisons | Rules result API and Rules Engine detail pages | Rules Engine tests and frontend display tests | AT-11 |
| CRM-01 | Approved data can be written to Mercury with safe retry controls | Mercury client, payloads, sync service, tracking repository and worker | Mercury payload and repository tests | AT-12 |
| SEC-01 | Secrets remain outside source control and browser code | Environment templates, `.gitignore`, secret-scan workflow | Secret Scan CI | AT-13 |
| SEC-02 | Staff data access is enforced by RLS | Supabase RLS migrations and verification queries | SQL verification scripts and authentication tests | AT-02 |
| OPS-01 | The system can be built and run with Docker | Multi-stage Dockerfiles and local/production Compose files | Production Image CI and Compose validation | AT-14 |
| OPS-02 | A tester can reproduce installation and verification | Installation manual and README | Documentation link checks and listed commands | AT-15 |
| UX-01 | Primary workflows provide clear loading, empty, error and success feedback | Async-state components, toast messages and page states | Frontend component tests | AT-16 |
| UX-02 | Primary workflows remain usable on desktop and narrow screens | Responsive tables/cards, navigation and layouts | Frontend build plus manual viewport checks | AT-17 |

## Change control

Client decisions from weekly meetings and demonstrations take precedence over superseded early drafts. Accepted MVP exclusions are recorded in `docs/Feature_Status_Report.md`. Any final scope change should update this matrix, the feature status report and the relevant acceptance test in the same pull request.
