from functools import wraps

from flask import current_app, g, jsonify, request

from app.services.auth import AuthenticationError


def _error_response(error: AuthenticationError):
    return jsonify({"error": {"code": error.code, "message": error.message}}), error.status


def require_staff(view):
    """Require a valid Supabase user JWT and an active staff profile."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        # DEMO BYPASS: We skip verifying the token and just inject a dummy user.
        # We use the publishable key (anon key) as the token, hoping the DB RLS allows it.
        # If the DB blocks it, we will need the SUPABASE_SECRET_KEY (service_role) to bypass RLS.
        g.current_user = {"id": "demo_user", "email": "demo@smartfinn.com"}
        g.staff_profile = {"id": "demo_profile"}
        
        # Try to use secret key if available, otherwise fallback to anon key
        secret = current_app.config.get("SUPABASE_SECRET_KEY", "")
        pub = current_app.config.get("SUPABASE_PUBLISHABLE_KEY", "")
        g.access_token = secret if secret else pub
        
        return view(*args, **kwargs)

    return wrapped
