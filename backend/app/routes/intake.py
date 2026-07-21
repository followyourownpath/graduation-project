from pathlib import Path
from uuid import UUID

from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.utils import secure_filename

from app.auth import require_staff
from app.services.intake import IntakeError


intake_bp = Blueprint("intake", __name__, url_prefix="/api/v1")

LOAN_TYPES = {"purchase", "investment", "refinance", "first_home", "self_employed"}
DOCUMENT_TYPES = {
    "payslip", "bank_statement_3m", "id_100", "contract_of_sale",
    "property_valuation", "rental_appraisal", "existing_loan_statements",
    "first_home_grant", "tax_return", "ato_notice", "profit_loss",
}


def _error(code, message, status=400):
    return jsonify({"error": {"code": code, "message": message}}), status


def _detected_mime(content: bytes):
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith((b"II*\x00", b"MM\x00*")):
        return "image/tiff"
    return None


@intake_bp.post("/applications")
@require_staff
def create_application():
    payload = request.get_json(silent=True) or {}
    customer_name = str(payload.get("customer_name", "")).strip()
    loan_type = str(payload.get("loan_type", "")).strip()
    if not customer_name:
        return _error("customer_name_required", "customer_name is required.")
    if loan_type not in LOAN_TYPES:
        return _error("invalid_loan_type", "loan_type is not supported.")

    try:
        result = current_app.extensions["intake_service"].create_application(
            g.access_token,
            {**payload, "customer_name": customer_name, "loan_type": loan_type},
        )
    except IntakeError as error:
        return _error(error.code, error.message, error.status)
    return jsonify(result), 201


@intake_bp.post("/submissions/<submission_id>/documents")
@require_staff
def upload_document(submission_id):
    try:
        UUID(submission_id)
    except ValueError:
        return _error("invalid_submission_id", "submission_id must be a UUID.")

    document_type = request.form.get("document_type", "").strip()
    if document_type not in DOCUMENT_TYPES:
        return _error("invalid_document_type", "document_type is not supported.")

    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return _error("file_required", "A document file is required.")

    filename = secure_filename(uploaded.filename)
    if not filename or Path(filename).suffix.lower() not in {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
        return _error("invalid_file_extension", "The file extension is not supported.")

    content = uploaded.read()
    mime_type = _detected_mime(content)
    if not mime_type:
        return _error("invalid_file_content", "The file content is not a supported document type.")

    try:
        result = current_app.extensions["intake_service"].upload_document(
            g.access_token, submission_id, document_type, filename, mime_type, content
        )
    except IntakeError as error:
        return _error(error.code, error.message, error.status)
    return jsonify(result), 201
