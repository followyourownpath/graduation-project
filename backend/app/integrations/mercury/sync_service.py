import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from app.integrations.mercury.client import MercuryClient
from app.integrations.mercury.errors import (
    MercuryApiError,
    MercuryError,
    MercuryNetworkError,
    MercuryWriteBlockedError,
)
from app.integrations.mercury.extension_merge import ExtensionMerger
from app.integrations.mercury.payloads import (
    build_address_payload,
    build_asset_payload,
    build_contact_payload,
    build_employment_payload,
    build_income_payload,
    build_liability_payload,
    build_opportunity_payload,
    build_related_party_payload,
)
from app.services.crm_repository import SupabaseCrmRepository

logger = logging.getLogger("mercury_sync_service")


class MercurySyncService:
    """Orchestrates the resumeable synchronization of approved data to Mercury CRM."""

    def __init__(
        self,
        client: MercuryClient,
        merger: ExtensionMerger,
        repository: SupabaseCrmRepository,
    ):
        self.client = client
        self.merger = merger
        self.repository = repository

    def sync_tracking_job(self, tracking_id: str) -> None:
        """Executes the end-to-end sync plan for a single tracking job, tracking progress at subtask level."""
        tracking = self.repository.get_tracking(tracking_id)
        if not tracking:
            logger.error(f"Tracking job {tracking_id} not found in database.")
            return

        submission_id = tracking["fact_find_submission_id"]
        crm_app_uuid = tracking["crm_application_id"]
        approved_data_record = tracking.get("approved_fact_find_data")

        if not approved_data_record or not approved_data_record.get("approved_data_json"):
            logger.error(f"Approved snapshot missing for tracking {tracking_id}.")
            self.repository.update_tracking(
                tracking_id,
                {
                    "update_status": "failed_permanent",
                    "last_error_code": "snapshot_missing",
                    "last_error_message": "No approved snapshot JSON found.",
                    "completed_at": None,
                },
            )
            return

        approved_data = approved_data_record["approved_data_json"]

        # Fetch existing sync subtasks to ensure resumeability (idempotency)
        existing_items = self.repository.get_update_items(tracking_id)
        # Create lookup map: local_ref -> completed_mercury_id
        completed_subtasks = {
            item["local_reference"]: item["mercury_unique_id"]
            for item in existing_items
            if item["status"] == "completed"
        }

        # Sequence counter to maintain task dependency ordering
        sequence_counter = 0

        # Subtask executor helper
        def execute_subtask(
            entity_type: str,
            operation: str,
            local_ref: str,
            api_callable: Callable[..., Dict[str, Any]],
            *args,
            **kwargs,
        ) -> Optional[str]:
            nonlocal sequence_counter
            sequence_counter += 1

            # Skip if already completed previously
            if local_ref in completed_subtasks:
                logger.info(f"Skipping completed subtask: {local_ref} -> {completed_subtasks[local_ref]}")
                return completed_subtasks[local_ref]

            # Upsert crm_update_item to pending/started
            item_data = {
                "crm_update_tracking_id": tracking_id,
                "sequence_number": sequence_counter,
                "entity_type": entity_type,
                "operation": operation,
                "local_reference": local_ref,
                "status": "pending",
                "attempt_count": 0,
            }
            self.repository.upsert_update_item(item_data)

            try:
                # Execute actual Mercury CRM API call
                result = api_callable(*args, **kwargs) or {}
                mercury_id = result.get("uniqueId") or result.get("id") or "synced"

                # Update item to completed
                item_data.update({
                    "status": "completed",
                    "mercury_unique_id": mercury_id,
                    "response_status": 200,
                })
                self.repository.upsert_update_item(item_data)
                logger.info(f"Subtask completed: {local_ref} -> {mercury_id}")
                return mercury_id

            except MercuryWriteBlockedError as e:
                item_data.update({
                    "status": "failed",
                    "error_code": e.code,
                    "error_message": str(e),
                })
                self.repository.upsert_update_item(item_data)
                raise e
            except MercuryApiError as e:
                item_data.update({
                    "status": "failed",
                    "error_code": e.code,
                    "error_message": f"API {e.status_code}: {e.response_body[:200]}",
                    "response_status": e.status_code,
                })
                self.repository.upsert_update_item(item_data)
                raise e
            except Exception as e:
                item_data.update({
                    "status": "failed",
                    "error_code": "unknown_error",
                    "error_message": str(e),
                })
                self.repository.upsert_update_item(item_data)
                raise e

        try:
            # 1. Sync Applicants (Contacts, Addresses, Employments, Incomes)
            synced_contacts = {} # applicant_number -> mercury_person_id
            for app in approved_data.get("applicants", []):
                app_num = app.get("applicant_number") or 1
                local_ref_contact = f"contact:applicant_number:{app_num}"

                # Split payload generation to keep it pure
                contact_payload = build_contact_payload(app)
                # Determine operation
                op = "update" if contact_payload.get("uniqueId") else "create"

                if op == "update":
                    person_id = execute_subtask(
                        "contact",
                        "update",
                        local_ref_contact,
                        self.client.update_contact,
                        contact_payload["uniqueId"],
                        contact_payload,
                    )
                else:
                    person_id = execute_subtask(
                        "contact",
                        "create",
                        local_ref_contact,
                        self.client.create_contact,
                        contact_payload,
                    )

                synced_contacts[app_num] = person_id

                # A. Sync Addresses
                for idx, addr in enumerate(app.get("addresses", [])):
                    local_ref_addr = f"address:applicant_number:{app_num}:index:{idx}"
                    addr_payload = build_address_payload(addr)
                    addr_op = "update" if addr_payload.get("uniqueId") else "create"

                    if addr_op == "update":
                        execute_subtask(
                            "address",
                            "update",
                            local_ref_addr,
                            self.client.update_address,
                            person_id,
                            addr_payload["uniqueId"],
                            addr_payload,
                        )
                    else:
                        execute_subtask(
                            "address",
                            "create",
                            local_ref_addr,
                            self.client.create_address,
                            person_id,
                            addr_payload,
                        )

                # B. Sync Employments
                for idx, emp in enumerate(app.get("employments", [])):
                    local_ref_emp = f"employment:applicant_number:{app_num}:index:{idx}"
                    emp_payload = build_employment_payload(emp, person_id)
                    emp_op = "update" if emp_payload.get("uniqueId") else "create"

                    if emp_op == "update":
                        execute_subtask(
                            "employment",
                            "update",
                            local_ref_emp,
                            self.client.update_employment,
                            person_id,
                            emp_payload["uniqueId"],
                            emp_payload,
                        )
                    else:
                        execute_subtask(
                            "employment",
                            "create",
                            local_ref_emp,
                            self.client.create_employment,
                            person_id,
                            emp_payload,
                        )

                # C. Sync Incomes
                for idx, inc in enumerate(app.get("incomes", [])):
                    local_ref_inc = f"income:applicant_number:{app_num}:index:{idx}"
                    inc_payload = build_income_payload(inc, person_id)
                    inc_op = "update" if inc_payload.get("uniqueId") else "create"

                    if inc_op == "update":
                        execute_subtask(
                            "income",
                            "update",
                            local_ref_inc,
                            self.client.update_income,
                            person_id,
                            inc_payload["uniqueId"],
                            inc_payload,
                        )
                    else:
                        execute_subtask(
                            "income",
                            "create",
                            local_ref_inc,
                            self.client.create_income,
                            person_id,
                            inc_payload,
                        )

            # 2. Sync Opportunity
            opp_data = approved_data.get("opportunity") or {}
            local_ref_opp = "opportunity:main"
            opp_payload = build_opportunity_payload(opp_data, self.client.test_record_prefix)
            opp_op = "update" if opp_payload.get("uniqueId") else "create"

            if opp_op == "update":
                opportunity_id = execute_subtask(
                    "opportunity",
                    "update",
                    local_ref_opp,
                    self.client.update_opportunity,
                    opp_payload["uniqueId"],
                    opp_payload,
                )
            else:
                opportunity_id = execute_subtask(
                    "opportunity",
                    "create",
                    local_ref_opp,
                    self.client.create_opportunity,
                    opp_payload,
                )

            # 3. Establish Related Parties Relationship
            for app_num, person_id in synced_contacts.items():
                local_ref_party = f"related_party:applicant_number:{app_num}"
                rel_type = "Primary applicant" if app_num == 1 else "Secondary applicant"
                party_payload = build_related_party_payload(person_id, rel_type)

                # Check if related party link already exists to prevent duplicate link creations
                def check_and_create_related_party():
                    try:
                        parties = self.client.get_related_parties(opportunity_id) or []
                        for p in parties:
                            if p.get("personID") == person_id:
                                logger.info(f"Related party link already exists online: {person_id}")
                                return {"uniqueId": p.get("uniqueId") or "already-linked"}
                    except Exception as e:
                        logger.warning(f"Failed checking related parties: {e}")
                    
                    return self.client.create_related_party(opportunity_id, party_payload)

                execute_subtask(
                    "related_party",
                    "create",
                    local_ref_party,
                    check_and_create_related_party,
                )

            # 4. Sync Assets & Liabilities
            for idx, asset in enumerate(approved_data.get("assets", [])):
                local_ref_asset = f"asset:index:{idx}"
                asset_payload = build_asset_payload(asset)
                asset_op = "update" if asset_payload.get("uniqueId") else "create"

                if asset_op == "update":
                    execute_subtask(
                        "asset",
                        "update",
                        local_ref_asset,
                        self.client.update_asset,
                        opportunity_id,
                        asset_payload["uniqueId"],
                        asset_payload,
                    )
                else:
                    execute_subtask(
                        "asset",
                        "create",
                        local_ref_asset,
                        self.client.create_asset,
                        opportunity_id,
                        asset_payload,
                    )

            for idx, liab in enumerate(approved_data.get("liabilities", [])):
                local_ref_liab = f"liability:index:{idx}"
                liab_payload = build_liability_payload(liab)
                liab_op = "update" if liab_payload.get("uniqueId") else "create"

                if liab_op == "update":
                    execute_subtask(
                        "liability",
                        "update",
                        local_ref_liab,
                        self.client.update_liability,
                        opportunity_id,
                        liab_payload["uniqueId"],
                        liab_payload,
                    )
                else:
                    execute_subtask(
                        "liability",
                        "create",
                        local_ref_liab,
                        self.client.create_liability,
                        opportunity_id,
                        liab_payload,
                    )

            # 5. Sync Extensions (GET-merge-PUT)
            local_expenses = approved_data.get("living_expenses", [])
            if local_expenses:
                execute_subtask(
                    "extension",
                    "update",
                    "extension:livingExpense",
                    self.merger.merge_and_put_living_expenses,
                    opportunity_id,
                    local_expenses,
                )

            local_incomes = approved_data.get("other_income", [])
            if local_incomes:
                execute_subtask(
                    "extension",
                    "update",
                    "extension:otherIncome",
                    self.merger.merge_and_put_other_income,
                    opportunity_id,
                    local_incomes,
                )

            # --- Sync Finished Successfully ---
            # Save the Opportunity ID back to local crm_application mapping
            self.repository.update_local_ids_and_sync_status(
                submission_id, crm_app_uuid, opportunity_id, "completed"
            )

            self.repository.update_tracking(
                tracking_id,
                {
                    "update_status": "completed",
                    "completed_at": datetime.now().isoformat(),
                    "last_error_code": None,
                    "last_error_message": None,
                },
            )

        except MercuryWriteBlockedError as e:
            # Environment safety switch triggered, this is a permanent configuration issue
            self.repository.update_tracking(
                tracking_id,
                {
                    "update_status": "failed_permanent",
                    "last_error_code": e.code,
                    "last_error_message": str(e),
                },
            )
            self.repository.update_local_ids_and_sync_status(
                submission_id, crm_app_uuid, "", "failed"
            )
            raise e

        except (MercuryApiError, MercuryNetworkError, Exception) as e:
            # Classify error as retryable vs permanent
            is_retryable = True
            err_code = getattr(e, "code", "unknown_error")
            err_msg = str(e)

            if isinstance(e, MercuryApiError):
                if e.status_code in (400, 401, 403, 404):
                    is_retryable = False

            new_status = "failed_retryable" if is_retryable else "failed_permanent"
            self.repository.update_tracking(
                tracking_id,
                {
                    "update_status": new_status,
                    "last_error_code": err_code,
                    "last_error_message": err_msg,
                },
            )
            
            # If permanently failed, mark sync status as failed
            if not is_retryable:
                self.repository.update_local_ids_and_sync_status(
                    submission_id, crm_app_uuid, "", "failed"
                )
            raise e
