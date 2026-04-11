"""Configuration and constants for V.I.T.A.L."""

import os

from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
NEBIUS_API_KEY = os.environ.get("NEBIUS_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

# --- Thryve ---
THRYVE_USER = os.environ.get("THRYVE_USER", "")
THRYVE_PASSWORD = os.environ.get("THRYVE_PASSWORD", "")
THRYVE_APP_ID = os.environ.get("THRYVE_APP_ID", "")
THRYVE_APP_SECRET = os.environ.get("THRYVE_APP_SECRET", "")
THRYVE_BASE_URL = os.environ.get("THRYVE_BASE_URL", "https://api-qa.thryve.de/v5")

# --- Demo mode ---
# When DEMO_MODE=1, ThryveClient returns synthetic vitals tuned to the seeded
# memory baselines instead of hitting the Thryve QA API. Used on stage because
# the QA catalog profiles are connected but contain no time-series data.
DEMO_MODE = os.environ.get("DEMO_MODE", "0").lower() in ("1", "true", "yes")

# --- Models ---
STT_MODEL = "voxtral-mini-latest"
REALTIME_STT_MODEL = "voxtral-mini-transcribe-realtime-2602"
LLM_MODEL = "mistral-small-latest"
TTS_MODEL = "voxtral-mini-tts-latest"
OCR_MODEL = "mistral-ocr-latest"

# --- Audio ---
SAMPLE_RATE = 16_000  # Voxtral STT requirement
TTS_SAMPLE_RATE = 24_000  # Voxtral TTS output
STT_LANGUAGE = os.environ.get("STT_LANGUAGE", "fr")
TTS_VOICE_ID = os.environ.get("TTS_VOICE_ID", "")

# --- Demo voice IDs (Voxtral French) ---
DEMO_USER_VOICE = "e0580ce5-e63c-4cbe-88c8-a983b80c5f1f"  # Marie - Curious
DEMO_ASSISTANT_VOICE = "5a271406-039d-46fe-835b-fbbb00eaf08d"  # Marie - Neutral

# --- Health Server ---
HEALTH_SERVER_HOST = os.environ.get("VITAL_HOST", "0.0.0.0")
HEALTH_SERVER_PORT = int(os.environ.get("VITAL_PORT", "8420"))

# --- External Services ---
NEBIUS_BASE_URL = "https://api.studio.nebius.com/v1"

# --- PostgreSQL ---
POSTGRES_USER = os.environ.get("POSTGRES_USER", "")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)


def require_thryve_credentials() -> None:
    """Fail loudly at startup if Thryve credentials are missing.

    Called from the FastAPI lifespan so the server refuses to boot without them.
    """
    missing = [
        name
        for name, value in [
            ("THRYVE_USER", THRYVE_USER),
            ("THRYVE_PASSWORD", THRYVE_PASSWORD),
            ("THRYVE_APP_ID", THRYVE_APP_ID),
            ("THRYVE_APP_SECRET", THRYVE_APP_SECRET),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"Missing Thryve env vars: {', '.join(missing)}. "
            "Copy .env.example to .env and fill them in. "
            "Credentials are provided by the hackathon organizer."
        )
