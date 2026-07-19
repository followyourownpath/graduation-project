from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class AuthenticationError(Exception):
    code: str
    message: str
    status: int


class SupabaseAuthService:
    """Validate a user JWT and resolve its RLS-protected staff profile."""

    def __init__(
        self,
        supabase_url: str,
        publishable_key: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._supabase_url = supabase_url.rstrip("/")
        self._publishable_key = publishable_key
        self._timeout_seconds = timeout_seconds

    def authenticate_staff(self, access_token: str) -> dict[str, Any]:
        self._ensure_configured()
        user = self._get_user(access_token)
        profile = self._get_staff_profile(access_token, user["id"])

        if not profile.get("is_active"):
            raise AuthenticationError(
                "staff_inactive",
                "This staff account is inactive.",
                403,
            )

        return {"user": user, "staff_profile": profile}

    def _ensure_configured(self) -> None:
        if not self._supabase_url or not self._publishable_key:
            raise AuthenticationError(
                "supabase_not_configured",
                "Supabase authentication is not configured.",
                503,
            )

    def _headers(self, access_token: str) -> dict[str, str]:
        return {
            "apikey": self._publishable_key,
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    def _get_user(self, access_token: str) -> dict[str, Any]:
        try:
            response = requests.get(
                f"{self._supabase_url}/auth/v1/user",
                headers=self._headers(access_token),
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as error:
            raise AuthenticationError(
                "authentication_service_unavailable",
                "The authentication service is unavailable.",
                503,
            ) from error

        if response.status_code in (401, 403):
            raise AuthenticationError(
                "invalid_access_token",
                "The access token is invalid or expired.",
                401,
            )
        if not response.ok:
            raise AuthenticationError(
                "authentication_service_error",
                "The authentication service returned an unexpected response.",
                503,
            )

        user = response.json()
        if not user.get("id"):
            raise AuthenticationError(
                "invalid_access_token",
                "The access token did not resolve to a user.",
                401,
            )

        return {
            "id": user["id"],
            "email": user.get("email"),
        }

    def _get_staff_profile(
        self, access_token: str, user_id: str
    ) -> dict[str, Any]:
        try:
            response = requests.get(
                f"{self._supabase_url}/rest/v1/staff_profile",
                headers=self._headers(access_token),
                params={
                    "select": "user_id,full_name,role,is_active",
                    "user_id": f"eq.{user_id}",
                    "limit": "1",
                },
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as error:
            raise AuthenticationError(
                "staff_profile_service_unavailable",
                "The staff profile service is unavailable.",
                503,
            ) from error

        if response.status_code in (401, 403):
            raise AuthenticationError(
                "staff_access_denied",
                "The authenticated user cannot access a staff profile.",
                403,
            )
        if not response.ok:
            raise AuthenticationError(
                "staff_profile_service_error",
                "The staff profile service returned an unexpected response.",
                503,
            )

        profiles = response.json()
        if not profiles:
            raise AuthenticationError(
                "staff_profile_required",
                "The authenticated user does not have a staff profile.",
                403,
            )

        return profiles[0]
