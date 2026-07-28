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
        print("❌ GOOGLE_CLIENT_ID или GOOGLE_CLIENT_SECRET не заданы")
        return False

    print("🔄 Запуск локального сервера для OAuth...")
    print("   Браузер откроется для входа через Google")

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
        creds = flow.run_local_server(port=0, open_browser=True, timeout=120)
        print("✅ Токен получен! Сохраняем...")
        _save_token({
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        })
        return True
    except Exception as e:
        print(f"❌ Ошибка получения токена: {e}")
        return False


def get_credentials() -> Credentials | None:
    token = _load_token()
    if not token:
        print("  → токена нет в файле")
        return None

    try:
        now = datetime.now(timezone.utc)
        expiry_str = token.get("expiry")

        if expiry_str:
            expiry = datetime.fromisoformat(expiry_str)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
        else:
            expiry = None

        print(f"  → токен: access_token={token.get('access_token','')[:20]}...")
        print(f"  → срок: {expiry}")
        print(f"  → сейчас: {now.isoformat()}")

        # Если протух — пробуем обновить ДО создания Credentials
        if expiry and expiry < now:
            print("  ⚠️ токен протух")
            refresh_token = token.get("refresh_token")
            if refresh_token:
                print("  🔄 пробуем обновить...")
                temp_creds = Credentials(
                    token=None,
                    refresh_token=refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=CLIENT_ID,
                    client_secret=CLIENT_SECRET,
                    scopes=SCOPES,
                )
                try:
                    temp_creds.refresh(Request())
                    print("  ✅ токен обновлён")
                    _save_token({
                        "access_token": temp_creds.token,
                        "refresh_token": temp_creds.refresh_token,
                        "expiry": temp_creds.expiry.isoformat() if temp_creds.expiry else None,
                    })
                    return temp_creds
                except Exception as e:
                    print(f"  ❌ ошибка обновления: {e}")
                    _delete_token()
                    return None
            else:
                print("  ❌ нет refresh_token")
                _delete_token()
                return None

        creds = Credentials(
            token=token.get("access_token"),
            refresh_token=token.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scopes=SCOPES,
        )

        print("  ✅ токен валиден")
        return creds
    except Exception as e:
        print(f"  ❌ ошибка в get_credentials: {e}")

    return None


def is_authenticated() -> bool:
    token = _load_token()
    if not token:
        return False
    return get_credentials() is not None


def logout():
    _delete_token()
