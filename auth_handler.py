import os
import json
import secrets
import urllib.parse
import urllib.request
import streamlit as st

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/calendar"]
AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
TOKEN_FILE = "token.json"


def _save_token(t: dict) -> None:
    try:
        with open(TOKEN_FILE, "w") as f:
            json.dump(t, f)
    except Exception:
        pass


def _load_token() -> dict | None:
    try:
        with open(TOKEN_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def build_google_auth_url(redirect_uri: str) -> str:
    state = secrets.token_urlsafe(32)
    st.session_state["_oauth_state"] = state
    return AUTHORIZE_ENDPOINT + "?" + urllib.parse.urlencode({
        "client_id": st.secrets["google"]["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    })


def handle_oauth_callback(code: str, redirect_uri: str) -> bool:
    print("=== handle_oauth_callback() ===")
    try:
        client_id = st.secrets["google"]["client_id"]
        client_secret = st.secrets["google"]["client_secret"]
        print(f"  client_id={client_id}")
    except Exception:
        print("  ❌ secrets google не найдены")
        return False

    if st.session_state.get("_last_code") == code:
        print("  ℹ️ code уже обработан")
        return True

    print("  🔄 обмен code на токен...")
    body = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request(TOKEN_ENDPOINT, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        resp = urllib.request.urlopen(req)
        token_data = json.loads(resp.read().decode())
        print(f"  ✅ токен получен, access_token={token_data.get('access_token', '')[:30]}...")
        print(f"     есть refresh_token: {'да' if token_data.get('refresh_token') else 'нет'}")
        st.session_state["_last_code"] = code
        st.session_state["token"] = token_data
        _save_token(token_data)
        return True
    except urllib.error.URLError as e:
        print(f"  ❌ ошибка обмена: {e}")
        return False


def get_credentials() -> Credentials | None:
    print("=== get_credentials() ===")
    if "token" in st.session_state:
        print("  ✅ токен есть в session_state")
        token = st.session_state["token"]
        try:
            cid = st.secrets["google"]["client_id"]
            csecret = st.secrets["google"]["client_secret"]
        except Exception:
            print("  ❌ secrets не найдены")
            return None

        creds = Credentials(
            token=token.get("access_token"),
            refresh_token=token.get("refresh_token"),
            token_uri=TOKEN_ENDPOINT,
            client_id=cid,
            client_secret=csecret,
            scopes=SCOPES,
        )
        if creds.valid:
            print("  ✅ токен валиден")
            return creds
        if creds.expired and creds.refresh_token:
            print("  🔄 токен истёк, refreshing...")
            try:
                creds.refresh(Request())
                st.session_state["token"] = {
                    "access_token": creds.token,
                    "refresh_token": creds.refresh_token,
                }
                _save_token(st.session_state["token"])
                print("  ✅ refresh успешен")
                return creds
            except Exception as e:
                print(f"  ❌ refresh failed: {e}")
                del st.session_state["token"]
                return None
        print("  ❌ токен невалиден и не может быть обновлён")
    else:
        print("  ❌ токена нет в session_state")
    return None


def revoke_token() -> bool:
    print("=== revoke_token() ===")
    if "token" in st.session_state:
        del st.session_state["token"]
        print("  🗑️ токен удалён из session_state")
    if os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
            print("  🗑️ token.json удалён")
            return True
        except OSError:
            pass
    print("  ℹ️ token.json не найден")
    return False


def is_authenticated() -> bool:
    result = "token" in st.session_state
    print(f"=== is_authenticated() → {result} ===")
    return result


def login_section() -> bool:
    if is_authenticated():
        st.sidebar.success("✓ Авторизован через Google")
        if st.sidebar.button("Выйти", use_container_width=True):
            revoke_token()
            st.rerun()
        return True
    else:
        st.sidebar.warning("Не авторизован")
        return False
