import os
import json
import streamlit as st
from datetime import datetime, timezone
from streamlit_oauth import OAuth2Component
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


def get_credentials() -> Credentials | None:
    if "token" not in st.session_state:
        return None

    token = st.session_state["token"]
    try:
        cid = st.secrets["google"]["client_id"]
        csecret = st.secrets["google"]["client_secret"]
    except Exception:
        return None

    expiry = None
    if token.get("expires_at"):
        expiry = datetime.fromtimestamp(token["expires_at"], tz=timezone.utc)

    creds = Credentials(
        token=token.get("access_token"),
        refresh_token=token.get("refresh_token"),
        token_uri=TOKEN_ENDPOINT,
        client_id=cid,
        client_secret=csecret,
        scopes=SCOPES,
        expiry=expiry,
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
    return "token" in st.session_state


def login_section() -> bool:
    if is_authenticated():
        st.sidebar.success("✓ Авторизован через Google")
        if st.sidebar.button("Выйти", use_container_width=True):
            revoke_token()
            st.rerun()
        return True

    st.sidebar.warning("Не авторизован")

    try:
        oauth2 = OAuth2Component(
            client_id=st.secrets["google"]["client_id"],
            client_secret=st.secrets["google"]["client_secret"],
            authorize_endpoint=AUTHORIZE_ENDPOINT,
            token_endpoint=TOKEN_ENDPOINT,
        )

        result = oauth2.authorize_button(
            "Войти через Google",
            redirect_uri=st.secrets["google"]["redirect_uri"],
            scope=" ".join(SCOPES),
            pkce="S256",
            extras_params={"prompt": "select_account", "access_type": "offline"},
            icon=None,
            use_container_width=True,
        )

        if result and "token" in result:
            st.session_state["token"] = result["token"]
            st.rerun()
    except Exception:
        pass

    return False
