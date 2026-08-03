import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests


@dataclass
class DocumentIntelligenceError(Exception):
    code: str
    message: str
    status: int


class AzureDocumentIntelligenceClient:
    """Small REST client for Azure Document Intelligence asynchronous analysis."""

    def __init__(
        self,
        endpoint: str,
        key: str,
        model: str,
        api_version: str,
        request_timeout: float = 30.0,
        analysis_timeout: float = 120.0,
        poll_interval: float = 1.0,
        session=None,
        sleep=time.sleep,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._key = key
        self._model = model
        self._api_version = api_version
        self._request_timeout = request_timeout
        self._analysis_timeout = analysis_timeout
        self._poll_interval = poll_interval
        self._session = session or requests.Session()
        self._sleep = sleep

    def analyze(self, content: bytes, mime_type: str) -> dict[str, Any]:
        self._ensure_configured()
        model = quote(self._model, safe="")
        analyze_url = (
            f"{self._endpoint}/documentintelligence/documentModels/"
            f"{model}:analyze"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": self._key,
            "Content-Type": mime_type,
            "Accept": "application/json",
        }

        max_retries = 5
        retry_delay = 3.0
        response = None
        for attempt in range(max_retries):
            try:
                response = self._session.post(
                    analyze_url,
                    params={"api-version": self._api_version},
                    headers=headers,
                    data=content,
                    timeout=self._request_timeout,
                )
                if response.status_code == 429:
                    # Rate limit reached: sleep and retry
                    self._sleep(retry_delay)
                    continue
                break
            except requests.RequestException as error:
                if attempt == max_retries - 1:
                    raise self._unavailable() from error
                self._sleep(retry_delay)

        if response is None:
            raise self._unavailable()

        if response.status_code != 202:
            self._raise_response_error(response)

        operation_url = response.headers.get("Operation-Location")
        if not operation_url:
            raise DocumentIntelligenceError(
                "azure_invalid_response",
                "Azure did not return an operation location.",
                502,
            )

        return self._poll(operation_url)

    def _poll(self, operation_url: str) -> dict[str, Any]:
        deadline = time.monotonic() + self._analysis_timeout
        headers = {
            "Ocp-Apim-Subscription-Key": self._key,
            "Accept": "application/json",
        }

        while time.monotonic() < deadline:
            try:
                response = self._session.get(
                    operation_url,
                    headers=headers,
                    timeout=self._request_timeout,
                )
            except requests.RequestException as error:
                raise self._unavailable() from error

            if response.status_code == 429:
                self._sleep(3.0)
                continue

            if not response.ok:
                self._raise_response_error(response)

            result = response.json()
            status = str(result.get("status", "")).lower()
            if status == "succeeded":
                return result
            if status in {"failed", "canceled"}:
                raise DocumentIntelligenceError(
                    "azure_analysis_failed",
                    "Azure could not analyze the document.",
                    422,
                )
            if status not in {"notstarted", "running"}:
                raise DocumentIntelligenceError(
                    "azure_invalid_response",
                    "Azure returned an unknown analysis status.",
                    502,
                )
            self._sleep(self._poll_interval)

        raise DocumentIntelligenceError(
            "azure_analysis_timeout",
            "Azure document analysis did not finish before the timeout.",
            504,
        )

    def _ensure_configured(self) -> None:
        if not all((self._endpoint, self._key, self._model, self._api_version)):
            raise DocumentIntelligenceError(
                "azure_not_configured",
                "Azure Document Intelligence is not configured.",
                503,
            )

    @staticmethod
    def _unavailable() -> DocumentIntelligenceError:
        return DocumentIntelligenceError(
            "azure_unavailable",
            "Azure Document Intelligence is unavailable.",
            503,
        )

    @staticmethod
    def _raise_response_error(response) -> None:
        if response.status_code == 429:
            raise DocumentIntelligenceError(
                "azure_rate_limited",
                "Azure Document Intelligence rate limit was reached.",
                503,
            )
        if response.status_code in (400, 415, 422):
            raise DocumentIntelligenceError(
                "azure_document_rejected",
                "Azure rejected the document or analysis request.",
                422,
            )
        if response.status_code in (401, 403):
            raise DocumentIntelligenceError(
                "azure_authentication_failed",
                "Azure Document Intelligence credentials were rejected.",
                503,
            )
        raise DocumentIntelligenceError(
            "azure_service_error",
            "Azure Document Intelligence returned an unexpected response.",
            502,
        )
