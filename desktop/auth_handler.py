import os
import json
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
SCOPES = ["https://www.googleapis.com/auth/calendar"]

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".calendar_app")
TOKEN_FILE = os.path.join(CONFIG_DIR, "token.json")


def _ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def _save_token(token: dict):
    _ensure_config_dir()
    with open(TOKEN_FILE, "w") as f:
        json.dump(token, f)


def _load_token() -> dict | None:
    try:
        with open(TOKEN_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def _delete_token():
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)


def login() -> bool:
    if not CLIENT_ID or not CLIENT_SECRET:
        return False

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )

    try:
        creds = flow.run_local_server(port=8080, open_browser=True)
        _save_token({
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        })
        return True
    except Exception:
        return False


def get_credentials() -> Credentials | None:
    token = _load_token()
    if not token:
        return None

    try:
        expiry_str = token.get("expiry")
        expiry = datetime.fromisoformat(expiry_str) if expiry_str else None

        creds = Credentials(
            token=token.get("access_token"),
            refresh_token=token.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scopes=SCOPES,
            expiry=expiry,
        )

        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                _save_token({
                    "access_token": creds.token,
                    "refresh_token": creds.refresh_token,
                })
                return creds
            except Exception:
                _delete_token()
                return None

        if creds.valid:
            return creds
    except Exception:
        pass

    return None


def is_authenticated() -> bool:
    token = _load_token()
    if not token:
        return False
    return get_credentials() is not None


def logout():
    _delete_token()
