import os
import json
import secrets
import webbrowser
import urllib.parse
import urllib.request
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# При сборке .exe заменить на вшитые значения:
# CLIENT_ID = "ваш_client_id"
# CLIENT_SECRET = "ваш_client_secret"
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
SCOPES = ["https://www.googleapis.com/auth/calendar"]
AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REDIRECT_URI = "http://localhost:8080"

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


# ── OAuth callback server ──────────────────────────────────

_code_event = threading.Event()
_code_result = None


class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _code_result
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            _code_result = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<h2>Авторизация завершена!</h2>"
                "<p>Можете закрыть это окно и вернуться в приложение.</p>"
                "<script>window.close()</script>".encode("utf-8")
            )
            _code_event.set()
        elif "error" in params:
            _code_result = None
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Error: {params['error'][0]}".encode())
            _code_event.set()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def _run_server(server):
    while not _code_event.is_set():
        server.handle_request()


def _check_creds():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError(
            "Не настроены GOOGLE_CLIENT_ID и GOOGLE_CLIENT_SECRET.\n"
            "Перед сборкой .exe пропишите их в desktop/auth_handler.py"
        )


def build_google_auth_url() -> str:
    _check_creds()
    state = secrets.token_urlsafe(32)
    return AUTHORIZE_ENDPOINT + "?" + urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    })


def login() -> bool:
    _check_creds()
    global _code_event, _code_result
    _code_event = threading.Event()
    _code_result = None

    server = HTTPServer(("localhost", 8080), OAuthHandler)
    auth_url = build_google_auth_url()
    webbrowser.open(auth_url)

    server_thread = threading.Thread(target=_run_server, args=(server,), daemon=True)
    server_thread.start()

    _code_event.wait(timeout=300)
    server.server_close()

    if not _code_result:
        return False

    body = urllib.parse.urlencode({
        "code": _code_result,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request(TOKEN_ENDPOINT, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        resp = urllib.request.urlopen(req)
        token = json.loads(resp.read().decode())
        _save_token(token)
        return True
    except Exception:
        return False


def get_credentials() -> Credentials | None:
    token = _load_token()
    if not token:
        return None

    try:
        creds = Credentials(
            token=token.get("access_token"),
            refresh_token=token.get("refresh_token"),
            token_uri=TOKEN_ENDPOINT,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scopes=SCOPES,
        )

        expires_at = token.get("expires_at")
        if expires_at and expires_at < datetime.now().timestamp() and creds.refresh_token:
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
