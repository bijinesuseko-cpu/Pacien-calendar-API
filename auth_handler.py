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


# ─── Token persistence ────────────────────────────────────

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


# ─── OAuth (st.secrets → redirect) ────────────────────────

def _try_login() -> bool:
    print("=== _try_login() ===")
    try:
        client_id = st.secrets["google"]["client_id"]
        client_secret = st.secrets["google"]["client_secret"]
        redirect_uri = st.secrets["google"].get("redirect_uri")
        print(f"  client_id={client_id}")
        print(f"  redirect_uri={redirect_uri}")
    except Exception:
        print("  ❌ secrets google не найдены")
        st.error("Настройте google client_id и client_secret в Secrets.")
        return False

    if not redirect_uri:
        print("  ❌ redirect_uri пустой")
        st.error("Добавьте redirect_uri в Secrets")
        return False

    code = None
    try:
        raw = st.query_params.get("code")
        code = raw[0] if isinstance(raw, list) else raw
    except Exception:
        try:
            raw = st.experimental_get_query_params().get("code", [None])
            code = raw[0] if isinstance(raw, list) else raw
        except Exception:
            pass

    if code:
        print(f"  🔑 code найден в URL: {code[:20]}...")

    if code and st.session_state.get("_last_code") != code:
        st.session_state["_last_code"] = code
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
            st.session_state["token"] = token_data
            _save_token(token_data)
            return True
        except urllib.error.URLError as e:
            print(f"  ❌ ошибка обмена: {e}")
            print(f"     status={e.code if hasattr(e, 'code') else 'N/A'}")
            st.error(f"Ошибка обмена кода на токен: {e}")
            return False

    print("  ℹ️ code не найден/уже обработан — показываем кнопку входа")

    # ── Login button ──
    state = secrets.token_urlsafe(32)
    st.session_state["_oauth_state"] = state

    auth_url = AUTHORIZE_ENDPOINT + "?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    })

    st.markdown(
        f"""
        <div style="display:flex;justify-content:center;padding:1rem 0;">
            <a href="{auth_url}" target="_self"
               style="background:#dc2626;color:#fff;border:none;border-radius:8px;
                      padding:10px 32px;font-size:15px;font-weight:600;
                      font-family:Inter,-apple-system,sans-serif;cursor:pointer;
                      text-decoration:none;display:inline-flex;align-items:center;gap:10px;
                      box-shadow:0 2px 6px rgba(220,38,38,0.35);">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5"
                     stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="8" r="4"/>
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                </svg>
                Войти через Google
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
        return _try_login()
