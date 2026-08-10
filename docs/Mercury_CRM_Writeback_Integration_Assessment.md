# Mercury CRM Writeback — Integration Assessment

> Assessment date: 2 August 2026
> Outcome: feasible with controlled rollout and explicit operational safeguards

## 1. Decision

SmartFINN can synchronize approved Fact Find data to Connective Mercury through the Mercury REST API. The integration should remain asynchronous because one application may require multiple dependent API calls and partial external success must be recoverable.

The implementation must treat the approved snapshot as the source of truth. OCR output and supporting documents remain verification evidence until a reviewer accepts a value.

## 2. Confirmed API characteristics

- The supplied contract is Swagger 2.0 and uses the Connective API host.
- Authentication uses an access token in the request path and an API key header.
- Resource creation uses `POST`; updates use `PUT`.
- Nested objects with a `uniqueId` represent updates; objects without one represent creates.
- `isDeleted: true` represents a soft-delete request where supported.
- Opportunity updates support partial fields.
- Living Expenses and Other Income updates replace their collections and therefore require GET-merge-PUT.

Repository reference:

```text
docs/MercuryAPISwagger-webhooks (1).yml
```

Official Connective references:

- <https://wiki.connective.com.au/en/articles/640-mercury-connect-api-swagger-2-0-update>
- <https://wiki.connective.com.au/en/articles/663-managing-opportunities-via-the-mercury-api>
- <https://wiki.connective.com.au/en/articles/24580-how-to-create-a-person-record-via-an-api-post-payload>
- <https://wiki.connective.com.au/en/articles/25091-how-to-create-an-opportunity-record-via-an-api-post-payload>
- <https://wiki.connective.com.au/en/articles/641-nexus-financials-living-expenses-endpoint>
- <https://wiki.connective.com.au/en/articles/644-nexus-financials-other-income-endpoint>
- <https://wiki.connective.com.au/en/articles/658-managing-related-parties-via-the-mercury-api>
- <https://wiki.connective.com.au/en/articles/661-managing-assets>
- <https://wiki.connective.com.au/en/articles/659-managing-liabilities>

## 3. Data ownership

| Data source | Writeback role |
|---|---|
| Reviewed Fact Find | Authoritative customer-declared value |
| Payslip | Verification evidence for employment and income |
| Bank statement | Verification evidence for accounts, income and expenses |
| Identification | Verification evidence for identity and address |
| ATO Notice of Assessment | Verification evidence for identity and annual tax data |

Supporting evidence must never silently overwrite the approved Fact Find snapshot.

## 4. Main risks and controls

| Risk | Required control |
|---|---|
| Duplicate records after retry | Persist Mercury IDs and resume at work-item level |
| Partial external success | Durable queue, status tracking and idempotent orchestration |
| Collection data loss | GET-merge-PUT for replacement-style endpoints |
| Credential or PII exposure | Environment secrets, masked URLs and redacted logs |
| Accidental production writes | Disabled-by-default writes, dry-run mode and test prefix |
| Contract ambiguity | Verify against the authorised test tenant and encode behaviour in tests |
| Long approval requests | Queue work after atomic approval rather than synchronizing inline |

## 5. Acceptance criteria

- Approval creates a versioned immutable snapshot and durable pending tracking row.
- One- and two-applicant cases can create or update contacts.
- Opportunity and related-party external IDs are persisted.
- Address, employment, income, assets and liabilities are supported.
- Collection extensions preserve existing Mercury rows.
- Retries do not duplicate completed work.
- UI status distinguishes pending, in-progress, completed and failed synchronization.
- Unit and integration tests cover payloads, safety switches, repository operations and retry behaviour.
- A controlled test-tenant run verifies the live contract before production enablement.
