import os
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT, ".env"))

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "assistant_db")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-3-flash-preview")
GEMINI_LIVE_MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")
GEMINI_VOICE = os.getenv("GEMINI_VOICE", "Kore")

# Optional local OpenAI-compatible model gateway (e.g. OmniRoute).
OMNIROUTE_BASE_URL = os.getenv("OMNIROUTE_BASE_URL", "http://localhost:20128/v1").rstrip("/")
OMNIROUTE_API_KEY = os.getenv("OMNIROUTE_API_KEY", "")
OMNIROUTE_MODEL = os.getenv("OMNIROUTE_MODEL", "")
SABA_USER_ID = int(os.getenv("SABA_USER_ID", "1"))
SABA_ACCESS_CODE = os.getenv("SABA_ACCESS_CODE", "")
SABA_SESSION_SECRET = os.getenv("SABA_SESSION_SECRET", "")
SABA_SECURE_COOKIES = os.getenv("SABA_SECURE_COOKIES", "false").lower() in {"1", "true", "yes", "on"}

APP_NAME = "JAMAL-FAMILY-ASSISTANT"
ASSISTANT_NAME = "Saba"
# Optional creator-brand display. Keep it empty unless the owner chooses to expose it.
CREATOR_BRAND = os.getenv("CREATOR_BRAND", "")
CREATOR_TITLE = os.getenv("CREATOR_TITLE", "")
SABA_CREATOR_ACTIVATION_SECRET = os.getenv("SABA_CREATOR_ACTIVATION_SECRET", "")

# Clap activation is implemented as an optional local companion/bridge. It never sends
# always-on microphone audio to Gemini; it only emits an activation event after a local
# double-clap is detected.
CLAP_ACTIVATION_ENABLED = os.getenv("CLAP_ACTIVATION_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
CLAP_COUNT = int(os.getenv("CLAP_COUNT", "2"))
CLAP_MIN_GAP_MS = int(os.getenv("CLAP_MIN_GAP_MS", "120"))
CLAP_MAX_GAP_MS = int(os.getenv("CLAP_MAX_GAP_MS", "900"))
ACTIVATION_BRIDGE_HOST = os.getenv("ACTIVATION_BRIDGE_HOST", "127.0.0.1")
ACTIVATION_BRIDGE_PORT = int(os.getenv("ACTIVATION_BRIDGE_PORT", "8766"))
MAX_VOICE_CONNECTIONS = int(os.getenv("MAX_VOICE_CONNECTIONS", "32"))
MAX_ACTIVATION_CONNECTIONS = int(os.getenv("MAX_ACTIVATION_CONNECTIONS", "32"))
VOICE_MAX_TEXT_BYTES = int(os.getenv("VOICE_MAX_TEXT_BYTES", "32768"))
VOICE_MAX_AUDIO_BYTES = int(os.getenv("VOICE_MAX_AUDIO_BYTES", "262144"))
HTTP_RATE_LIMIT = int(os.getenv("HTTP_RATE_LIMIT", "120"))
HTTP_RATE_WINDOW_SECONDS = int(os.getenv("HTTP_RATE_WINDOW_SECONDS", "60"))
CREATOR_ACTIVATION_TTL_SECONDS = int(os.getenv("CREATOR_ACTIVATION_TTL_SECONDS", os.getenv("CREATOR_SESSION_TTL_SECONDS", "8")))
SABA_PROJECT_ROOT = os.path.abspath(os.getenv("SABA_PROJECT_ROOT", ROOT))

# Smart-home integrations
LG_THINQ_PAT = os.getenv("LG_THINQ_PAT", "")
LG_THINQ_CLIENT_ID = os.getenv("LG_THINQ_CLIENT_ID", "")
LG_THINQ_API_KEY = os.getenv("LG_THINQ_API_KEY", "")
LG_THINQ_COUNTRY = os.getenv("LG_THINQ_COUNTRY", "IN")
LG_THINQ_LANGUAGE = os.getenv("LG_THINQ_LANGUAGE", "en-IN")
LG_THINQ_BASE_URL = os.getenv("LG_THINQ_BASE_URL", "https://api-eic.lgthinq.com")
ELECTRICITY_TARIFF_PER_KWH = float(os.getenv("ELECTRICITY_TARIFF_PER_KWH", "0"))
SMARTTHINGS_APP_ID = os.getenv("SMARTTHINGS_APP_ID", "")
SMARTTHINGS_ACCESS_TOKEN = os.getenv("SMARTTHINGS_ACCESS_TOKEN", "")
SMARTTHINGS_REFRESH_TOKEN = os.getenv("SMARTTHINGS_REFRESH_TOKEN", "")
SMARTTHINGS_CLIENT_ID = os.getenv("SMARTTHINGS_CLIENT_ID", "")
SMARTTHINGS_CLIENT_SECRET = os.getenv("SMARTTHINGS_CLIENT_SECRET", "")
SMARTTHINGS_REDIRECT_URI = os.getenv("SMARTTHINGS_REDIRECT_URI", "")
SMARTTHINGS_TOKEN_EXPIRES_AT = float(os.getenv("SMARTTHINGS_TOKEN_EXPIRES_AT", "0") or 0)

# IR / HomeMate integration. The transport is intentionally generic until the exact
# HomeMate/Tuya endpoint for the physical blaster is verified.
IR_BACKEND = os.getenv("IR_BACKEND", "disabled").strip().lower()
IR_BASE_URL = os.getenv("IR_BASE_URL", "").strip().rstrip("/")
IR_CONTROL_PATH = os.getenv("IR_CONTROL_PATH", "/control").strip() or "/control"
IR_STATUS_PATH = os.getenv("IR_STATUS_PATH", "").strip()
IR_DEVICE_ID = os.getenv("IR_DEVICE_ID", "").strip()
IR_DEVICE_NAME = os.getenv("IR_DEVICE_NAME", "HomeMate IR Blaster").strip()
IR_HTTP_TIMEOUT_SECONDS = float(os.getenv("IR_HTTP_TIMEOUT_SECONDS", "8"))
IR_HTTP_TOKEN = os.getenv("IR_HTTP_TOKEN", "").strip()
IR_DEVICES_FILE = os.getenv("IR_DEVICES_FILE", os.path.join(ROOT, "data", "ir_devices.json"))
IR_COMMANDS_FILE = os.getenv("IR_COMMANDS_FILE", os.path.join(ROOT, "data", "ir_commands.json"))

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]
