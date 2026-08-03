import json
import logging
from typing import Any, Dict, List

from app.integrations.mercury.client import MercuryClient
from app.integrations.mercury.errors import MercuryApiError

logger = logging.getLogger("mercury_extension_merge")


class ExtensionMerger:
    """Handles GET-merge-PUT flow for Opportunity extensions to avoid overwriting existing data.

    Applies to:
    - livingExpense
    - otherIncome
    """

    def __init__(self, client: MercuryClient):
        self.client = client

    def merge_and_put_living_expenses(
        self, opportunity_id: str, local_expenses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """GETs current living expenses from Mercury, merges with local_expenses, and PUTs back."""
        online_data = {}
        try:
            online_data = self.client.get_extension(opportunity_id, "livingExpense") or {}
        except MercuryApiError as e:
            if e.status_code == 404:
                online_data = {}
            else:
                raise e

        # If response is {} or has no uniqueId, the extension does not exist yet in CRM
        exists = bool(online_data.get("uniqueId"))

        # Ensure value is deserialized from JSON string
        online_val = online_data.get("value") or "[]"
        if isinstance(online_val, str):
            try:
                online_list = json.loads(online_val)
            except Exception:
                online_list = []
        elif isinstance(online_val, list):
            online_list = online_val
        else:
            online_list = []

        # Merge local expenses into online_list
        # local_expenses format: [{"type": "Housing/Rent", "value": 1500.0}]
        # online_list item format: {"type": "Housing/Rent", "amount": "1200.00", "frequency": "Monthly"}
        online_by_type = {item.get("type"): item for item in online_list if item.get("type")}

        for local_item in local_expenses:
            exp_type = local_item.get("type")
            exp_val = local_item.get("value")
            if not exp_type:
                continue

            # Clean/Format local amount
            from app.integrations.mercury.payloads import format_number
            numeric_val = format_number(exp_val) or 0.0
            amount_str = f"{numeric_val:.2f}"

            if exp_type in online_by_type:
                online_by_type[exp_type]["amount"] = amount_str
                online_by_type[exp_type]["frequency"] = "Monthly"
            else:
                new_item = {
                    "type": exp_type,
                    "amount": amount_str,
                    "frequency": "Monthly",
                }
                online_list.append(new_item)
                online_by_type[exp_type] = new_item

        # Build request payload
        payload = dict(online_data)
        payload.update({
            "parentId": opportunity_id,
            "parentType": "loan",
            "key": "livingExpense",
            "value": json.dumps(online_list)
        })

        if exists:
            return self.client.update_extension(opportunity_id, "livingExpense", payload)
        else:
            return self.client.create_extension(opportunity_id, "livingExpense", payload)

    def merge_and_put_other_income(
        self, opportunity_id: str, local_incomes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """GETs current other incomes from Mercury, merges with local_incomes, and PUTs back."""
        online_data = {}
        try:
            online_data = self.client.get_extension(opportunity_id, "otherIncome") or {}
        except MercuryApiError as e:
            if e.status_code == 404:
                online_data = {}
            else:
                raise e

        # If response is {} or has no uniqueId, the extension does not exist yet in CRM
        exists = bool(online_data.get("uniqueId"))

        # Ensure value is deserialized from JSON string
        online_val = online_data.get("value") or "[]"
        if isinstance(online_val, str):
            try:
                online_list = json.loads(online_val)
            except Exception:
                online_list = []
        elif isinstance(online_val, list):
            online_list = online_val
        else:
            online_list = []

        online_by_type = {item.get("type"): item for item in online_list if item.get("type")}

        for local_item in local_incomes:
            inc_type = local_item.get("type")
            inc_val = local_item.get("value")
            frequency = local_item.get("frequency") or "Annual"
            # Standardize frequency case for Mercury enums
            frequency = frequency.capitalize()
            if not inc_type:
                continue

            from app.integrations.mercury.payloads import format_number
            numeric_val = format_number(inc_val) or 0.0
            amount_str = f"{numeric_val:.2f}"

            if inc_type in online_by_type:
                online_by_type[inc_type]["amount"] = amount_str
                online_by_type[inc_type]["frequency"] = frequency
            else:
                new_item = {
                    "type": inc_type,
                    "amount": amount_str,
                    "frequency": frequency,
                }
                online_list.append(new_item)
                online_by_type[inc_type] = new_item

        payload = dict(online_data)
        payload.update({
            "parentId": opportunity_id,
            "parentType": "loan",
            "key": "otherIncome",
            "value": json.dumps(online_list)
        })

        if exists:
            return self.client.update_extension(opportunity_id, "otherIncome", payload)
        else:
            return self.client.create_extension(opportunity_id, "otherIncome", payload)
