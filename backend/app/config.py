import os

from dotenv import load_dotenv


load_dotenv()


def _csv_env(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


class Config:
    """Environment-backed application configuration.

    Integration credentials are optional during startup so the health endpoint and
    tests can run before Supabase and Azure are configured. Integration services
    will validate their own required settings when they are introduced.
    """

    JSON_SORT_KEYS = False
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))
    CORS_ORIGINS = _csv_env("CORS_ORIGINS", "http://localhost:3000")

    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_PUBLISHABLE_KEY = os.getenv(
        "SUPABASE_PUBLISHABLE_KEY", os.getenv("SUPABASE_ANON_KEY", "")
    )
    SUPABASE_SECRET_KEY = os.getenv(
        "SUPABASE_SECRET_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    )

    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv(
        "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", ""
    )
    AZURE_DOCUMENT_INTELLIGENCE_KEY = os.getenv(
        "AZURE_DOCUMENT_INTELLIGENCE_KEY", ""
    )
    AZURE_DOCUMENT_INTELLIGENCE_MODEL = os.getenv(
        "AZURE_DOCUMENT_INTELLIGENCE_MODEL", ""
    )
    AZURE_DOCUMENT_INTELLIGENCE_API_VERSION = os.getenv(
        "AZURE_DOCUMENT_INTELLIGENCE_API_VERSION", ""
    )
    AZURE_DOCUMENT_INTELLIGENCE_REGION = os.getenv(
        "AZURE_DOCUMENT_INTELLIGENCE_REGION", ""
    )


class TestConfig(Config):
    TESTING = True
    CORS_ORIGINS = ["http://localhost:3000"]
    SUPABASE_URL = ""
    SUPABASE_PUBLISHABLE_KEY = ""
    SUPABASE_SECRET_KEY = ""
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = ""
    AZURE_DOCUMENT_INTELLIGENCE_KEY = ""
    AZURE_DOCUMENT_INTELLIGENCE_MODEL = ""
    AZURE_DOCUMENT_INTELLIGENCE_API_VERSION = ""
    AZURE_DOCUMENT_INTELLIGENCE_REGION = ""
