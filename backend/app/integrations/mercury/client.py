import hashlib
import json
import logging
import time
import requests

from app.integrations.mercury.errors import (
    MercuryApiError,
    MercuryInvalidResponseError,
    MercuryNetworkError,
    MercuryWriteBlockedError,
)

logger = logging.getLogger("mercury_client")


class MercuryClient:
    """Connective Mercury CRM REST API client with built-in safety switches and masked URL logs."""

    def __init__(
        self,
        base_url: str,
        token: str,
        api_key: str,
        timeout_seconds: float = 20.0,
        allow_writes: bool = False,
        dry_run: bool = True,
        test_record_prefix: str = "SMARTFINN-TEST-",
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.api_key = api_key
        self.timeout = timeout_seconds
        self.allow_writes = allow_writes
        self.dry_run = dry_run
        self.test_record_prefix = test_record_prefix

    def _request(self, method: str, path: str, json_data=None, params=None) -> dict:
        method = method.upper()
        clean_path = path.lstrip("/")
        url = f"{self.base_url}/{self.token}/{clean_path}"

        headers = {
            "x-api-key": self.api_key,
            "Accept": "application/json",
        }
        if json_data is not None:
            headers["Content-Type"] = "application/json"

        # Mask token in logs
        logged_url = f"{self.base_url}/[MASKED_TOKEN]/{clean_path}"

        # Write Protection Safety Switch
        if method in ("POST", "PUT", "DELETE", "PATCH"):
            if not self.allow_writes:
                logger.warning("Mercury write blocked: MERCURY_ALLOW_WRITES is False")
                raise MercuryWriteBlockedError("Mercury writes are disabled by configuration.")
            if self.dry_run:
                payload_hash = ""
                if json_data is not None:
                    payload_hash = hashlib.sha256(
                        json.dumps(json_data, sort_keys=True).encode("utf-8")
                    ).hexdigest()
                logger.info(
                    f"Mercury DRY_RUN: {method} {logged_url} (payload hash: {payload_hash})"
                )
                return {"status": 200, "uniqueId": "dry-run-uuid-placeholder"}

            # Prefix constraint on Opportunity operations
            if "opportunities" in clean_path:
                opp_name = None
                if json_data:
                    opp_name = json_data.get("opportunityName")
                if opp_name and not opp_name.startswith(self.test_record_prefix):
                    logger.warning(
                        f"Mercury write blocked: Opportunity name '{opp_name}' "
                        f"does not start with test prefix '{self.test_record_prefix}'"
                    )
                    raise MercuryWriteBlockedError(
                        f"Opportunity name must start with '{self.test_record_prefix}' in test mode."
                    )

        start_time = time.time()
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                json=json_data,
                params=params,
                timeout=self.timeout,
            )
            duration_ms = int((time.time() - start_time) * 1000)

            # Log only permitted information (no token, no keys, no raw PII in url)
            logger.info(
                f"Mercury API call: method={method} path={clean_path} "
                f"status={response.status_code} duration_ms={duration_ms}"
            )

            if not response.ok:
                raise MercuryApiError(
                    response.text[:500], response.status_code, response.text
                )

            if response.status_code == 204 or not response.text.strip():
                return {}

            try:
                res_data = response.json()
            except ValueError as e:
                raise MercuryInvalidResponseError("Response is not valid JSON") from e

            # Parse uniqueId for successful POST creations
            if method == "POST":
                # relatedParties create returns JSON but might not have uniqueId in some sub-entities, 
                # but standard Contact/Opportunity/Asset/Liability/Address/Employment/Income do.
                if not res_data.get("uniqueId") and not "relatedParties" in clean_path:
                    raise MercuryInvalidResponseError(
                        f"POST response missing uniqueId: {json.dumps(res_data)}"
                    )

            return res_data

        except requests.Timeout as e:
            logger.error(f"Mercury API Timeout: method={method} path={clean_path}")
            raise MercuryNetworkError("Connection timed out") from e
        except requests.RequestException as e:
            logger.error(f"Mercury API RequestException: method={method} path={clean_path} error={str(e)}")
            raise MercuryNetworkError(str(e)) from e

    # --- Opportunities API ---
    def create_opportunity(self, payload: dict) -> dict:
        return self._request("POST", "opportunities", json_data=payload)

    def update_opportunity(self, id: str, payload: dict) -> dict:
        return self._request("PUT", f"opportunities/{id}", json_data=payload)

    def get_opportunity(self, id: str) -> dict:
        return self._request("GET", f"opportunities/{id}")

    # --- Contacts API ---
    def create_contact(self, payload: dict) -> dict:
        return self._request("POST", "contacts", json_data=payload)

    def update_contact(self, id: str, payload: dict) -> dict:
        return self._request("PUT", f"contacts/{id}", json_data=payload)

    def get_contact(self, id: str) -> dict:
        return self._request("GET", f"contacts/{id}")

    # --- Related Parties API ---
    def create_related_party(self, opportunity_id: str, payload: dict) -> dict:
        return self._request(
            "POST", f"opportunities/{opportunity_id}/relatedParties", json_data=payload
        )

    def update_related_party(self, opportunity_id: str, related_party_id: str, payload: dict) -> dict:
        return self._request(
            "PUT",
            f"opportunities/{opportunity_id}/relatedParties/{related_party_id}",
            json_data=payload,
        )

    def get_related_parties(self, opportunity_id: str) -> dict:
        return self._request("GET", f"opportunities/{opportunity_id}/relatedParties")

    # --- Address API ---
    def create_address(self, person_id: str, payload: dict) -> dict:
        return self._request("POST", f"contacts/{person_id}/addresses", json_data=payload)

    def update_address(self, person_id: str, address_id: str, payload: dict) -> dict:
        return self._request(
            "PUT", f"contacts/{person_id}/addresses/{address_id}", json_data=payload
        )

    def get_addresses(self, person_id: str) -> dict:
        return self._request("GET", f"contacts/{person_id}/addresses")

    # --- Employment API ---
    def create_employment(self, person_id: str, payload: dict) -> dict:
        return self._request("POST", f"contacts/{person_id}/employments", json_data=payload)

    def update_employment(self, person_id: str, employment_id: str, payload: dict) -> dict:
        return self._request(
            "PUT", f"contacts/{person_id}/employments/{employment_id}", json_data=payload
        )

    def get_employments(self, person_id: str) -> dict:
        return self._request("GET", f"contacts/{person_id}/employments")

    # --- Incomes API ---
    def create_income(self, person_id: str, payload: dict) -> dict:
        return self._request("POST", f"contacts/{person_id}/incomes", json_data=payload)

    def update_income(self, person_id: str, income_id: str, payload: dict) -> dict:
        return self._request(
            "PUT", f"contacts/{person_id}/incomes/{income_id}", json_data=payload
        )

    def get_incomes(self, person_id: str) -> dict:
        return self._request("GET", f"contacts/{person_id}/incomes")

    # --- Assets API ---
    def create_asset(self, opportunity_id: str, payload: dict) -> dict:
        return self._request("POST", f"opportunities/{opportunity_id}/assets", json_data=payload)

    def update_asset(self, opportunity_id: str, asset_id: str, payload: dict) -> dict:
        return self._request(
            "PUT", f"opportunities/{opportunity_id}/assets/{asset_id}", json_data=payload
        )

    def get_assets(self, opportunity_id: str) -> dict:
        return self._request("GET", f"opportunities/{opportunity_id}/assets")

    # --- Liabilities API ---
    def create_liability(self, opportunity_id: str, payload: dict) -> dict:
        return self._request(
            "POST", f"opportunities/{opportunity_id}/liabilities", json_data=payload
        )

    def update_liability(self, opportunity_id: str, liability_id: str, payload: dict) -> dict:
        return self._request(
            "PUT",
            f"opportunities/{opportunity_id}/liabilities/{liability_id}",
            json_data=payload,
        )

    def get_liabilities(self, opportunity_id: str) -> dict:
        return self._request("GET", f"opportunities/{opportunity_id}/liabilities")

    # --- Extensions (Living Expenses / Other Income) API ---
    def get_extension(self, opportunity_id: str, extension_key: str) -> dict:
        return self._request("GET", f"opportunities/{opportunity_id}/extension/{extension_key}")

    def create_extension(self, opportunity_id: str, extension_key: str, payload: dict) -> dict:
        return self._request(
            "POST", f"opportunities/{opportunity_id}/extension/{extension_key}", json_data=payload
        )

    def update_extension(self, opportunity_id: str, extension_key: str, payload: dict) -> dict:
        return self._request(
            "PUT", f"opportunities/{opportunity_id}/extension/{extension_key}", json_data=payload
        )
