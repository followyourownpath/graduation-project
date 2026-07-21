from uuid import UUID

from flask import Blueprint, current_app, g, jsonify, request

from app.auth import require_staff
from app.services.intake import IntakeError


review_bp = Blueprint("review", __name__, url_prefix="/api/v1")
REVIEW_STATUSES = {"pending", "corrected", "confirmed", "rejected"}


def _error(code, message, status=400):
    return jsonify({"error": {"code": code, "message": message}}), status


def _uuid(value, name):
    try:
        UUID(value)
    except (ValueError, TypeError):
        return _error(f"invalid_{name}", f"{name} must be a UUID.")
    return None


@review_bp.get("/submissions")
@require_staff
def list_submissions():
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 50))
    except ValueError:
        return _error("invalid_pagination", "page and limit must be integers.")
    if page < 1 or limit < 1 or limit > 100:
        return _error("invalid_pagination", "page must be positive and limit must be between 1 and 100.")

    try:
        result = current_app.extensions["review_service"].list_submissions(
            g.access_token, page, limit, request.args.get("status")
        )
    except IntakeError as error:
        return _error(error.code, error.message, error.status)
    return jsonify(result)


@review_bp.get("/submissions/<submission_id>")
@require_staff
def get_submission(submission_id):
    invalid = _uuid(submission_id, "submission_id")
    if invalid:
        return invalid
    try:
        result = current_app.extensions["review_service"].get_submission(
            g.access_token, submission_id
        )
    except IntakeError as error:
        return _error(error.code, error.message, error.status)
    return jsonify(result)


@review_bp.get("/documents/<document_id>/extracted-data")
@require_staff
def get_extracted_data(document_id):
    invalid = _uuid(document_id, "document_id")
    if invalid:
        return invalid
    try:
        result = current_app.extensions["review_service"].get_extracted_data(
            g.access_token, document_id
        )
    except IntakeError as error:
        return _error(error.code, error.message, error.status)
    return jsonify(result)


@review_bp.put("/fields/<field_id>/review")
@require_staff
def review_field(field_id):
    invalid = _uuid(field_id, "field_id")
    if invalid:
        return invalid
    payload = request.get_json(silent=True) or {}
    review_status = str(payload.get("review_status", "")).strip().lower()
    if review_status not in REVIEW_STATUSES:
        return _error("invalid_review_status", "review_status is not supported.")
    if "corrected_value" not in payload:
        return _error("corrected_value_required", "corrected_value is required.")
    payload["review_status"] = review_status

    try:
        result = current_app.extensions["review_service"].review_field(
            g.access_token, field_id, payload, g.current_user["id"]
        )
    except IntakeError as error:
        return _error(error.code, error.message, error.status)
    return jsonify(result)
