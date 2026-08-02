from uuid import UUID

from flask import Blueprint, current_app, g, jsonify, request

from app.auth import require_staff
from app.services.intake import IntakeError


rules_engine_bp = Blueprint("rules_engine", __name__, url_prefix="/api/v1")


def _error(error: IntakeError):
    body = {"error": {"code": error.code, "message": error.message}}
    if error.details is not None:
        body["error"]["details"] = error.details
    return jsonify(body), error.status


def _uuid(value, name):
    try:
        UUID(value)
    except (ValueError, TypeError):
        return jsonify(
            {
                "error": {
                    "code": f"invalid_{name}",
                    "message": f"{name} must be a UUID.",
                }
            }
        ), 400
    return None


@rules_engine_bp.post("/submissions/<submission_id>/risk-assessment")
@require_staff
def create_or_update_risk_assessment(submission_id):
    invalid = _uuid(submission_id, "submission_id")
    if invalid:
        return invalid
    try:
        report, created = current_app.extensions["rules_engine_service"].assess(
            g.access_token, submission_id, g.current_user["id"]
        )
    except IntakeError as error:
        return _error(error)
    return jsonify(report), 201 if created else 200


@rules_engine_bp.get("/submissions/<submission_id>/risk-assessment")
@require_staff
def get_risk_assessment(submission_id):
    invalid = _uuid(submission_id, "submission_id")
    if invalid:
        return invalid
    try:
        report = current_app.extensions["rules_engine_service"].get_assessment(
            g.access_token, submission_id
        )
    except IntakeError as error:
        return _error(error)
    return jsonify(report)
