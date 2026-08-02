import logging
import requests
from typing import Any, Dict, List, Optional

from app.services.intake import IntakeError

logger = logging.getLogger("crm_repository")


class SupabaseCrmRepository:
    """Handles all Supabase database queries and updates for CRM Writeback integrations."""

    def __init__(self, supabase_url: str, secret_key: str, timeout_seconds: float = 20.0):
        self._url = supabase_url.rstrip("/")
        # We use Supabase Secret Key (service_role_key) to bypass RLS for background workers
        self._key = secret_key
        self._timeout = timeout_seconds

    def _request(self, method: str, path: str, json_data=None, params=None, extra_headers=None) -> requests.Response:
        headers = {
            "apikey": self._key,
            "Authorization": f"Bearer {self._key}",
            "Accept": "application/json",
            **(extra_headers or {}),
        }
        if json_data is not None:
            headers["Content-Type"] = "application/json"

        try:
            response = requests.request(
                method,
                f"{self._url}{path}",
                headers=headers,
                json=json_data,
                params=params,
                timeout=self._timeout,
            )
            return response
        except requests.RequestException as e:
            raise IntakeError("supabase_unavailable", f"Supabase unavailable: {str(e)}", 503)

    def get_pending_trackings(self) -> List[Dict[str, Any]]:
        """Fetches pending CRM update tracking jobs."""
        response = self._request(
            "get",
            "/rest/v1/crm_update_tracking",
            params={
                "select": "id,fact_find_submission_id,crm_application_id,approved_data_id,update_status,attempt_count,next_attempt_at",
                "update_status": "in.(pending,failed_retryable)",
                "order": "created_at.asc",
            },
        )
        if not response.ok:
            logger.error(f"Failed to fetch pending tracking jobs: {response.text}")
            return []
        return response.json()

    def get_tracking(self, tracking_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a single tracking job with its associated approved snapshot JSON."""
        response = self._request(
            "get",
            "/rest/v1/crm_update_tracking",
            params={
                "select": (
                    "id,fact_find_submission_id,crm_application_id,update_status,attempt_count,"
                    "approved_fact_find_data(id,approved_data_json)"
                ),
                "id": f"eq.{tracking_id}",
                "limit": "1",
            },
        )
        if not response.ok or not response.json():
            return None
        return response.json()[0]

    def update_tracking(self, tracking_id: str, updates: Dict[str, Any]) -> bool:
        """Updates tracking job status and metrics."""
        response = self._request(
            "patch",
            "/rest/v1/crm_update_tracking",
            params={"id": f"eq.{tracking_id}"},
            json_data=updates,
        )
        if not response.ok:
            logger.error(f"Failed to update tracking {tracking_id}: {response.text}")
            return False
        return True

    def get_update_items(self, tracking_id: str) -> List[Dict[str, Any]]:
        """Gets all synced item steps for a tracking job."""
        response = self._request(
            "get",
            "/rest/v1/crm_update_item",
            params={
                "select": (
                    "id,crm_update_tracking_id,sequence_number,entity_type,operation,"
                    "local_reference,mercury_unique_id,status,attempt_count"
                ),
                "crm_update_tracking_id": f"eq.{tracking_id}",
                "order": "sequence_number.asc",
            },
        )
        if not response.ok:
            logger.error(f"Failed to fetch update items for {tracking_id}: {response.text}")
            return []
        return response.json()

    def upsert_update_item(self, item: Dict[str, Any]) -> Optional[str]:
        """Inserts or updates a sync item task record."""
        headers = {"Prefer": "return=representation"}
        
        # Check if item exists by crm_update_tracking_id and local_reference/sequence_number
        query_params = {
            "crm_update_tracking_id": f"eq.{item['crm_update_tracking_id']}",
            "sequence_number": f"eq.{item['sequence_number']}",
            "limit": "1",
        }
        exist_response = self._request("get", "/rest/v1/crm_update_item", params=query_params)
        
        if exist_response.ok and exist_response.json():
            # Update existing
            existing_id = exist_response.json()[0]["id"]
            response = self._request(
                "patch",
                "/rest/v1/crm_update_item",
                params={"id": f"eq.{existing_id}"},
                json_data=item,
                extra_headers={"Prefer": "return=representation"},
            )
        else:
            # Insert new
            response = self._request(
                "post",
                "/rest/v1/crm_update_item",
                json_data=item,
                params={"select": "id"},
                extra_headers={"Prefer": "return=representation"},
            )

        if not response.ok:
            logger.error(f"Failed to upsert crm_update_item: {response.text}")
            return None
        
        rows = response.json()
        return rows[0]["id"] if rows else None

    def update_local_ids_and_sync_status(
        self, submission_id: str, crm_app_uuid: str, mercury_id_str: str, sync_status: str
    ) -> bool:
        """Sets the external Mercury Opportunity uniqueId back to crm_application and updates fact_find_submission sync status."""
        # 1. Update crm_application
        app_update = self._request(
            "patch",
            "/rest/v1/crm_application",
            params={"id": f"eq.{crm_app_uuid}"},
            json_data={"crm_application_id": mercury_id_str, "application_status": "synced"},
        )
        if not app_update.ok:
            logger.error(f"Failed to update crm_application: {app_update.text}")
            return False

        # 2. Update submission
        sub_update = self._request(
            "patch",
            "/rest/v1/fact_find_submission",
            params={"id": f"eq.{submission_id}"},
            json_data={"crm_sync_status": sync_status},
        )
        if not sub_update.ok:
            logger.error(f"Failed to update fact_find_submission crm_sync_status: {sub_update.text}")
            return False

        return True
