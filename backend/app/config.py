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

    # Mercury CRM configuration
    MERCURY_ENABLED = os.getenv("MERCURY_ENABLED", "false").lower() == "true"
    MERCURY_ALLOW_WRITES = os.getenv("MERCURY_ALLOW_WRITES", "false").lower() == "true"
    MERCURY_DRY_RUN = os.getenv("MERCURY_DRY_RUN", "true").lower() == "true"
    MERCURY_BASE_URL = os.getenv("MERCURY_BASE_URL", "https://apis.connective.com.au/mercury/v1").rstrip("/")
    MERCURY_API_TOKEN = os.getenv("MERCURY_API_TOKEN", "")
    MERCURY_API_KEY = os.getenv("MERCURY_API_KEY", "")
    MERCURY_TIMEOUT_SECONDS = float(os.getenv("MERCURY_TIMEOUT_SECONDS", "20.0"))
    MERCURY_MAX_ATTEMPTS = int(os.getenv("MERCURY_MAX_ATTEMPTS", "5"))
    MERCURY_TEST_RECORD_PREFIX = os.getenv("MERCURY_TEST_RECORD_PREFIX", "SMARTFINN-TEST-")
    MERCURY_WORKER_POLL_SECONDS = float(os.getenv("MERCURY_WORKER_POLL_SECONDS", "5.0"))


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
    
    MERCURY_ENABLED = False
    MERCURY_ALLOW_WRITES = False
    MERCURY_DRY_RUN = True
    MERCURY_BASE_URL = ""
    MERCURY_API_TOKEN = ""
    MERCURY_API_KEY = ""
    MERCURY_TIMEOUT_SECONDS = 5.0
    MERCURY_MAX_ATTEMPTS = 1
    MERCURY_TEST_RECORD_PREFIX = "SMARTFINN-TEST-"
    MERCURY_WORKER_POLL_SECONDS = 1.0
