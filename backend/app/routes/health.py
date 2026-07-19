from flask import Blueprint, current_app, jsonify


health_bp = Blueprint("health", __name__)


@health_bp.get("/")
def root():
    return jsonify({"service": "smartfinn-backend", "status": "ok"})


@health_bp.get("/api/v1/health")
def health():
    integrations = {
        "supabase": bool(
            current_app.config["SUPABASE_URL"]
            and current_app.config["SUPABASE_PUBLISHABLE_KEY"]
        ),
        "azure_document_intelligence": bool(
            current_app.config["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"]
            and current_app.config["AZURE_DOCUMENT_INTELLIGENCE_KEY"]
            and current_app.config["AZURE_DOCUMENT_INTELLIGENCE_MODEL"]
            and current_app.config["AZURE_DOCUMENT_INTELLIGENCE_API_VERSION"]
        ),
    }
    return jsonify(
        {
            "service": "smartfinn-backend",
            "status": "ok",
            "integrations_configured": integrations,
        }
    )
