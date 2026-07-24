import os
import json
import secrets
import urllib.parse
import urllib.request
import warnings
import streamlit as st
import streamlit.components.v1 as components

warnings.filterwarnings("ignore", message=".*st\\.components\\.v1\\.html.*")

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/calendar"]

AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


# ─── Environment ──────────────────────────────────────────

def _is_local() -> bool:
    return os.path.exists(CREDENTIALS_FILE)


def _is_cloud() -> bool:
    try:
        return "google" in st.secrets
    except Exception:
        return False


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


# ─── Local OAuth (credentials.json → run_local_server) ────

def _local_login() -> bool:
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not os.path.exists(CREDENTIALS_FILE):
        return False

    try:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        st.session_state["token"] = {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
        }
        _save_token(st.session_state["token"])
        return True
    except Exception as e:
        st.error(f"Ошибка авторизации: {e}")
        return False


# ─── Cloud OAuth (st.secrets → popup) ─────────────────────

def _popup_login() -> bool:
    client_id = st.secrets["google"]["client_id"]
    client_secret = st.secrets["google"]["client_secret"]
    redirect_uri = st.secrets["google"].get(
        "redirect_uri",
        f"{st.get_option('server.baseUrlPath')}/component/streamlit_oauth.authorize_button",
    )

    state = st.session_state.get("_oauth_state", "")
    if not state:
        state = secrets.token_urlsafe(32)
        st.session_state["_oauth_state"] = state

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = AUTHORIZE_ENDPOINT + "?" + urllib.parse.urlencode(params)

    result = components.html(
        f"""
        <div style="display:flex;justify-content:center;align-items:center;height:100%;">
            <button id="google-btn"
                    style="background:#dc2626;color:#fff;border:none;border-radius:8px;
                           padding:10px 32px;font-size:15px;font-weight:600;
                           font-family:'Inter',-apple-system,sans-serif;cursor:pointer;
                           box-shadow:0 2px 6px rgba(220,38,38,0.35);
                           display:inline-flex;align-items:center;gap:10px;outline:none;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="8" r="4"/>
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                </svg>
                Войти через Google
            </button>
        </div>
        <script>
            document.getElementById('google-btn').onclick = function() {{
                var w = 600, h = 600;
                var left = Math.round((screen.width - w) / 2);
                var top = Math.round((screen.height - h) / 2);
                var popup = window.open(
                    '{auth_url}',
                    'oauth',
                    'toolbar=no,location=no,status=no,menubar=no,width=' + w + ',height=' + h + ',top=' + top + ',left=' + left
                );
                if (!popup) return;
                var poll = setInterval(function() {{
                    try {{
                        var url = popup.location.href;
                        if (url && url.startsWith('{redirect_uri}')) {{
                            clearInterval(poll);
                            var data = {{}};
                            for (var entry of new URL(url).searchParams.entries()) {{
                                data[entry[0]] = entry[1];
                            }}
                            Streamlit.setComponentValue(data);
                            setTimeout(function() {{ popup.close(); }}, 100);
                        }}
                    }} catch(e) {{}}
                }}, 500);
            }};
        </script>
        """,
        height=56,
    )

    if result and isinstance(result, dict) and "code" in result:
        if result.get("state") != state:
            st.error("Ошибка: несовпадение state. Попробуйте снова.")
            return False

        body = urllib.parse.urlencode({
            "code": result["code"],
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
            st.session_state["token"] = token_data
            _save_token(token_data)
            return True
        except urllib.error.URLError as e:
            st.error(f"Ошибка обмена кода на токен: {e}")

    return False


# ─── Public API ───────────────────────────────────────────

def get_credentials() -> Credentials | None:
    """Return valid Google Credentials. Runs auth flow if needed."""
    # Try restoring from saved token
    token = st.session_state.get("token") or _load_token()
    if token:
        st.session_state["token"] = token

    if "token" in st.session_state:
        token = st.session_state["token"]
        client_id = client_secret = token_uri = None

        if _is_local():
            with open(CREDENTIALS_FILE) as f:
                cfg = json.load(f)["installed"]
            client_id, client_secret = cfg["client_id"], cfg["client_secret"]
            token_uri = cfg["token_uri"]
        elif _is_cloud():
            client_id = st.secrets["google"]["client_id"]
            client_secret = st.secrets["google"]["client_secret"]
            token_uri = TOKEN_ENDPOINT

        if client_id:
            creds = Credentials(
                token=token.get("access_token"),
                refresh_token=token.get("refresh_token"),
                token_uri=token_uri,
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES,
            )
            if creds.valid:
                return creds
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    st.session_state["token"] = {
                        "access_token": creds.token,
                        "refresh_token": creds.refresh_token,
                    }
                    _save_token(st.session_state["token"])
                    return creds
                except Exception:
                    del st.session_state["token"]
                    return None

    # No valid token → run auth flow
    if _is_local():
        if _local_login():
            return get_credentials()
    elif _is_cloud():
        st.warning("Нажмите «Войти через Google» для авторизации.")
        return None
    else:
        st.error("Нет конфигурации: поместите credentials.json или настройте secrets.")
        return None

    return None


def revoke_token() -> bool:
    if "token" in st.session_state:
        del st.session_state["token"]
    if os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
            return True
        except OSError:
            pass
    return False


def is_authenticated() -> bool:
    if "token" not in st.session_state:
        saved = _load_token()
        if saved:
            st.session_state["token"] = saved
    return "token" in st.session_state


# ─── UI helpers ───────────────────────────────────────────

def login_section() -> bool:
    if is_authenticated():
        st.sidebar.success("✓ Авторизован через Google")
        if st.sidebar.button("Выйти", use_container_width=True):
            revoke_token()
            st.rerun()
        return True
    else:
        st.sidebar.warning("Не авторизован")
        if _is_cloud():
            return _popup_login()
        else:
            if st.sidebar.button("Войти через Google", use_container_width=True):
                creds = get_credentials()
                if creds:
                    st.rerun()
                else:
                    st.sidebar.error("Ошибка входа")
        return False
