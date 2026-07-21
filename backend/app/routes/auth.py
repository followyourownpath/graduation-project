from flask import Blueprint, g, jsonify

from app.auth import require_staff


auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@auth_bp.get("/me")
@require_staff
def me():
    return jsonify(
        {
            "user": g.current_user,
            "staff_profile": g.staff_profile,
        }
    )
