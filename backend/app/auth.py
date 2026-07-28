import os
from functools import wraps

from flask import current_app, g, jsonify, request

from app.services.auth import AuthenticationError, SupabaseAuthService


def _error_response(error: AuthenticationError):
    return jsonify({"error": {"code": error.code, "message": error.message}}), error.status


def require_staff(view):
    """Require a valid Supabase user JWT and an active staff profile."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        # DEMO BYPASS: We skip verifying the token and just inject a dummy user.
        # This is controlled by the AUTH_DEMO_BYPASS environment variable.
        bypass_env = os.getenv("AUTH_DEMO_BYPASS", "false").lower()
        if bypass_env == "true" or bypass_env == "1":
            g.current_user = {"id": "demo_user", "email": "demo@smartfinn.com"}
            g.staff_profile = {"id": "demo_profile"}
            
            secret = current_app.config.get("SUPABASE_SECRET_KEY", "")
            pub = current_app.config.get("SUPABASE_PUBLISHABLE_KEY", "")
            g.access_token = secret if secret else pub
            
            return view(*args, **kwargs)

        # Real Auth logic
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            error = AuthenticationError("bearer_token_required", "Missing or invalid Authorization header", 401)
            return _error_response(error)

        token = auth_header.split(" ")[1]
        try:
            auth_service = current_app.extensions["auth_service"]
            auth_data = auth_service.authenticate_staff(token)
            g.current_user = auth_data["user"]
            g.staff_profile = auth_data["staff_profile"]
            g.access_token = token
            return view(*args, **kwargs)
        except AuthenticationError as error:
            return _error_response(error)

    return wrapped
