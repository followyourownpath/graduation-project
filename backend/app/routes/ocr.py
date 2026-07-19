from uuid import UUID

from flask import Blueprint, current_app, g, jsonify

from app.auth import require_staff
from app.services.azure_document_intelligence import DocumentIntelligenceError
from app.services.intake import IntakeError


ocr_bp = Blueprint("ocr", __name__, url_prefix="/api/v1/documents")


@ocr_bp.post("/<document_id>/ocr")
@require_staff
def run_ocr(document_id):
    try:
        UUID(document_id)
    except ValueError:
        return jsonify({"error": {"code": "invalid_document_id", "message": "document_id must be a UUID."}}), 400
    try:
        result = current_app.extensions["ocr_pipeline"].process(g.access_token, document_id)
    except (DocumentIntelligenceError, IntakeError) as error:
        return jsonify({"error": {"code": error.code, "message": error.message}}), error.status
    return jsonify(result), 200
