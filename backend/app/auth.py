from functools import wraps

from flask import current_app, g, jsonify, request

from app.services.auth import AuthenticationError


def _error_response(error: AuthenticationError):
    return jsonify({"error": {"code": error.code, "message": error.message}}), error.status


def require_staff(view):
    """Require a valid Supabase user JWT and an active staff profile."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        authorization = request.headers.get("Authorization", "")
        scheme, separator, token = authorization.partition(" ")

        if not separator or scheme.lower() != "bearer" or not token.strip():
            return _error_response(
                AuthenticationError(
                    "bearer_token_required",
                    "A Bearer access token is required.",
                    401,
                )
            )

        try:
            identity = current_app.extensions["auth_service"].authenticate_staff(
                token.strip()
            )
        except AuthenticationError as error:
            return _error_response(error)

        g.current_user = identity["user"]
        g.staff_profile = identity["staff_profile"]
        g.access_token = token.strip()
        return view(*args, **kwargs)

    return wrapped
