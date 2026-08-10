# Mercury CRM Writeback — Implementation Handoff

> Audience: developers, testers, and maintainers
> Status: implemented; live writeback requires Mercury credentials and explicit safety configuration
> Related assessment: [Mercury_CRM_Writeback_Integration_Assessment.md](./Mercury_CRM_Writeback_Integration_Assessment.md)

## 1. What shipped

Approval creates an immutable approved-data snapshot and queues a durable CRM synchronization record. A worker then maps the approved Fact Find values to Mercury entities and records progress for retry and audit purposes.

```text
Reviewed Fact Find values
  -> immutable approved snapshot
  -> CRM tracking row and work items
  -> Mercury payload mapping
  -> background worker
  -> Contact and Opportunity writeback
  -> related entities and extensions
  -> status, external IDs, and audit records
```

Supporting documents such as payslips, bank statements, identification, and ATO notices verify the Fact Find. They do not silently replace customer-declared values. A reviewer must approve the final value before it enters the snapshot.

## 2. Key implementation files

| Path | Responsibility |
|---|---|
| `backend/app/integrations/mercury/client.py` | Authenticated HTTP client, masked logging, timeouts, dry-run and write guards |
| `backend/app/integrations/mercury/payloads.py` | Contact, opportunity, address, employment, income, asset and liability payloads |
| `backend/app/integrations/mercury/extension_merge.py` | GET-merge-PUT handling for collection-style extensions |
| `backend/app/integrations/mercury/sync_service.py` | Resumable orchestration and per-item progress |
| `backend/app/services/crm_repository.py` | Tracking, work-item and external-ID persistence |
| `backend/app/workers/mercury_sync.py` | Background queue consumer |
| `backend/app/services/review.py` | Approved snapshot creation, queueing and retry entry point |
| `backend/app/routes/review.py` | Staff-authenticated review and retry endpoints |
| `supabase/migrations/add_mercury_sync_workflow.sql` | Snapshot versioning, work items and atomic approval RPC |

## 3. Required configuration

Keep writes disabled unless running an authorised integration test or production workflow.

```dotenv
MERCURY_ENABLED=false
MERCURY_ALLOW_WRITES=false
MERCURY_DRY_RUN=true
MERCURY_BASE_URL=https://apis.connective.com.au/mercury/v1
MERCURY_API_KEY=
MERCURY_ACCESS_TOKEN=
MERCURY_TEST_RECORD_PREFIX=SMARTFINN-TEST-
```

Safety expectations:

- API keys and tokens must come from environment configuration, never source control.
- Logs must not contain access tokens, full payloads, TFNs, account numbers, dates of birth, or customer addresses.
- Test writes must use the configured record prefix.
- Living Expenses and Other Income require GET-merge-PUT because their update operations replace the collection.
- Retries must resume completed work items rather than create duplicate Mercury records.

## 4. Approval and queue contract

`approve_submission_and_queue_crm_sync` performs the following operations atomically:

1. Locks the submission.
2. allocates the next approved-data version.
3. Inserts the immutable snapshot.
4. Sets the submission to `approved` and CRM status to `pending`.
5. Creates the CRM tracking row.
6. Records an audit event.

Approval state and CRM synchronization state are independent. A synchronization failure must not reverse a completed human approval.

Expected CRM states are:

```text
not_started -> pending -> in_progress -> completed
                                  \-> failed -> pending (manual retry)
                                  \-> failed_permanent
```

## 5. Verification

Automated coverage is primarily located in:

```text
backend/tests/test_mercury_client.py
backend/tests/test_mercury_payloads.py
backend/tests/test_mercury_repository.py
backend/tests/test_mercury_sync_service.py
```

Run the backend suite before merging:

```bash
cd backend
python -m pytest -q
```

For a live test, use only the authorised Mercury test account, enable writes explicitly, retain the test record prefix, and verify the returned external IDs through a read-back request. Return the environment to write-disabled dry-run mode immediately afterward.

## 6. Operational limitations

- Live success depends on valid Connective Mercury credentials and network access.
- The repository test suite mocks external Mercury responses; it does not prove the external service is available.
- The checked-in Swagger file and official Connective documentation remain the API references. Confirm uncertain behaviour against the authorised test tenant before changing payload contracts.
