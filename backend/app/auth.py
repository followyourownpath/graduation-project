from functools import wraps

from flask import current_app, g, jsonify, request

from app.services.auth import AuthenticationError, SupabaseAuthService


def _error_response(error: AuthenticationError):
    return jsonify({"error": {"code": error.code, "message": error.message}}), error.status


def require_staff(view):
    """Require a valid Supabase user JWT and an active staff profile."""

    @wraps(view)
    def wrapped(*args, **kwargs):
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
