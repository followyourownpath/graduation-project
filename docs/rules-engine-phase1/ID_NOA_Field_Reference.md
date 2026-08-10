# ID and Notice of Assessment Field Reference

> Updated: 30 July 2026
> Scope: `id_100` (NSW Driver Licence) and `ato_notice` (ATO Notice of Assessment)
> Storage: `extracted_field`

Frontend integration details are documented in [ID_NOA_Frontend_Handoff.md](./ID_NOA_Frontend_Handoff.md).

## 1. NSW Driver Licence (`id_100`)

Pipeline: Azure `prebuilt-layout` to `backend/app/normalization/id_100.py`.

The mapper targets NSW driver licence cards. Legacy passport-oriented keys are not supported.

| `field_key` | Label | Type | Normalisation |
|---|---|---|---|
| `document_type` | Document Type | text | Controlled document label |
| `jurisdiction` | Jurisdiction | text | State or issuing jurisdiction |
| `full_legal_name` | Full Legal Name | text | Collapse whitespace |
| `residential_address` | Residential Address | text | Preserve as one address line |
| `licence_number` | Licence Number | identifier | Remove display whitespace |
| `licence_class` | Licence Class | text | Uppercase |
| `date_of_birth` | Date of Birth | date | ISO `YYYY-MM-DD` |
| `card_number` | Card Number | identifier | Remove display whitespace |
| `expiry_date` | Expiry Date | date | ISO `YYYY-MM-DD` |

Example output:

| `field_key` | `normalised_value` |
|---|---|
| `document_type` | `Driver Licence` |
| `jurisdiction` | `New South Wales, Australia` |
| `full_legal_name` | `Junhong ZHONG` |
| `residential_address` | `150 TODMAN AVE, KENSINGTON NSW 2033` |
| `licence_number` | `11208313` |
| `licence_class` | `C` |
| `date_of_birth` | `1992-01-08` |
| `card_number` | `2042604436` |
| `expiry_date` | `2023-12-12` |

Fields that cannot be extracted are omitted.

## 2. ATO Notice of Assessment (`ato_notice`)

Pipeline: Azure `prebuilt-layout` to `backend/app/normalization/ato_notice.py`.

The mapper emits all 24 keys. Optional amount rows are stored with `null` values when no separate amount appears in the notice. This supports a stable review form without interpreting missing amounts as zero.

### Identity and document metadata

| `field_key` | Label | Type | Normalisation |
|---|---|---|---|
| `taxpayer_name` | Taxpayer Name | text | Collapse whitespace |
| `taxpayer_address` | Taxpayer Address | text | Preserve as one address line |
| `tfn` | Tax File Number | identifier | Digits only; sensitive |
| `ato_reference` | ATO Reference | identifier | Remove display whitespace |
| `year_ended` | Year Ended | date | ISO `YYYY-MM-DD` |
| `income_year` | Income Year | text | Derived Australian financial year |
| `date_of_issue` | Date of Issue | date | ISO `YYYY-MM-DD` |

### Tax, credit and liability amounts

| `field_key` | Label | Type |
|---|---|---|
| `taxable_income` | Taxable Income | money |
| `tax_on_taxable_income` | Tax on Taxable Income | money |
| `low_income_tax_offset` | Low Income Tax Offset | money |
| `non_refundable_tax_offsets` | Total Non-refundable Tax Offsets | money |
| `assessed_tax_payable` | Assessed Tax Payable | money |
| `medicare_levy` | Medicare Levy | money |
| `other_liabilities` | Total Other Liabilities | money |
| `tax_offset_refunds` | Tax Offset Refunds | money |
| `payg_withholding_credits` | PAYG Withholding Credits | money |
| `payg_credits_and_entitlements` | Total PAYG and Other Entitlements | money |

Money values remove currency symbols and thousands separators and retain two decimal places. Only an explicit zero is stored as `0.00`.

### Result and refund fields

| `field_key` | Label | Type |
|---|---|---|
| `result_of_notice_amount` | Result of This Notice Amount | money |
| `result_of_notice_direction` | Result of This Notice Direction | enum (`CR` or `DR`) |
| `outcome_amount` | Outcome Amount | money |
| `outcome_direction` | Outcome Direction | enum (`CR` or `DR`) |
| `refund_amount` | Refund Amount | money |
| `refund_status` | Refund Status | text |
| `refund_reference` | Refund Reference | identifier |

`CR` normally indicates a credit or refund; `DR` normally indicates an amount owing. Keep amount and direction as separate review controls.

## 3. Frontend requirements

1. Bind only the keys listed above; do not restore legacy passport fields.
2. Render `null` NOA amount values as empty editable fields, not extraction failures.
3. Keep amount and `CR`/`DR` direction fields separate.
4. Treat TFNs as sensitive data and avoid exposing them in logs.
5. Use the review API display value and submit corrections through the field-review endpoint.

## 4. Verification

Implementation:

```text
backend/app/normalization/id_100.py
backend/app/normalization/ato_notice.py
backend/app/services/ocr_pipeline.py
```

Tests:

```text
backend/tests/test_normalization.py
```
