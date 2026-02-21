import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (same dir as this file)
_project_root = Path(__file__).resolve().parent
load_dotenv(_project_root / ".env")

_loaded = False


def _require(var_name):
    val = os.getenv(var_name)
    if not val:
        print(f"Error: {var_name} is not set. Copy .env.example to .env and fill in your values.")
        sys.exit(1)
    return val


def _ensure_loaded():
    """Load required config on first access. Allows --help to work without .env."""
    global _loaded, FITBIT_CLIENT_ID, FITBIT_CLIENT_SECRET, GOOGLE_SHEET_ID
    global GOOGLE_SERVICE_ACCOUNT_FILE, FITBIT_TOKEN_FILE
    global API_KEY, SERVER_PORT
    if _loaded:
        return
    FITBIT_CLIENT_ID = _require("FITBIT_CLIENT_ID")
    FITBIT_CLIENT_SECRET = _require("FITBIT_CLIENT_SECRET")
    GOOGLE_SHEET_ID = _require("GOOGLE_SHEET_ID")
    GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_FILE",
        str(_project_root / "service_account.json"),
    )
    FITBIT_TOKEN_FILE = os.getenv(
        "FITBIT_TOKEN_FILE",
        str(_project_root / "tokens.json"),
    )
    API_KEY = _require("API_KEY")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "8585"))
    _loaded = True


# Defaults so imports don't fail before _ensure_loaded()
FITBIT_CLIENT_ID = ""
FITBIT_CLIENT_SECRET = ""
GOOGLE_SHEET_ID = ""
GOOGLE_SERVICE_ACCOUNT_FILE = str(_project_root / "service_account.json")
FITBIT_TOKEN_FILE = str(_project_root / "tokens.json")
API_KEY = ""
SERVER_PORT = 8585

FITBIT_AUTH_URI = "https://www.fitbit.com/oauth2/authorize"
FITBIT_TOKEN_URI = "https://api.fitbit.com/oauth2/token"
FITBIT_REDIRECT_URI = "http://127.0.0.1:8080/callback"
FITBIT_SCOPES = [
    "activity",
    "cardio_fitness",
    "heartrate",
    "oxygen_saturation",
    "respiratory_rate",
    "sleep",
    "temperature",
]
