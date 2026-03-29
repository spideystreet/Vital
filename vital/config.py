"""Configuration and constants for V.I.T.A.L."""

import os

from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")

# --- Models ---
STT_MODEL = "voxtral-mini-transcribe-2507"
LLM_MODEL = "mistral-small-latest"
TTS_MODEL = "voxtral-mini-tts-2603"

# --- Audio ---
SAMPLE_RATE = 16_000  # Voxtral STT requirement
TTS_SAMPLE_RATE = 24_000  # Voxtral TTS output
SILENCE_THRESHOLD = 500
SILENCE_DURATION = 1.5  # seconds
MAX_RECORD_SECONDS = 30
AUDIO_OUTPUT_DEVICE = os.environ.get("AUDIO_OUTPUT_DEVICE")
TTS_VOICE_ID = os.environ.get("TTS_VOICE_ID", "")

# --- Demo voice IDs (Voxtral French) ---
DEMO_USER_VOICE = "e0580ce5-e63c-4cbe-88c8-a983b80c5f1f"  # Marie - Curious
DEMO_ASSISTANT_VOICE = "5a271406-039d-46fe-835b-fbbb00eaf08d"  # Marie - Neutral

# --- Health Server ---
HEALTH_SERVER_HOST = os.environ.get("VITAL_HOST", "0.0.0.0")
HEALTH_SERVER_PORT = int(os.environ.get("VITAL_PORT", "8420"))

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

# --- UI ---
ORANGE = "#ff7000"
ORANGE_DIM = "#cc5500"
ORANGE_DARK = "#884400"
REFRESH_FPS = 15
