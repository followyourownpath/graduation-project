from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.errors import register_error_handlers
from app.routes.auth import auth_bp
from app.routes.health import health_bp
from app.routes.intake import intake_bp
from app.routes.ocr import ocr_bp
from app.routes.review import review_bp
from app.services.auth import SupabaseAuthService
from app.services.intake import SupabaseIntakeService
from app.services.azure_document_intelligence import AzureDocumentIntelligenceClient
from app.services.ocr_pipeline import OcrPipelineService, SupabaseOcrRepository
from app.services.review import SupabaseReviewService


def create_app(
    config_object: type[Config] = Config,
    auth_service=None,
    intake_service=None,
    ocr_pipeline=None,
    review_service=None,
) -> Flask:
    """Create and configure the SmartFinn API application."""
    app = Flask(__name__)
    app.config.from_object(config_object)

    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=False,
    )

    app.extensions["auth_service"] = auth_service or SupabaseAuthService(
        app.config["SUPABASE_URL"],
        app.config["SUPABASE_PUBLISHABLE_KEY"],
    )
    app.extensions["intake_service"] = intake_service or SupabaseIntakeService(
        app.config["SUPABASE_URL"],
        app.config["SUPABASE_PUBLISHABLE_KEY"],
    )
    app.extensions["review_service"] = review_service or SupabaseReviewService(
        app.config["SUPABASE_URL"],
        app.config["SUPABASE_PUBLISHABLE_KEY"],
    )
    azure_client = AzureDocumentIntelligenceClient(
        app.config["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"],
        app.config["AZURE_DOCUMENT_INTELLIGENCE_KEY"],
        app.config["AZURE_DOCUMENT_INTELLIGENCE_MODEL"],
        app.config["AZURE_DOCUMENT_INTELLIGENCE_API_VERSION"],
    )
    app.extensions["ocr_pipeline"] = ocr_pipeline or OcrPipelineService(
        SupabaseOcrRepository(app.config["SUPABASE_URL"], app.config["SUPABASE_PUBLISHABLE_KEY"]),
        azure_client,
        app.config["AZURE_DOCUMENT_INTELLIGENCE_MODEL"],
    )

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(intake_bp)
    app.register_blueprint(ocr_bp)
    app.register_blueprint(review_bp)
    register_error_handlers(app)

    return app
