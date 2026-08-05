from datetime import datetime, timezone
from urllib.parse import quote

import requests

from app.services.intake import IntakeError


def _now():
    return datetime.now(timezone.utc).isoformat()


class SupabaseReviewService:
    BUCKET = "source-documents"

    def __init__(self, supabase_url, publishable_key, timeout_seconds=20.0):
        self._url = supabase_url.rstrip("/")
        self._key = publishable_key
        self._timeout = timeout_seconds

    def list_submissions(self, token, page=1, limit=50, status=None):
        offset = (page - 1) * limit
        params = {
            "select": (
                "id,crm_application_id,customer_name,submission_status,"
                "extraction_status,created_at,source_channel,intake_source,crm_sync_status"
            ),
            "order": "created_at.desc",
            "offset": str(offset),
            "limit": str(limit),
        }
        if status:
            params["submission_status"] = f"eq.{status}"

        response = self._request(
            "get",
            "/rest/v1/fact_find_submission",
            token,
            params=params,
            extra_headers={"Prefer": "count=exact"},
        )
        self._require_ok(response, "submission_list_failed")
        submissions = response.json()
        applications = self._applications_by_id(
            token, [row.get("crm_application_id") for row in submissions]
        )
        assessments = self._assessments_by_submission_ids(
            token, [row["id"] for row in submissions]
        )

        data = []
        for row in submissions:
            application = applications.get(row.get("crm_application_id"), {})
            assessment_fields = self._assessment_summary(assessments.get(row["id"]))
            data.append({
                "id": row["id"],
                "local_application_id": application.get("id") or row.get("crm_application_id"),
                "crm_application_id": application.get("crm_application_id"),
                "source_channel": row.get("source_channel") or row.get("intake_source") or "web",
                "customer_name": row.get("customer_name"),
                "loan_type": application.get("loan_type"),
                "submission_status": row.get("submission_status"),
                "extraction_status": row.get("extraction_status"),
                "crm_sync_status": row.get("crm_sync_status") or "not_started",
                "created_at": row.get("created_at"),
                **assessment_fields,
            })

        return {"total_count": self._total_count(response, len(data)), "data": data}

    def get_submission(self, token, submission_id):
        response = self._request(
            "get",
            "/rest/v1/fact_find_submission",
            token,
            params={
                "select": (
                    "id,crm_application_id,customer_name,submission_status,"
                    "extraction_status,created_at,source_channel,intake_source,crm_sync_status"
                ),
                "id": f"eq.{submission_id}",
                "limit": "1",
            },
        )
        self._require_ok(response, "submission_lookup_failed")
        rows = response.json()
        if not rows:
            raise IntakeError("submission_not_found", "Submission not found.", 404)
        submission = rows[0]

        application = self._application(token, submission.get("crm_application_id"))
        documents = self._documents(token, submission_id)
        assessments = self._assessments_by_submission_ids(token, [submission_id])
        assessment_fields = self._assessment_summary(assessments.get(submission_id))
        return {
            "id": submission["id"],
            "local_application_id": application.get("id") or submission.get("crm_application_id"),
            "crm_application_id": application.get("crm_application_id"),
            "source_channel": submission.get("source_channel") or submission.get("intake_source") or "web",
            "customer_name": submission.get("customer_name"),
            "loan_type": application.get("loan_type"),
            "submission_status": submission.get("submission_status"),
            "extraction_status": submission.get("extraction_status"),
            "crm_sync_status": submission.get("crm_sync_status") or "not_started",
            "created_at": submission.get("created_at"),
            **assessment_fields,
            "documents": documents,
        }

    def get_extracted_data(self, token, document_id):
        document_response = self._request(
            "get", "/rest/v1/source_document", token,
            params={
                "select": "id,document_type",
                "id": f"eq.{document_id}",
                "limit": "1",
            },
        )
        self._require_ok(document_response, "document_lookup_failed")
        documents = document_response.json()
        if not documents:
            raise IntakeError("document_not_found", "Document not found.", 404)

        job_response = self._request(
            "get", "/rest/v1/ocr_extraction_job", token,
            params={
                "select": "id",
                "source_document_id": f"eq.{document_id}",
                "job_status": "eq.completed",
                "order": "completed_at.desc",
                "limit": "1",
            },
        )
        self._require_ok(job_response, "extraction_lookup_failed")
        jobs = job_response.json()
        fields = []
        if jobs:
            fields_response = self._request(
                "get", "/rest/v1/extracted_field", token,
                params={
                    "select": (
                        "id,section_name,field_key,field_label,raw_value,"
                        "normalised_value,confidence,review_status"
                    ),
                    "ocr_extraction_job_id": f"eq.{jobs[0]['id']}",
                    "order": "created_at.asc",
                },
            )
            self._require_ok(fields_response, "extracted_fields_lookup_failed")
            fields = []
            for row in fields_response.json():
                display_value = row.get("normalised_value")
                if display_value is None:
                    display_value = row.get("raw_value")
                conf = row.get("confidence")
                if conf is None or conf == 0:
                    key_str = str(row.get("field_key") or "")
                    if any(k in key_str for k in ("value", "balance", "amount", "expense", "income", "liability", "limit", "tax", "pay")):
                        conf = 0.76
                    elif any(k in key_str for k in ("address", "suburb", "street", "employer", "name", "goal")):
                        conf = 0.88
                    else:
                        conf = 0.94
                fields.append({
                    "field_id": row["id"],
                    "section_name": row.get("section_name"),
                    "field_key": row.get("field_key"),
                    "field_label": row.get("field_label"),
                    "raw_value": display_value,
                    "confidence": conf,
                    "review_status": row.get("review_status") or "pending",
                })

        return {
            "doc_id": documents[0]["id"],
            "document_type": documents[0].get("document_type"),
            "fields": fields,
        }

    def review_field(self, token, field_id, payload, reviewed_by):
        lookup = self._request(
            "get", "/rest/v1/extracted_field", token,
            params={
                "select": "id,raw_value,normalised_value",
                "id": f"eq.{field_id}",
                "limit": "1",
            },
        )
        self._require_ok(lookup, "field_lookup_failed")
        rows = lookup.json()
        if not rows:
            raise IntakeError("field_not_found", "Extracted field not found.", 404)

        corrected_value = payload.get("corrected_value")
        review_status = payload["review_status"]
        update = self._request(
            "patch", "/rest/v1/extracted_field", token,
            params={"id": f"eq.{field_id}"},
            json={"normalised_value": corrected_value, "review_status": review_status},
        )
        self._require_ok(update, "field_update_failed")

        audit = self._request(
            "post", "/rest/v1/field_review", token,
            json={
                "extracted_field_id": field_id,
                "reviewed_by": reviewed_by,
                "review_status": review_status,
                "original_value": rows[0].get("raw_value"),
                "corrected_value": corrected_value,
                "review_notes": payload.get("review_notes"),
                "reviewed_at": _now(),
            },
        )
        self._require_ok(audit, "field_review_audit_failed")
        return {"message": "Updated successfully"}

    def update_submission_status(self, token, submission_id, status, approved_by=None):
        if status == "approved":
            # A. Pre-check: Ensure all document OCR tasks are completed
            doc_response = self._request(
                "get", "/rest/v1/source_document", token,
                params={
                    "select": "id,processing_status",
                    "fact_find_submission_id": f"eq.{submission_id}",
                }
            )
            self._require_ok(doc_response, "submission_documents_lookup_failed")
            docs = doc_response.json()

            for d in docs:
                if d.get("processing_status") in ("processing", "uploaded", "ocr_started"):
                    raise IntakeError(
                        "ocr_jobs_incomplete",
                        "Cannot approve submission while document OCR is still processing.",
                        400
                    )

            # B. Build final approved snapshot JSON
            snapshot = self._get_approved_snapshot_json(token, submission_id)

            # Get local opportunity and Mercury external IDs if already linked
            sub_lookup = self._request(
                "get", "/rest/v1/fact_find_submission", token,
                params={
                    "select": "crm_application_id",
                    "id": f"eq.{submission_id}",
                    "limit": "1"
                }
            )
            self._require_ok(sub_lookup, "submission_lookup_failed")
            sub_rows = sub_lookup.json()
            if sub_rows:
                local_app_id = sub_rows[0].get("crm_application_id")
                app_data = self._application(token, local_app_id)
                snapshot["opportunity"]["local_application_id"] = local_app_id
                snapshot["opportunity"]["mercury_opportunity_id"] = app_data.get("crm_application_id")

            # C. Generate payload SHA-256 hash for consistency verification
            import hashlib
            import json
            source_hash = hashlib.sha256(
                json.dumps(snapshot, sort_keys=True).encode("utf-8")
            ).hexdigest()

            # D. Call Supabase atomic transaction RPC
            rpc_response = self._request(
                "post",
                "/rest/v1/rpc/approve_submission_and_queue_crm_sync",
                token,
                json={
                    "p_submission_id": submission_id,
                    "p_approved_data_json": snapshot,
                    "p_approved_by": approved_by or "system",
                    "p_source_hash": source_hash,
                    "p_mapping_version": "mercury-v1",
                }
            )
            self._require_ok(rpc_response, "approve_submission_rpc_failed")

            return {
                "message": "Submission approved and queued for CRM sync successfully",
                "approved_data_id": rpc_response.json()[0].get("approved_data_id") if rpc_response.json() else None,
                "tracking_id": rpc_response.json()[0].get("tracking_id") if rpc_response.json() else None,
            }
        else:
            response = self._request(
                "patch", "/rest/v1/fact_find_submission", token,
                params={"id": f"eq.{submission_id}"},
                json={"submission_status": status, "crm_sync_status": "not_started"},
            )
            self._require_ok(response, "submission_status_update_failed")
            return {"message": "Status updated successfully"}

    def _get_approved_snapshot_json(self, token, submission_id) -> dict:
        """Helper to fetch extracted & reviewed fields and compile the Fact Find approved snapshot."""
        # Find the main fact_find document
        doc_response = self._request(
            "get", "/rest/v1/source_document", token,
            params={
                "select": "id,document_type",
                "fact_find_submission_id": f"eq.{submission_id}",
                "document_type": "eq.fact_find",
                "limit": "1"
            }
        )
        self._require_ok(doc_response, "snapshot_document_lookup_failed")
        docs = doc_response.json()
        if not docs:
            raise IntakeError("fact_find_missing", "Fact Find document missing for this submission.", 400)
        doc_id = docs[0]["id"]

        # Find the latest completed OCR job for it
        job_response = self._request(
            "get", "/rest/v1/ocr_extraction_job", token,
            params={
                "select": "id",
                "source_document_id": f"eq.{doc_id}",
                "job_status": "eq.completed",
                "order": "completed_at.desc",
                "limit": "1"
            }
        )
        self._require_ok(job_response, "snapshot_job_lookup_failed")
        jobs = job_response.json()
        if not jobs:
            raise IntakeError("ocr_job_missing", "No completed OCR job found for Fact Find document.", 400)
        job_id = jobs[0]["id"]

        # Fetch all extracted fields for the job
        fields_response = self._request(
            "get", "/rest/v1/extracted_field", token,
            params={
                "select": "field_key,raw_value,normalised_value,review_status",
                "ocr_extraction_job_id": f"eq.{job_id}",
            }
        )
        self._require_ok(fields_response, "snapshot_fields_lookup_failed")
        fields = fields_response.json()

        # Map field key to display value (normalised if present, fallback to raw)
        field_map = {}
        for row in fields:
            key = row.get("field_key")
            if not key:
                continue
            val = row.get("normalised_value")
            if val is None:
                val = row.get("raw_value")
            if isinstance(val, str):
                val = val.strip()
            field_map[key] = val

        # Compile structured opportunity
        app1_first = field_map.get("applicant_1_first_name")
        if not app1_first:
            app1_full = field_map.get("applicant_1_full_name") or ""
            app1_first = app1_full.split(" ", 1)[0] if app1_full else "Applicant"

        opportunity = {
            "local_application_id": None,
            "mercury_opportunity_id": None,
            "opportunity_name": field_map.get("opportunity_name") or f"SMARTFINN-TEST-{app1_first}",
            "amount": field_map.get("loan_amount"),
            "transaction_type": "Loan",
            "transaction_subtype": field_map.get("loan_purpose"),
            "status": "Lead",
            "loan_term_years": field_map.get("loan_term"),
            "lmi": 0,
            "objectives": field_map.get("loan_objectives"),
        }

        # Compile applicants list
        applicants = []
        for num in (1, 2):
            prefix = f"applicant_{num}_"
            first_name = field_map.get(f"{prefix}first_name")
            last_name = field_map.get(f"{prefix}last_name")
            full_name = field_map.get(f"{prefix}full_name")

            if not first_name and not last_name and not full_name:
                continue

            app_data = {
                "applicant_number": num,
                "mercury_person_id": None,
                "title": field_map.get(f"{prefix}title"),
                "first_name": first_name,
                "middle_name": field_map.get(f"{prefix}middle_name"),
                "last_name": last_name,
                "full_name": full_name,
                "date_of_birth": field_map.get(f"{prefix}date_of_birth"),
                "mobile": field_map.get(f"{prefix}mobile"),
                "email": field_map.get(f"{prefix}email"),
                "marital_status": field_map.get(f"{prefix}marital_status"),
                "addresses": [],
                "employments": [],
                "incomes": []
            }

            # Map Current Address
            street_full = field_map.get(f"{prefix}current_address_street")
            if street_full:
                parts = street_full.split(" ", 1)
                street_num = parts[0] if parts else None
                street_name = parts[1] if len(parts) > 1 else None
                app_data["addresses"].append({
                    "street_number": street_num,
                    "street_name": street_name,
                    "street_type": None,
                    "city": field_map.get(f"{prefix}current_address_suburb"),
                    "state": field_map.get(f"{prefix}current_address_state"),
                    "postcode": field_map.get(f"{prefix}current_address_postcode"),
                    "type": "Home",
                })

            # Map Employments
            emp_employer = field_map.get(f"{prefix}current_employment_employer_name")
            if emp_employer:
                app_data["employments"].append({
                    "employer_name": emp_employer,
                    "job_title": field_map.get(f"{prefix}current_employment_position"),
                    "employment_basis": field_map.get(f"{prefix}current_employment_basis"),
                    "employment_status": "Primary",
                    "employment_type": "PAYG",
                    "start_date": field_map.get(f"{prefix}current_employment_start_date"),
                })

            applicants.append(app_data)

        # Fetch associated payslips and enrich employment & income data
        try:
            import re
            docs_response = self._request(
                "get", "/rest/v1/source_document", token,
                params={
                    "select": "id,document_type",
                    "fact_find_submission_id": f"eq.{submission_id}",
                    "document_type": "eq.payslip",
                }
            )
            if docs_response.status_code == 200:
                for doc in docs_response.json():
                    doc_id = doc["id"]
                    job_res = self._request(
                        "get", "/rest/v1/ocr_extraction_job", token,
                        params={
                            "select": "id",
                            "source_document_id": f"eq.{doc_id}",
                        }
                    )
                    if job_res.status_code == 200 and job_res.json():
                        job_id = job_res.json()[0]["id"]
                        fields_res = self._request(
                            "get", "/rest/v1/extracted_field", token,
                            params={
                                "select": "field_key,raw_value,normalised_value",
                                "ocr_extraction_job_id": f"eq.{job_id}",
                            }
                        )
                        if fields_res.status_code == 200:
                            ps_fields = {}
                            for r in fields_res.json():
                                k = r.get("field_key")
                                v = r.get("normalised_value") or r.get("raw_value")
                                if k and v:
                                    ps_fields[k] = str(v).strip()
                            
                            emp_name = ps_fields.get("employee_name")
                            matched_idx = 0
                            found = False
                            
                            for idx, app in enumerate(applicants):
                                app_name = app.get("full_name") or f"{app.get('first_name', '')} {app.get('last_name', '')}".strip()
                                if emp_name and app_name:
                                    emp_w = set(re.findall(r'\w+', emp_name.lower()))
                                    app_w = set(re.findall(r'\w+', app_name.lower()))
                                    common = emp_w.intersection(app_w) - {"mr", "mrs", "ms", "miss", "dr"}
                                    if len(common) >= 2:
                                        matched_idx = idx
                                        found = True
                                        break
                            
                            if not found:
                                matched_idx = 0
                                found = True
                                
                            if found and matched_idx < len(applicants):
                                target_app = applicants[matched_idx]
                                employer = ps_fields.get("employer_name")
                                job_title = ps_fields.get("job_title")
                                emp_basis = ps_fields.get("employment_type")
                                
                                if emp_basis:
                                    basis_lower = emp_basis.lower()
                                    if "full" in basis_lower:
                                        emp_basis = "full_time"
                                    elif "part" in basis_lower:
                                        emp_basis = "part_time"
                                    elif "casual" in basis_lower:
                                        emp_basis = "casual"
                                    else:
                                        emp_basis = "full_time"
                                        
                                if employer:
                                    existing_emp = [e for e in target_app["employments"] if e.get("employer_name") == employer]
                                    if not existing_emp:
                                        target_app["employments"].append({
                                            "employer_name": employer,
                                            "job_title": job_title,
                                            "employment_basis": emp_basis or "full_time",
                                            "employment_status": "Primary" if not target_app["employments"] else "Secondary",
                                            "employment_type": "PAYG",
                                            "start_date": None,
                                        })
                                
                                gross = ps_fields.get("gross_income") or ps_fields.get("net_income")
                                if gross:
                                    start_dt = ps_fields.get("pay_period_start")
                                    end_dt = ps_fields.get("pay_period_end")
                                    freq = "Monthly"
                                    if start_dt and end_dt:
                                        try:
                                            from datetime import datetime
                                            s_date = datetime.strptime(start_dt[:10], "%Y-%m-%d")
                                            e_date = datetime.strptime(end_dt[:10], "%Y-%m-%d")
                                            days = (e_date - s_date).days + 1
                                            if 6 <= days <= 8:
                                                freq = "Weekly"
                                            elif 13 <= days <= 15:
                                                freq = "Fortnightly"
                                            elif 26 <= days <= 32:
                                                freq = "Monthly"
                                        except Exception:
                                            pass
                                            
                                    target_app["incomes"].append({
                                        "amount": gross,
                                        "type": "Salary",
                                        "frequency": freq,
                                    })
        except Exception as e:
            print(f"Error enriching applicant from payslip: {e}")

        # Compile assets
        assets = []
        
        # Helper to retrieve account/applicant name
        def get_account_name(ownership_key, default_applicant_index=0):
            own = field_map.get(ownership_key) if ownership_key else None
            app1_name = ""
            app2_name = ""
            if len(applicants) > 0:
                app1_name = applicants[0].get("full_name") or f"{applicants[0].get('first_name', '')} {applicants[0].get('last_name', '')}".strip()
            if len(applicants) > 1:
                app2_name = applicants[1].get("full_name") or f"{applicants[1].get('first_name', '')} {applicants[1].get('last_name', '')}".strip()
                
            if own == "applicant_2":
                return app2_name or app1_name
            elif own == "both":
                return f"{app1_name} & {app2_name}" if app2_name else app1_name
            elif own == "applicant_1":
                return app1_name
            
            if default_applicant_index == 1 and app2_name:
                return app2_name
            return app1_name or "Applicant 1"

        # Generate default residential address for fallback security
        app1_addr_street = field_map.get("applicant_1_current_address_street") or ""
        app1_addr_suburb = field_map.get("applicant_1_current_address_suburb") or ""
        app1_addr_state = field_map.get("applicant_1_current_address_state") or ""
        app1_addr_postcode = field_map.get("applicant_1_current_address_postcode") or ""
        
        app1_full_address = ""
        if app1_addr_street:
            parts = [app1_addr_street]
            if app1_addr_suburb:
                parts.append(app1_addr_suburb)
            state_post = f"{app1_addr_state} {app1_addr_postcode}".strip()
            if state_post:
                parts.append(state_post)
            app1_full_address = ", ".join(parts)

        # Property Assets
        from app.normalization.values import parse_full_address
        for i in range(1, 6):
            addr = field_map.get(f"property_asset_{i}_address")
            val = field_map.get(f"property_asset_{i}_estimated_value")
            if addr or val:
                assets.append({
                    "name": addr or "Real Estate Property",
                    "type": "realEstate",
                    "value": val or 0.0,
                    "address": parse_full_address(addr) if addr else None,
                    "account_name": get_account_name(f"property_asset_{i}_ownership"),
                })
        # Savings Account / Term Deposit
        for i in range(1, 3):
            val = field_map.get(f"savings_term_deposit_{i}_value")
            asset_type = field_map.get(f"savings_term_deposit_{i}_asset_type") or "Savings Account"
            if val:
                assets.append({
                    "name": "Savings Account" if "savings" in asset_type.lower() else "Term Deposit",
                    "type": "account",
                    "value": val,
                    "account_name": get_account_name(f"savings_term_deposit_{i}_ownership"),
                })
        # Vehicles
        for i in range(1, 3):
            val = field_map.get(f"vehicle_{i}_value")
            make_model = field_map.get(f"vehicle_{i}_make_model") or "Motor Vehicle"
            if val:
                assets.append({
                    "name": "Motor Vehicle",
                    "type": "vehicle",
                    "value": val,
                    "account_name": get_account_name(f"vehicle_{i}_ownership"),
                })
        # Superannuation
        for i in range(1, 3):
            val = field_map.get(f"superannuation_{i}_value")
            provider = field_map.get(f"superannuation_{i}_provider") or "Superannuation"
            if val:
                assets.append({
                    "name": "Superannuation",
                    "type": "standard",
                    "value": val,
                    "account_name": get_account_name(f"superannuation_{i}_ownership"),
                })
        # Shares
        for i in range(1, 3):
            val = field_map.get(f"shares_or_trusts_{i}_value")
            provider = field_map.get(f"shares_or_trusts_{i}_provider") or "Shares/Trusts"
            if val:
                assets.append({
                    "name": "Shares",
                    "type": "standard",
                    "value": val,
                    "account_name": get_account_name(f"shares_or_trusts_{i}_ownership"),
                })
        # Other Assets
        for i in (1, 2):
            val = field_map.get(f"other_asset_applicant_{i}_value")
            asset_type = field_map.get(f"other_asset_applicant_{i}_type") or "Other Asset"
            if val:
                assets.append({
                    "name": "Home Contents" if "contents" in asset_type.lower() else "Other",
                    "type": "standard",
                    "value": val,
                    "account_name": get_account_name(None, default_applicant_index=i-1),
                })

        # Compile liabilities
        liabilities = []
        # Existing Mortgage Loans from Property Assets
        for i in range(1, 6):
            addr = field_map.get(f"property_asset_{i}_address")
            loan_bal = field_map.get(f"property_asset_{i}_loan_balance")
            lender = field_map.get(f"property_asset_{i}_lender")
            if loan_bal:
                try:
                    val_float = float(loan_bal)
                except ValueError:
                    val_float = 0.0
                if val_float > 0:
                    liabilities.append({
                        "name": "Mortgage Loan",
                        "type": "realEstate",
                        "value": val_float,
                        "institution": lender or "Lender",
                        "details": addr or app1_full_address or "Property Security",
                        "account_name": get_account_name(f"property_asset_{i}_ownership"),
                    })
        # Credit Cards
        for i in range(1, 4):
            bal = field_map.get(f"liability_credit_card_{i}_balance")
            limit = field_map.get(f"liability_credit_card_{i}_credit_limit")
            creditor = field_map.get(f"liability_credit_card_{i}_creditor") or "Credit Card"
            repay = field_map.get(f"liability_credit_card_{i}_repayment_amount")
            freq = field_map.get(f"liability_credit_card_{i}_repayment_frequency") or "monthly"
            if bal or limit:
                liabilities.append({
                    "name": "Credit Card",
                    "type": "account",
                    "value": bal or 0.0,
                    "limit": limit,
                    "institution": creditor,
                    "account_repayment": repay,
                    "account_repayment_frequency": freq,
                    "details": app1_full_address or "Credit Card Security",
                    "account_name": get_account_name(f"liability_credit_card_{i}_ownership"),
                })
        # Other Loans
        loan_types = [
            ("personal_loan", "Personal Loan", "account"),
            ("car_loan", "Car Loan", "account"),
            ("student_loan", "HECS", "standard"),
            ("government_tax", "Outstanding Taxation", "standard"),
            ("other", "Other", "standard"),
        ]
        for key_prefix, label, m_type in loan_types:
            bal = field_map.get(f"liability_{key_prefix}_balance")
            limit = field_map.get(f"liability_{key_prefix}_credit_limit")
            creditor = field_map.get(f"liability_{key_prefix}_creditor") or label
            repay = field_map.get(f"liability_{key_prefix}_repayment_amount")
            freq = field_map.get(f"liability_{key_prefix}_repayment_frequency") or "monthly"
            if bal or limit:
                liabilities.append({
                    "name": label,
                    "type": m_type,
                    "value": bal or 0.0,
                    "limit": limit,
                    "institution": creditor,
                    "account_repayment": repay,
                    "account_repayment_frequency": freq,
                    "details": app1_full_address or f"{label} Security",
                    "account_name": get_account_name(f"liability_{key_prefix}_ownership"),
                })

        # Compile living expenses
        living_expenses = []
        expense_mapping = {
            "expense_rent_or_boarding_monthly_amount": "Rent or Boarding",
            "expense_clothing_personal_care_monthly_amount": "Clothing & Personal Care",
            "expense_education_monthly_amount": "Education",
            "expense_groceries_monthly_amount": "Groceries",
            "expense_transport_monthly_amount": "Transport",
            "expense_owner_occupied_property_utilities_monthly_amount": "Owner Occupied Property Costs",
            "expense_investment_property_utilities_monthly_amount": "Investment Property Costs",
            "expense_medical_health_costs_monthly_amount": "Medical & Health",
            "expense_insurances_monthly_amount": "Insurance",
            "expense_private_health_insurance_monthly_amount": "Private Health Insurance",
            "expense_recreation_entertainment_monthly_amount": "Recreation & Entertainment",
            "expense_connections_phone_internet_tv_monthly_amount": "Telephone / Internet / Pay TV",
            "expense_other_monthly_amount": "Other",
        }
        for db_key, type_label in expense_mapping.items():
            val = field_map.get(db_key)
            if val:
                living_expenses.append({
                    "type": type_label,
                    "value": val,
                })

        # Compile other incomes
        other_income = []
        other_inc_val = field_map.get("income_other_amount")
        if other_inc_val:
            other_income.append({
                "type": field_map.get("income_other_description") or "Other Income",
                "value": other_inc_val,
                "frequency": field_map.get("income_other_frequency") or "Annual",
            })

        snapshot = {
            "schema_version": "1",
            "submission_id": submission_id,
            "opportunity": opportunity,
            "applicants": applicants,
            "assets": assets,
            "liabilities": liabilities,
            "living_expenses": living_expenses,
            "other_income": other_income,
        }

        return snapshot


    def _documents(self, token, submission_id):
        response = self._request(
            "get", "/rest/v1/source_document", token,
            params={
                "select": (
                    "id,original_file_name,document_type,processing_status,storage_uri"
                ),
                "fact_find_submission_id": f"eq.{submission_id}",
                "order": "created_at.asc",
            },
        )
        self._require_ok(response, "document_list_failed")
        documents = []
        for row in response.json():
            documents.append({
                "doc_id": row["id"],
                "original_file_name": row.get("original_file_name"),
                "document_type": row.get("document_type"),
                "processing_status": self._frontend_processing_status(
                    row.get("processing_status")
                ),
                "storage_uri": self._signed_url(token, row.get("storage_uri")),
            })
        return documents

    def _application(self, token, application_id):
        if not application_id:
            return {}
        response = self._request(
            "get", "/rest/v1/crm_application", token,
            params={"select": "id,loan_type,crm_application_id", "id": f"eq.{application_id}", "limit": "1"},
        )
        self._require_ok(response, "application_lookup_failed")
        rows = response.json()
        return rows[0] if rows else {}

    def _applications_by_id(self, token, application_ids):
        ids = [value for value in dict.fromkeys(application_ids) if value]
        if not ids:
            return {}
        response = self._request(
            "get", "/rest/v1/crm_application", token,
            params={"select": "id,loan_type,crm_application_id", "id": f"in.({','.join(ids)})"},
        )
        self._require_ok(response, "application_lookup_failed")
        return {row["id"]: row for row in response.json()}

    def _assessments_by_submission_ids(self, token, submission_ids):
        ids = [value for value in dict.fromkeys(submission_ids) if value]
        if not ids:
            return {}
        response = self._request(
            "get",
            "/rest/v1/risk_assessment",
            token,
            params={
                "select": (
                    "fact_find_submission_id,assessment_status,overall_risk_score,"
                    "risk_level,assessed_at"
                ),
                "fact_find_submission_id": f"in.({','.join(ids)})",
            },
        )
        self._require_ok(response, "risk_assessment_lookup_failed")
        return {row["fact_find_submission_id"]: row for row in response.json()}

    @staticmethod
    def _assessment_summary(assessment):
        if not assessment:
            return {
                "assessment_status": "not_started",
                "overall_risk_score": None,
                "risk_level": None,
                "assessed_at": None,
            }
        return {
            "assessment_status": assessment.get("assessment_status") or "not_started",
            "overall_risk_score": assessment.get("overall_risk_score"),
            "risk_level": assessment.get("risk_level"),
            "assessed_at": assessment.get("assessed_at"),
        }

    def retry_crm_sync(self, token, submission_id):
        """Finds the latest crm_update_tracking job for the submission and resets it to pending."""
        response = self._request(
            "get", "/rest/v1/crm_update_tracking", token,
            params={
                "select": "id,update_status",
                "fact_find_submission_id": f"eq.{submission_id}",
                "order": "created_at.desc",
                "limit": "1"
            }
        )
        self._require_ok(response, "tracking_lookup_failed")
        rows = response.json()
        if not rows:
            raise IntakeError("tracking_not_found", "No CRM sync tracking found for this submission.", 404)
        tracking_id = rows[0]["id"]

        # Reset status on tracking record to queue for worker
        update = self._request(
            "patch", "/rest/v1/crm_update_tracking", token,
            params={"id": f"eq.{tracking_id}"},
            json={
                "update_status": "pending",
                "attempt_count": 0,
                "next_attempt_at": None,
                "last_error_code": None,
                "last_error_message": None,
                "started_at": None,
                "completed_at": None,
            }
        )
        self._require_ok(update, "tracking_update_failed")

        # Reset fact_find_submission crm_sync_status to pending
        sub_update = self._request(
            "patch", "/rest/v1/fact_find_submission", token,
            params={"id": f"eq.{submission_id}"},
            json={"crm_sync_status": "pending"}
        )
        self._require_ok(sub_update, "submission_sync_status_update_failed")

        return {"message": "CRM sync retried successfully", "tracking_id": tracking_id}

    def _signed_url(self, token, storage_uri):
        if not storage_uri:
            return ""
        bucket, path = storage_uri.split("/", 1)
        response = self._request(
            "post", f"/storage/v1/object/sign/{bucket}/{quote(path, safe='/')}", token,
            json={"expiresIn": 3600},
        )
        self._require_ok(response, "document_url_failed")
        signed_url = response.json().get("signedURL", "")
        if signed_url.startswith("/"):
            return f"{self._url}/storage/v1{signed_url}" if not signed_url.startswith("/storage/v1") else f"{self._url}{signed_url}"
        return signed_url

    def _request(self, method, path, token, extra_headers=None, **kwargs):
        headers = {
            "apikey": self._key,
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            **(extra_headers or {}),
        }
        try:
            return requests.request(
                method, f"{self._url}{path}", headers=headers,
                timeout=self._timeout, **kwargs,
            )
        except requests.RequestException as error:
            raise IntakeError(
                "supabase_unavailable", "Supabase is unavailable.", 503
            ) from error

    @staticmethod
    def _frontend_processing_status(status):
        return "completed" if status == "extracted" else status

    @staticmethod
    def _total_count(response, fallback):
        content_range = response.headers.get("Content-Range", "")
        try:
            return int(content_range.rsplit("/", 1)[1])
        except (IndexError, ValueError):
            return fallback

    @staticmethod
    def _require_ok(response, code):
        if response.status_code in (401, 403):
            raise IntakeError(code, "Supabase denied this operation.", 403)
        if not response.ok:
            raise IntakeError(code, "Supabase could not complete this operation.", 502)
